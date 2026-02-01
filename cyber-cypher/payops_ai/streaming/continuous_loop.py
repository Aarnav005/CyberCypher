"""Continuous agent loop for real-time payment stream processing."""

import logging
import time
import signal
from typing import Optional
from dataclasses import dataclass
import json
import random

from payops_ai.orchestrator import AgentOrchestrator
from payops_ai.streaming.continuous_generator import ContinuousPaymentGenerator
from payops_ai.streaming.feedback_controller import FeedbackController
from payops_ai.streaming.drift_engine import StochasticDriftEngine
from payops_ai.streaming.ws_broadcaster import get_broadcaster

logger = logging.getLogger(__name__)


@dataclass
class LoopConfig:
    """Configuration for continuous agent loop."""
    cycle_interval: float = 15.0  # seconds between agent cycles
    loop_rate: float = 10.0       # Hz for main loop
    max_duration: Optional[float] = None  # seconds (None = infinite)
    checkpoint_cycles: Optional[int] = None  # pause after N cycles for user input


class ContinuousAgentLoop:
    """Main loop for continuous agent operation with streaming data.
    
    Coordinates:
    - Continuous transaction generation with stochastic drift
    - Agent cycle execution at regular intervals
    - Feedback from agent decisions to generation parameters
    - Graceful shutdown handling
    """
    
    def __init__(self, 
                 orchestrator: AgentOrchestrator,
                 drift_engine: StochasticDriftEngine,
                 generator: ContinuousPaymentGenerator,
                 feedback: FeedbackController,
                 config: LoopConfig):
        """Initialize continuous agent loop.
        
        Args:
            orchestrator: Agent orchestrator for decision-making
            drift_engine: Stochastic drift engine for parameter evolution
            generator: Continuous payment generator
            feedback: Feedback controller for interventions
            config: Loop configuration
        """
        self.orchestrator = orchestrator
        self.drift_engine = drift_engine
        self.generator = generator
        self.feedback = feedback
        self.config = config
        
        self.running = False
        self.cycle_count = 0
        self.total_transactions = 0

        # Lightweight series for telemetry charts
        self.success_series: list[float] = []
        self.latency_series: list[float] = []
        self.intervention_history = []

        # WebSocket broadcaster
        self.ws_broadcaster = get_broadcaster()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        
        logger.info(f"Initialized ContinuousAgentLoop: cycle_interval={config.cycle_interval}s, "
                   f"loop_rate={config.loop_rate}Hz")
    
    def _handle_shutdown(self, signum, frame):
        """Handle graceful shutdown on signal.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.running = False
    
    def run(self) -> None:
        """Run continuous loop until stopped or duration limit reached."""
        self.running = True
        start_time = time.time()
        last_cycle_time = start_time
        last_log_time = start_time
        last_telemetry_time = 0.0
        
        decision = None
        explanation = None
        
        logger.info("="*80)
        logger.info("Starting Continuous Agent Loop")
        logger.info("="*80)
        logger.info(f"Cycle interval: {self.config.cycle_interval}s")
        logger.info(f"Transaction rate: {self.generator.transaction_rate} txns/s")
        logger.info(f"Issuers: {', '.join(self.drift_engine.issuers.keys())}")
        logger.info("="*80)

        # Start WS broadcaster
        try:
            self.ws_broadcaster.start()
        except Exception as e:
            logger.warning(f"Failed to start WebSocket broadcaster: {e}")

        loop_sleep = 1.0 / self.config.loop_rate
        
        while self.running:
            current_time = time.time()
            elapsed = current_time - start_time
            dt = current_time - last_cycle_time
            
            try:
                # Update drift engine
                self.drift_engine.update(dt, current_time)
                
                # Generate new transactions
                new_txns = self.generator.generate_next_batch(dt)
                self.total_transactions += len(new_txns)
                
                # Add to observation stream
                if new_txns:
                    self.orchestrator.stream.add_transaction_batch(new_txns)
                
                # Run agent cycle if interval elapsed
                if dt >= self.config.cycle_interval:
                    self.cycle_count += 1
                    logger.info(f"\n{'='*80}")
                    logger.info(f"CYCLE {self.cycle_count} - Elapsed: {elapsed:.1f}s")
                    logger.info(f"{'='*80}")
                    
                    # Log current issuer states
                    for issuer_name, state in self.drift_engine.get_all_issuers().items():
                        logger.info(f"{issuer_name}: success={state.success_rate:.2%}, "
                                   f"latency={state.latency_ms:.0f}ms, retry={state.retry_prob:.2%}")
                    
                    # USER REQUEST: Forced intervention every 5 cycles
                    # First, manipulate state if it's the 5th cycle to justify intervention
                    synthetic_failure = False
                    if self.cycle_count % 5 == 0:
                        logger.info("!! FORCING SYNTHETIC FAILURE FOR CYCLE 5 !!")
                        issuer_states = self.drift_engine.get_all_issuers()
                        if issuer_states:
                            target_issuer_name = list(issuer_states.keys())[0]
                            target_state = issuer_states[target_issuer_name]
                            # Force failure: low success, high latency
                            target_state.success_rate = 0.05
                            target_state.latency_ms = 2000.0
                            synthetic_failure = True

                    # Execute agent cycle
                    decision, explanation = self.orchestrator.execute_cycle()

                    # If it's a 5th cycle and agent didn't act, force an intervention
                    if self.cycle_count % 5 == 0 and not (decision.should_act and decision.selected_option):
                        logger.info("!! FORCING SYNTHETIC INTERVENTION !!")
                        from payops_ai.models.intervention import InterventionOption, InterventionType, OutcomeEstimate, Tradeoffs
                        
                        synthetic_option = InterventionOption(
                            type=InterventionType.REROUTE_TRAFFIC,
                            target=f"issuer:{list(self.drift_engine.get_all_issuers().keys())[0]}",
                            parameters={"duration_ms": 60000},
                            expected_outcome=OutcomeEstimate(
                                expected_success_rate_change=0.9,
                                expected_latency_change=-100.0,
                                expected_cost_change=0.01,
                                confidence=0.99
                            ),
                            tradeoffs=Tradeoffs(
                                success_rate_impact=0.9,
                                latency_impact=-100.0,
                                cost_impact=0.01,
                                risk_impact=0.0,
                                user_friction_impact=0.1
                            ),
                            reversible=True,
                            blast_radius=0.1
                        )
                        self.feedback.apply_intervention(synthetic_option)
                        # Patch decision for logging/telemetry
                        decision.should_act = True
                        decision.selected_option = synthetic_option
                        decision.rationale = "Synthetic intervention triggered for demo cycle 5. NRV=$5,000"
                        
                        # Add to history
                        self.intervention_history.append({
                            'ts': time.strftime('%H:%M:%S', time.localtime()),
                            'action': synthetic_option.type,
                            'target': synthetic_option.target,
                            'reason': decision.rationale,
                            'result': 'Triggered',
                            'rate': '+5.0%' # Mock impact
                        })
                    
                    # Apply intervention if decided
                    if decision.should_act and decision.selected_option:
                        self.feedback.apply_intervention(decision.selected_option)
                        
                        # Add to history if not already added (for forced ones)
                        if not any(i['ts'] == time.strftime('%H:%M:%S', time.localtime()) and i['action'] == decision.selected_option.type for i in self.intervention_history):
                            self.intervention_history.append({
                                'ts': time.strftime('%H:%M:%S', time.localtime()),
                                'action': decision.selected_option.type,
                                'target': decision.selected_option.target,
                                'reason': decision.rationale or "Automatic intervention",
                                'result': 'Active',
                                'rate': f"+{random.uniform(1, 5):.1f}%"
                            })
                        logger.info(f"Applied intervention: {decision.selected_option.type.value} "
                                   f"on {decision.selected_option.target}")
                    
                    # Log active interventions
                    if self.feedback.get_active_count() > 0:
                        logger.info(f"\n{self.feedback.get_status_summary(current_time)}")
                    
                    # Update rolling series during the cycle
                    issuers = list(self.drift_engine.get_all_issuers().values())
                    cycle_success = (sum(s.success_rate for s in issuers)/len(issuers)) * 100.0 if issuers else 100.0
                    cycle_latency = (sum(s.latency_ms for s in issuers)/len(issuers)) if issuers else 0.0
                    
                    self.success_series.append(cycle_success)
                    self.latency_series.append(cycle_latency)
                    if len(self.success_series) > 40:
                        self.success_series = self.success_series[-40:]
                    if len(self.latency_series) > 40:
                        self.latency_series = self.latency_series[-40:]

                    last_cycle_time = current_time

                # Prepare and broadcast a lightweight telemetry snapshot every 1 second
                if current_time - last_telemetry_time >= 1.0:
                    try:
                        from payops_ai.models.transaction import Outcome
                        recent_txns = self.orchestrator.stream.get_recent_transactions()
                        if recent_txns:
                            success_count = sum(1 for t in recent_txns if t.outcome == Outcome.SUCCESS)
                            avg_success = (success_count / len(recent_txns)) * 100.0
                            avg_latency = sum(t.latency_ms for t in recent_txns) / len(recent_txns)
                        else:
                            # Fallback to issuer state if no recent txns
                            issuers = list(self.drift_engine.get_all_issuers().values())
                            avg_success = (sum(s.success_rate for s in issuers)/len(issuers)) * 100.0 if issuers else 100.0
                            avg_latency = (sum(s.latency_ms for s in issuers)/len(issuers)) if issuers else 0.0

                        # Extract simple summary from explanation if present
                        thinking = []
                        try:
                            if explanation and hasattr(explanation, 'executive_summary') and explanation.executive_summary:
                                thinking.append(explanation.executive_summary)
                            else:
                                thinking.append('Operational - Monitoring stream...')
                        except Exception:
                            thinking = ['Operational - Monitoring stream...']

                        # Parse NRV from decision rationale if present
                        nrv_val = None
                        try:
                            if decision and getattr(decision, 'rationale', None):
                                if 'NRV=$' in decision.rationale:
                                    nrv_str = decision.rationale.split('NRV=$')[1].split()[0]
                                    nrv_val = float(nrv_str.replace(',',''))
                        except Exception:
                            nrv_val = None

                        # Generate lightweight safety metrics (simulated for demo)
                        fpr = max(0.0, round(0.8 + random.uniform(-0.1, 0.1), 2))
                        avg_resp = max(0.2, round(1.0 + random.uniform(-0.1, 0.1), 2))
                        rollback = max(0.0, round(2.1 + random.uniform(-0.1, 0.1), 2))
                        human_escalations = max(0, int(3 + random.randint(0, 1)))

                        status = {
                            'timestamp': int(current_time),
                            'total_volume': self.total_transactions,
                            'fail_rate': round(100.0 - avg_success, 2),
                            'active_gateway': 'Gateway-Alpha',
                            'success_series': self.success_series,
                            'latency_series': self.latency_series,
                            'thinking_log': thinking,
                            'nrv': nrv_val or 0,
                            'confidence': round(getattr(explanation, 'confidence', 0.0) * 100.0, 1) if explanation else 0.0,
                            'safety_metrics': {
                                'false_positive_rate': fpr,
                                'avg_response_time_s': avg_resp,
                                'rollback_rate': rollback,
                                'human_escalations': human_escalations
                            },
                            'intervention_history': self.intervention_history[-10:]
                        }

                        # Broadcast
                        self.ws_broadcaster.broadcast_sync(json.dumps(status))
                        last_telemetry_time = current_time
                    except Exception as e:
                        logger.debug(f"Telemetry broadcast failed: {e}")

                    # Check for checkpoint
                    if self.config.checkpoint_cycles and self.cycle_count >= self.config.checkpoint_cycles:
                        if not self._handle_checkpoint(elapsed):
                            logger.info("User chose to end simulation")
                            break
                
                # Update feedback controller (expire interventions)
                self.feedback.update(current_time)
                
                # Periodic status log (every 60 seconds)
                if current_time - last_log_time >= 60.0:
                    self._log_status(elapsed)
                    last_log_time = current_time
                
                # Check duration limit
                if self.config.max_duration and elapsed >= self.config.max_duration:
                    logger.info(f"Reached duration limit of {self.config.max_duration}s")
                    break
                
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                break
            except Exception as e:
                logger.error(f"Error in loop iteration: {e}", exc_info=True)
                # Continue running despite errors
            
            # Sleep to control loop rate
            time.sleep(loop_sleep)
        
        # Shutdown
        self._shutdown()
    
    def _log_status(self, elapsed: float) -> None:
        """Log periodic status update.
        
        Args:
            elapsed: Elapsed time since start
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"STATUS UPDATE - Elapsed: {elapsed:.1f}s")
        logger.info(f"{'='*80}")
        logger.info(f"Cycles completed: {self.cycle_count}")
        logger.info(f"Total transactions: {self.total_transactions}")
        logger.info(f"Buffer size: {self.generator.get_buffer_size()}")
        logger.info(f"Active interventions: {self.feedback.get_active_count()}")
        
        # Log issuer states
        logger.info("\nIssuer States:")
        for issuer_name, state in self.drift_engine.get_all_issuers().items():
            logger.info(f"  {issuer_name}: success={state.success_rate:.2%}, "
                       f"latency={state.latency_ms:.0f}ms, retry={state.retry_prob:.2%}")
        
        logger.info(f"{'='*80}\n")
    
    def _handle_checkpoint(self, elapsed: float) -> bool:
        """Handle checkpoint - show results and ask user to continue or end.
        
        Args:
            elapsed: Elapsed time since start
            
        Returns:
            True to continue, False to end
        """
        print("\n" + "="*80)
        print(f"CHECKPOINT REACHED - {self.cycle_count} CYCLES COMPLETED")
        print("="*80)
        print(f"\nElapsed Time: {elapsed:.1f}s ({elapsed/60:.1f} minutes)")
        print(f"Total Cycles: {self.cycle_count}")
        print(f"Total Transactions: {self.total_transactions:,}")
        print(f"Avg Transactions/Cycle: {self.total_transactions/self.cycle_count:.0f}")
        print(f"Buffer Size: {self.generator.get_buffer_size()}")
        print(f"Active Interventions: {self.feedback.get_active_count()}")
        
        # Show issuer states
        print("\nIssuer Health Summary:")
        print("-" * 80)
        for issuer_name, state in self.drift_engine.get_all_issuers().items():
            status = "✓ HEALTHY" if state.success_rate >= 0.9 else "⚠ DEGRADED" if state.success_rate >= 0.7 else "✗ CRITICAL"
            print(f"  {issuer_name:8s}: {status:12s} | Success: {state.success_rate:6.2%} | "
                  f"Latency: {state.latency_ms:5.0f}ms | Retry: {state.retry_prob:5.2%}")
        
        # Show agent performance
        print("\nAgent Performance:")
        print("-" * 80)
        
        # Get recent patterns from orchestrator
        if hasattr(self.orchestrator, 'stream') and hasattr(self.orchestrator.stream, 'get_recent_transactions'):
            recent_txns = self.orchestrator.stream.get_recent_transactions(300000)  # Last 5 minutes
            if recent_txns:
                from payops_ai.models.transaction import Outcome
                success_count = sum(1 for t in recent_txns if t.outcome == Outcome.SUCCESS)
                success_rate = success_count / len(recent_txns)
                print(f"  Recent Success Rate: {success_rate:.2%} ({success_count}/{len(recent_txns)} transactions)")
        
        print(f"  Total Interventions Applied: {self.feedback.get_active_count()}")
        print(f"  Patterns Detected: (check logs for details)")
        
        print("\n" + "="*80)
        print("OPTIONS:")
        print("  [C] Continue for another 15 cycles")
        print("  [E] End simulation and show final results")
        print("="*80)
        
        # Get user input
        while True:
            try:
                choice = input("\nYour choice (C/E): ").strip().upper()
                if choice in ['C', 'CONTINUE']:
                    print("\nContinuing simulation for another 15 cycles...")
                    self.config.checkpoint_cycles = self.cycle_count + 15
                    return True
                elif choice in ['E', 'END']:
                    return False
                else:
                    print("Invalid choice. Please enter C (continue) or E (end).")
            except (EOFError, KeyboardInterrupt):
                print("\nEnding simulation...")
                return False
    
    def _shutdown(self) -> None:
        """Perform graceful shutdown."""
        logger.info("\n" + "="*80)
        logger.info("SHUTTING DOWN")
        logger.info("="*80)
        logger.info(f"Total cycles: {self.cycle_count}")
        logger.info(f"Total transactions: {self.total_transactions}")
        logger.info(f"Final buffer size: {self.generator.get_buffer_size()}")
        
        # Log final issuer states
        logger.info("\nFinal Issuer States:")
        for issuer_name, state in self.drift_engine.get_all_issuers().items():
            logger.info(f"  {issuer_name}: success={state.success_rate:.2%}, "
                       f"latency={state.latency_ms:.0f}ms, retry={state.retry_prob:.2%}")
        
        # Stop broadcaster if running
        try:
            self.ws_broadcaster.stop()
        except Exception:
            pass

        logger.info("="*80)
        logger.info("Continuous Agent Loop stopped gracefully")
    
    def stop(self) -> None:
        """Stop the loop (can be called from another thread)."""
        logger.info("Stop requested")
        self.running = False
