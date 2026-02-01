"""Demo script for continuous payment stream with stochastic drift and closed-loop feedback."""

import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from payops_ai.orchestrator import AgentOrchestrator
from payops_ai.streaming.drift_engine import StochasticDriftEngine, DriftConfig
from payops_ai.streaming.continuous_generator import ContinuousPaymentGenerator
from payops_ai.streaming.feedback_controller import FeedbackController
from payops_ai.streaming.continuous_loop import ContinuousAgentLoop, LoopConfig
from payops_ai.streaming.config_loader import ConfigLoader


def setup_logging(log_level: str = "INFO"):
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('continuous_stream.log')
        ]
    )


def main():
    """Run continuous payment stream demo."""
    
    print("="*80)
    print("CONTINUOUS PAYMENT STREAM DEMO")
    print("="*80)
    print()
    print("This demo runs a continuous payment stream where:")
    print("  - Issuer health drifts stochastically (Ornstein-Uhlenbeck process)")
    print("  - Failures emerge naturally from parameter drift")
    print("  - Agent detects patterns and intervenes")
    print("  - Interventions affect future transaction generation (closed-loop)")
    print("  - No scenario resets - continuous operation with rolling baselines")
    print()
    print("Press Ctrl+C to stop gracefully")
    print("="*80)
    print()
    
    # Load configuration
    try:
        config = ConfigLoader.load('continuous_stream_config.yaml')
        print(f"Loaded configuration from continuous_stream_config.yaml")
    except FileNotFoundError:
        print("Config file not found, using defaults")
        config = ConfigLoader.get_default_config()
    
    # Setup logging
    setup_logging(config.log_level)
    logger = logging.getLogger(__name__)
    
    logger.info("Initializing continuous stream components...")
    
    # 1. Create drift engine
    drift_config = DriftConfig(
        theta=config.drift_theta,
        sigma=config.drift_sigma,
        mean_success=config.drift_mean_success,
        mean_latency=config.drift_mean_latency,
        mean_retry=config.drift_mean_retry,
        sigma_success=config.drift_sigma_success,
        sigma_latency=config.drift_sigma_latency,
        sigma_retry=config.drift_sigma_retry,
        retry_spike_prob=config.drift_retry_spike_prob,
        retry_spike_magnitude=config.drift_retry_spike_magnitude,
        retry_decay_rate=config.drift_retry_decay_rate
    )
    drift_engine = StochasticDriftEngine(drift_config)
    
    # Add issuers
    for issuer_name, issuer_config in config.issuers.items():
        drift_engine.add_issuer(
            issuer_name,
            initial_success=issuer_config['initial_success'],
            initial_latency=issuer_config['initial_latency'],
            initial_retry_prob=issuer_config['initial_retry_prob']
        )
    
    # Set time scale
    drift_engine.set_time_scale(config.time_scale)
    
    # 2. Create continuous payment generator
    generator = ContinuousPaymentGenerator(
        drift_engine=drift_engine,
        transaction_rate=config.transaction_rate,
        buffer_size=config.buffer_size
    )
    
    # 3. Create feedback controller
    feedback = FeedbackController(generator)
    
    # 4. Create agent orchestrator
    orchestrator = AgentOrchestrator(
        window_duration_ms=config.window_duration_ms,
        anomaly_threshold=config.anomaly_threshold,
        min_confidence=config.min_confidence,
        max_blast_radius=config.max_blast_radius,
        simulation_mode=True,
        gemini_api_key=None,  # Disable RAG for demo
        enable_state_persistence=True,
        enable_audit_logging=True,
        enable_safety_constraints=True,
        min_action_frequency_cycles=config.min_action_frequency_cycles
    )
    
    # 5. Create continuous loop
    loop_config = LoopConfig(
        cycle_interval=config.cycle_interval,
        loop_rate=config.loop_rate,
        max_duration=config.duration_seconds,
        checkpoint_cycles=config.checkpoint_cycles
    )
    
    continuous_loop = ContinuousAgentLoop(
        orchestrator=orchestrator,
        drift_engine=drift_engine,
        generator=generator,
        feedback=feedback,
        config=loop_config
    )
    
    # 6. Run continuous loop
    logger.info("Starting continuous loop...")
    print("\nStarting continuous stream... (Press Ctrl+C to stop)\n")
    
    try:
        continuous_loop.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error in continuous loop: {e}", exc_info=True)
    
    print("\n" + "="*80)
    print("DEMO COMPLETE")
    print("="*80)
    print(f"Total cycles: {continuous_loop.cycle_count}")
    print(f"Total transactions: {continuous_loop.total_transactions}")
    print(f"Check continuous_stream.log for detailed logs")
    print("="*80)


if __name__ == "__main__":
    main()
