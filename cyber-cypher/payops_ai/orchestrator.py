"""Agent orchestrator - main control loop."""

import logging
import time
from typing import Optional, List, Dict, Any

from payops_ai.observation.stream import ObservationStream
from payops_ai.observation.window import ObservationWindow
from payops_ai.observation.baseline import BaselineManager
from payops_ai.reasoning.anomaly import AnomalyDetector
from payops_ai.reasoning.pattern import PatternDetector
from payops_ai.reasoning.hypothesis import HypothesisGenerator
from payops_ai.reasoning.belief import BeliefStateManager
from payops_ai.decision.planner import InterventionPlanner
from payops_ai.decision.policy import DecisionPolicy
from payops_ai.action.executor import ActionExecutor
from payops_ai.learning.evaluator import OutcomeEvaluator
from payops_ai.explainability.generator import ExplanationGenerator
from payops_ai.memory.incident_store import IncidentStore, IncidentSignature
from payops_ai.memory.playbook_retriever import PlaybookRetriever
from payops_ai.memory.state_manager import StateManager
from payops_ai.memory.audit_log import AuditLog
from payops_ai.safety.constraints import SafetyConstraints
from payops_ai.models.explanation import Explanation
from payops_ai.models.intervention import InterventionDecision

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Orchestrates the complete observe → reason → decide → act → learn loop."""
    
    def __init__(
        self,
        window_duration_ms: int = 300000,  # 5 minutes
        anomaly_threshold: float = 2.0,
        min_confidence: float = 0.7,
        max_blast_radius: float = 0.3,
        simulation_mode: bool = True,
        gemini_api_key: Optional[str] = None,
        enable_state_persistence: bool = True,
        enable_audit_logging: bool = True,
        enable_safety_constraints: bool = True,
        min_action_frequency_cycles: int = 6
    ):
        """Initialize agent orchestrator.
        
        Args:
            window_duration_ms: Observation window duration
            anomaly_threshold: Anomaly detection threshold
            min_confidence: Minimum confidence for autonomous action
            max_blast_radius: Maximum blast radius for autonomous action
            simulation_mode: If True, simulate actions without executing
            gemini_api_key: Google Gemini API key for RAG playbook retrieval
            enable_state_persistence: Enable state save/load
            enable_audit_logging: Enable audit log
            enable_safety_constraints: Enable safety constraints
            min_action_frequency_cycles: Guarantee action every N cycles
        """
        # Observation components
        self.stream = ObservationStream()
        self.window = ObservationWindow(window_duration_ms)
        self.baseline_manager = BaselineManager()
        
        # Reasoning components
        self.anomaly_detector = AnomalyDetector(anomaly_threshold)
        self.pattern_detector = PatternDetector()
        self.hypothesis_generator = HypothesisGenerator()
        self.belief_manager = BeliefStateManager()
        
        # Decision components
        self.intervention_planner = InterventionPlanner()
        self.decision_policy = DecisionPolicy(
            min_confidence, 
            max_blast_radius,
            min_action_frequency_cycles=min_action_frequency_cycles
        )
        self.safety_constraints = SafetyConstraints() if enable_safety_constraints else None
        
        # Action components
        self.action_executor = ActionExecutor(simulation_mode=simulation_mode)
        
        # Learning components
        self.outcome_evaluator = OutcomeEvaluator()
        
        # Explainability
        self.explanation_generator = ExplanationGenerator()
        
        # Memory components (RAG)
        self.incident_store = IncidentStore()
        self.playbook_retriever = PlaybookRetriever(gemini_api_key) if gemini_api_key else None
        self.enable_rag = gemini_api_key is not None
        
        # State & Audit components
        self.state_manager = StateManager() if enable_state_persistence else None
        self.audit_log = AuditLog() if enable_audit_logging else None
        
        self.simulation_mode = simulation_mode
        self.cycle_count = 0
        
        # Try to load previous state
        if self.state_manager:
            loaded_state = self.state_manager.load_state()
            if loaded_state:
                logger.info(f"Restored state from {loaded_state.last_updated}")
                # State loaded successfully (cycle_count starts fresh)
        
        logger.info(f"Agent initialized (simulation_mode={simulation_mode}, "
                   f"RAG={'enabled' if self.enable_rag else 'disabled'}, "
                   f"state_persistence={'enabled' if self.state_manager else 'disabled'}, "
                   f"audit_log={'enabled' if self.audit_log else 'disabled'}, "
                   f"safety_constraints={'enabled' if self.safety_constraints else 'disabled'})")
    
    def execute_cycle(self) -> tuple[InterventionDecision, Explanation]:
        """Execute one complete agent cycle with professional upgrades.
        
        Returns:
            Tuple of (decision, explanation)
        """
        self.cycle_count += 1
        timestamp = int(time.time() * 1000)
        
        logger.info(f"=== Cycle {self.cycle_count} starting ===")
        
        # 1. OBSERVE
        logger.info("Phase 1: OBSERVE")
        recent_transactions = self.stream.get_recent_transactions()
        self.window.update(recent_transactions, timestamp)
        windowed_transactions = self.window.get_transactions()
        aggregate_stats = self.window.calculate_aggregate_stats()
        
        logger.info(f"Observed {len(windowed_transactions)} transactions, "
                   f"success rate: {aggregate_stats.success_rate:.2%}")
        
        # 2. REASON (with Multi-Factor Confidence Scoring and Rolling Baselines)
        logger.info("Phase 2: REASON (with Multi-Factor Confidence and EWMA Baselines)")
        
        # Update rolling baselines with current observations
        self.baseline_manager.update_rolling_baselines(windowed_transactions, timestamp)
        
        # Detect anomalies with confidence scoring using rolling baselines
        all_patterns = []
        z_score_max = 0.0
        
        # Calculate dimension-specific aggregate stats for anomaly detection
        from collections import defaultdict
        from payops_ai.models.transaction import Outcome
        
        # Group by issuer
        by_issuer = defaultdict(list)
        for txn in windowed_transactions:
            by_issuer[f"issuer:{txn.issuer}"].append(txn)
        
        # Detect anomalies per issuer
        for dimension, txns in by_issuer.items():
            if len(txns) < 5:
                continue
            
            # Calculate dimension-specific stats
            success_count = sum(1 for t in txns if t.outcome == Outcome.SUCCESS)
            dim_stats = type('obj', (object,), {
                'total_transactions': len(txns),
                'success_rate': success_count / len(txns),
                'success_count': success_count,
                'soft_fail_count': sum(1 for t in txns if t.outcome == Outcome.SOFT_FAIL),
                'hard_fail_count': sum(1 for t in txns if t.outcome == Outcome.HARD_FAIL),
                'avg_latency_ms': sum(t.latency_ms for t in txns) / len(txns),
                'p95_latency_ms': sorted([t.latency_ms for t in txns])[int(0.95 * len(txns))],
                'p99_latency_ms': sorted([t.latency_ms for t in txns])[int(0.99 * len(txns))],
                'avg_retry_count': sum(t.retry_count for t in txns) / len(txns),
                'unique_issuers': 1,
                'unique_methods': len(set(t.payment_method for t in txns))
            })()
            
            # Prefer rolling baseline over static baseline
            rolling_baseline = self.baseline_manager.get_rolling_baseline(dimension)
            if rolling_baseline and rolling_baseline.sample_count >= 3:
                # Use rolling baseline for Z-score calculation
                patterns = self.anomaly_detector.detect_anomalies_with_rolling_baseline(
                    dim_stats, rolling_baseline, dimension, timestamp, txns
                )
                all_patterns.extend(patterns)
                
                # Extract Z-score from evidence
                for pattern in patterns:
                    for evidence in pattern.evidence:
                        if "Z-score" in evidence.description:
                            z_score_max = max(z_score_max, evidence.value)
            else:
                # Fall back to static baseline if rolling baseline not ready
                baseline = self.baseline_manager.get_baseline(dimension)
                if baseline:
                    # Pass transactions for confidence scoring
                    patterns = self.anomaly_detector.detect_anomalies(
                        dim_stats, baseline, dimension, timestamp, txns
                    )
                    all_patterns.extend(patterns)
                    
                    # Extract Z-score from evidence
                    for pattern in patterns:
                        for evidence in pattern.evidence:
                            if "Z-score" in evidence.description:
                                z_score_max = max(z_score_max, evidence.value)
        
        # Detect other patterns
        all_patterns.extend(self.pattern_detector.detect_patterns(windowed_transactions, timestamp))
        
        logger.info(f"Detected {len(all_patterns)} pattern(s), max Z-score: {z_score_max:.2f}")
        
        # RAG: Query historical incidents for similar patterns
        similar_incidents = []
        rag_playbook = None
        if self.enable_rag and all_patterns:
            # Create incident signature from current state
            primary_pattern = all_patterns[0]
            current_signature = self.incident_store.create_signature_from_current_state(
                error_code=primary_pattern.type.value,  # FIX: Use .type not .pattern_type
                issuer=primary_pattern.affected_dimension.split("=")[1] if "=" in primary_pattern.affected_dimension else primary_pattern.affected_dimension.split(":")[1] if ":" in primary_pattern.affected_dimension else "UNKNOWN",
                payment_method="card",  # Would extract from patterns
                failure_rate=1.0 - aggregate_stats.success_rate,
                timestamp=timestamp
            )
            
            # Find similar historical incidents
            similar_incidents = self.incident_store.find_similar_incidents(current_signature, top_k=3)
            
            if similar_incidents:
                logger.info(f"Found {len(similar_incidents)} similar historical incident(s)")
                for incident, similarity in similar_incidents:
                    logger.info(f"  - {incident.incident_id} (similarity: {similarity:.0%})")
                
                # Retrieve RAG-based playbook
                if self.playbook_retriever:
                    current_telemetry = {
                        "success_rate": aggregate_stats.success_rate,
                        "avg_latency_ms": aggregate_stats.avg_latency_ms,
                        "total_transactions": aggregate_stats.total_transactions,
                        "failure_rate": 1.0 - aggregate_stats.success_rate
                    }
                    rag_playbook = self.playbook_retriever.retrieve_playbook(
                        current_signature, similar_incidents, current_telemetry
                    )
                    logger.info(f"RAG Playbook: {rag_playbook['recommended_action']} (confidence: {rag_playbook['confidence']:.0%})")
        
        # Generate hypotheses
        hypotheses = self.hypothesis_generator.generate_hypotheses(all_patterns)
        logger.info(f"Generated {len(hypotheses)} hypothesis/hypotheses")
        
        # Update beliefs
        beliefs = self.belief_manager.update_beliefs(hypotheses, timestamp)
        logger.info(f"System health: {beliefs.system_health_score:.2f}, "
                   f"uncertainty: {beliefs.uncertainty_level:.2f}")
        
        # 3. DECIDE (with NRV Optimization)
        logger.info("Phase 3: DECIDE (with NRV Optimization)")
        options = self.intervention_planner.generate_options(all_patterns, hypotheses)
        logger.info(f"Generated {len(options)} intervention option(s)")
        
        # Apply safety constraints if enabled
        if self.safety_constraints:
            # Estimate current fraud/compliance risk (would come from real metrics)
            fraud_risk = 0.0  # Placeholder
            compliance_risk = 0.0  # Placeholder
            
            filtered_options, blocked_reasons = self.safety_constraints.apply_constraints(
                options, fraud_risk, compliance_risk
            )
            
            if blocked_reasons:
                logger.warning(f"Safety constraints blocked {len(blocked_reasons)} option(s)")
                for reason in blocked_reasons:
                    logger.warning(f"  - {reason}")
            
            options = filtered_options
        
        # Make decision with NRV optimization
        decision = self.decision_policy.make_decision(
            options,
            beliefs,
            current_volume=aggregate_stats.total_transactions,
            current_success_rate=aggregate_stats.success_rate
        )
        logger.info(f"Decision: {'ACT' if decision.should_act else 'NO ACTION'}")
        
        # Log decision to audit log
        if self.audit_log and decision.should_act and decision.selected_option:
            nrv_value = 0.0
            if "NRV=" in decision.rationale:
                # Extract NRV from rationale
                try:
                    nrv_str = decision.rationale.split("NRV=$")[1].split()[0]
                    nrv_value = float(nrv_str)
                except:
                    pass
            
            self.audit_log.log_decision(
                decision_id=f"decision_{timestamp}",
                timestamp=timestamp,
                patterns=[p.type.value for p in all_patterns],
                hypotheses=[h.description for h in hypotheses],
                options=[o.type.value for o in options],
                selected_option=decision.selected_option.type.value,
                rationale=decision.rationale,
                confidence=1.0 - beliefs.uncertainty_level,
                nrv=nrv_value,
                requires_approval=decision.requires_human_approval
            )
        
        # Extract NRV details from decision rationale
        nrv_details = None
        if decision.should_act and decision.selected_option:
            logger.info(f"Selected: {decision.selected_option.type.value} on {decision.selected_option.target}")
            if decision.requires_human_approval:
                logger.warning("Requires human approval")
            
            # Calculate NRV details for explanation
            nrv_details = self.decision_policy.nrv_calculator.calculate_nrv(
                decision.selected_option,
                aggregate_stats.total_transactions,
                aggregate_stats.success_rate
            )
        
        # 4. ACT (with Adversarial Pre-Mortem)
        logger.info("Phase 4: ACT (with Pre-Mortem Safety Check)")
        pre_mortem_analysis = None
        if decision.should_act and decision.selected_option and not decision.requires_human_approval:
            # Execute with pre-mortem analysis
            current_state = {
                "success_rate": aggregate_stats.success_rate,
                "total_transactions": aggregate_stats.total_transactions,
                "system_health": beliefs.system_health_score
            }
            result, pre_mortem_analysis = self.action_executor.execute(
                decision.selected_option, current_state
            )
            if result.success:
                logger.info(f"Executed intervention {result.intervention_id}")
                
                # Log action to audit log
                if self.audit_log:
                    self.audit_log.log_action(
                        action_id=result.intervention_id,
                        timestamp=timestamp,
                        action_type=decision.selected_option.type.value,
                        target=decision.selected_option.target,
                        parameters=decision.selected_option.parameters,
                        success=True,
                        error=None,
                        pre_mortem_risk=pre_mortem_analysis.get('risk_score') if pre_mortem_analysis else None
                    )
            else:
                logger.error(f"Execution failed: {result.error}")
                
                # Log failed action to audit log
                if self.audit_log:
                    self.audit_log.log_action(
                        action_id=result.intervention_id,
                        timestamp=timestamp,
                        action_type=decision.selected_option.type.value,
                        target=decision.selected_option.target,
                        parameters=decision.selected_option.parameters,
                        success=False,
                        error=result.error,
                        pre_mortem_risk=None
                    )
        else:
            logger.info("No action executed")
        
        # 5. LEARN (simplified - would evaluate after observing outcomes)
        logger.info("Phase 5: LEARN")
        logger.info("Outcome evaluation deferred until next cycle")
        
        # Generate explanation with dual-output format
        explanation = self.explanation_generator.explain_decision(
            all_patterns,
            hypotheses,
            decision,
            nrv_details=nrv_details,
            z_score=z_score_max,
            pre_mortem=pre_mortem_analysis
        )
        
        # Add RAG context to explanation if available
        if rag_playbook:
            explanation.context["rag_playbook"] = rag_playbook
            explanation.context["similar_incidents"] = [
                {
                    "incident_id": inc.incident_id,
                    "similarity": sim,
                    "description": inc.description,
                    "lessons": inc.lessons_learned
                }
                for inc, sim in similar_incidents
            ]
        
        # Log dual-output format
        logger.info("\n" + "="*60)
        logger.info(explanation.format_dual_output())
        logger.info("="*60 + "\n")
        
        # Save state if enabled
        if self.state_manager:
            from payops_ai.models.state import AgentState, ObservationWindow as StateObservationWindow
            
            current_state = AgentState(
                current_beliefs=beliefs,
                active_interventions=self.action_executor.get_active_interventions(),
                recent_observations=StateObservationWindow(
                    transactions=[t.model_dump() for t in windowed_transactions[:10]],  # Keep last 10
                    time_range_ms=(
                        windowed_transactions[0].timestamp if windowed_transactions else timestamp,
                        timestamp
                    ),
                    aggregate_stats=aggregate_stats.model_dump()
                ),
                last_updated=timestamp,
                nrv_projection=nrv_details.get('nrv', 0.0) if nrv_details else 0.0,
                z_score=z_score_max,
                risk_acknowledged=pre_mortem_analysis is not None
            )
            
            self.state_manager.save_state(current_state)
        
        logger.info(f"=== Cycle {self.cycle_count} complete ===\n")
        
        return decision, explanation
    
    def run_continuous(self, cycle_interval_seconds: int = 60, max_cycles: Optional[int] = None):
        """Run agent continuously.
        
        Args:
            cycle_interval_seconds: Seconds between cycles
            max_cycles: Maximum cycles to run (None for infinite)
        """
        logger.info(f"Starting continuous operation (interval={cycle_interval_seconds}s)")
        
        cycles_run = 0
        while max_cycles is None or cycles_run < max_cycles:
            try:
                decision, explanation = self.execute_cycle()
                cycles_run += 1
                
                if max_cycles is None or cycles_run < max_cycles:
                    time.sleep(cycle_interval_seconds)
            except KeyboardInterrupt:
                logger.info("Interrupted by user")
                break
            except Exception as e:
                logger.error(f"Error in cycle: {e}", exc_info=True)
                time.sleep(cycle_interval_seconds)
        
        logger.info(f"Stopped after {cycles_run} cycles")
    
    def get_status(self) -> dict:
        """Get current agent status."""
        return {
            "cycle_count": self.cycle_count,
            "simulation_mode": self.simulation_mode,
            "active_interventions": len(self.action_executor.get_active_interventions()),
            "system_health": self.belief_manager.get_current_beliefs().system_health_score,
            "uncertainty": self.belief_manager.get_current_beliefs().uncertainty_level
        }
