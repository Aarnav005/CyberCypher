"""Run PayOps-AI Agent in Production Mode

This script demonstrates the complete autonomous agent running with:
- State persistence
- Audit logging
- Safety constraints
- RAG integration
- Real-time decision making
"""

import logging
import time
from payops_ai.config import config
from payops_ai.orchestrator import AgentOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def simulate_payment_stream(agent: AgentOrchestrator, scenario: str = "normal"):
    """Simulate payment transactions for different scenarios."""
    timestamp = int(time.time() * 1000)
    
    if scenario == "normal":
        # Normal operations - high success rate
        for i in range(50):
            signal = {
                "transaction_id": f"txn_normal_{i}",
                "timestamp": timestamp + i * 100,
                "merchant_id": f"merchant_{i % 10}",
                "amount": 100.0 + (i % 50),
                "payment_method": "card",
                "issuer": ["HDFC", "ICICI", "SBI", "AXIS"][i % 4],
                "outcome": "success" if i % 10 != 0 else "soft_fail",
                "latency_ms": 150 + (i % 50),
                "error_code": "TIMEOUT" if i % 10 == 0 else None,
                "retry_count": 1 if i % 10 == 0 else 0,
                "geography": "IN"
            }
            agent.stream.ingest_transaction(signal)
        logger.info("✓ Simulated 50 normal transactions (90% success rate)")
    
    elif scenario == "issuer_outage":
        # HDFC issuer experiencing major outage
        for i in range(100):
            is_hdfc = i % 2 == 0
            is_failure = is_hdfc and (i % 3 != 0)  # HDFC has 66% failure rate
            
            signal = {
                "transaction_id": f"txn_outage_{i}",
                "timestamp": timestamp + i * 50,
                "merchant_id": f"merchant_{i % 10}",
                "amount": 100.0 + (i % 50),
                "payment_method": "card",
                "issuer": "HDFC" if is_hdfc else "ICICI",
                "outcome": "hard_fail" if is_failure else "success",
                "latency_ms": 500 if is_failure else 150,
                "error_code": "ISSUER_DOWN" if is_failure else None,
                "retry_count": 3 if is_failure else 0,
                "geography": "IN"
            }
            agent.stream.ingest_transaction(signal)
        logger.info("✓ Simulated 100 transactions with HDFC outage (HDFC: 33% success, ICICI: 100% success)")
    
    elif scenario == "retry_storm":
        # Retry storm - excessive retries causing system load
        for i in range(80):
            is_retry_storm = i % 3 == 0
            
            signal = {
                "transaction_id": f"txn_retry_{i}",
                "timestamp": timestamp + i * 30,
                "merchant_id": "merchant_123",
                "amount": 100.0,
                "payment_method": "card",
                "issuer": "HDFC",
                "outcome": "soft_fail" if is_retry_storm else "success",
                "latency_ms": 200,
                "error_code": "TIMEOUT" if is_retry_storm else None,
                "retry_count": 5 if is_retry_storm else 0,
                "geography": "IN"
            }
            agent.stream.ingest_transaction(signal)
        logger.info("✓ Simulated 80 transactions with retry storm (33% experiencing 5+ retries)")
    
    elif scenario == "gradual_degradation":
        # Gradual degradation - success rate slowly declining
        for i in range(100):
            # Success rate: 100% -> 90% -> 80% -> 70%
            failure_threshold = 100 - (i // 25) * 10
            is_failure = (i % 100) >= failure_threshold
            
            signal = {
                "transaction_id": f"txn_degrade_{i}",
                "timestamp": timestamp + i * 60,
                "merchant_id": f"merchant_{i % 5}",
                "amount": 100.0,
                "payment_method": "card",
                "issuer": "HDFC",
                "outcome": "soft_fail" if is_failure else "success",
                "latency_ms": 150 + (i // 10) * 20,  # Latency also increasing
                "error_code": "TIMEOUT" if is_failure else None,
                "retry_count": 1 if is_failure else 0,
                "geography": "IN"
            }
            agent.stream.ingest_transaction(signal)
        logger.info("✓ Simulated 100 transactions with gradual degradation (100% -> 70% success)")


def main():
    """Run the PayOps-AI agent with multiple scenarios."""
    
    print("=" * 80)
    print("🚀 PayOps-AI Agent - Production Mode")
    print("=" * 80)
    print()
    
    # Initialize agent with all production features
    print("📋 Initializing Agent...")
    agent = AgentOrchestrator(
        window_duration_ms=300000,  # 5 minutes
        anomaly_threshold=2.0,
        min_confidence=0.7,
        max_blast_radius=0.3,
        simulation_mode=True,  # Set to False for real execution
        gemini_api_key=config.gemini_api_key,
        enable_state_persistence=True,
        enable_audit_logging=True,
        enable_safety_constraints=True
    )
    
    print(f"   ✓ Agent initialized")
    print(f"   ✓ State Persistence: Enabled")
    print(f"   ✓ Audit Logging: Enabled")
    print(f"   ✓ Safety Constraints: Enabled")
    print(f"   ✓ RAG: {'Enabled' if agent.enable_rag else 'Disabled'}")
    print(f"   ✓ Historical Incidents: {len(agent.incident_store.incidents)}")
    print()
    
    # Scenario 1: Normal Operations
    print("=" * 80)
    print("📊 SCENARIO 1: Normal Operations")
    print("=" * 80)
    simulate_payment_stream(agent, "normal")
    print("\n🔄 Running Agent Cycle...")
    decision1, explanation1 = agent.execute_cycle()
    print(f"\n✅ Decision: {'ACT' if decision1.should_act else 'NO ACTION'}")
    print(f"   Confidence: {explanation1.confidence:.2%}")
    print(f"   Executive Summary: {explanation1.executive_summary}")
    print()
    
    # Scenario 2: Issuer Outage
    print("=" * 80)
    print("⚠️  SCENARIO 2: HDFC Issuer Outage")
    print("=" * 80)
    simulate_payment_stream(agent, "issuer_outage")
    print("\n🔄 Running Agent Cycle...")
    decision2, explanation2 = agent.execute_cycle()
    print(f"\n✅ Decision: {'ACT' if decision2.should_act else 'NO ACTION'}")
    print(f"   Confidence: {explanation2.confidence:.2%}")
    print(f"   Executive Summary: {explanation2.executive_summary}")
    if decision2.should_act and decision2.selected_option:
        print(f"\n🎯 Recommended Action:")
        print(f"   Type: {decision2.selected_option.type.value}")
        print(f"   Target: {decision2.selected_option.target}")
        print(f"   Blast Radius: {decision2.selected_option.blast_radius:.2%}")
        print(f"   NRV: ${explanation2.action_json.get('nrv', 0):.2f}")
    print()
    
    # Scenario 3: Retry Storm
    print("=" * 80)
    print("🌪️  SCENARIO 3: Retry Storm")
    print("=" * 80)
    simulate_payment_stream(agent, "retry_storm")
    print("\n🔄 Running Agent Cycle...")
    decision3, explanation3 = agent.execute_cycle()
    print(f"\n✅ Decision: {'ACT' if decision3.should_act else 'NO ACTION'}")
    print(f"   Confidence: {explanation3.confidence:.2%}")
    print(f"   Executive Summary: {explanation3.executive_summary}")
    if decision3.should_act and decision3.selected_option:
        print(f"\n🎯 Recommended Action:")
        print(f"   Type: {decision3.selected_option.type.value}")
        print(f"   Target: {decision3.selected_option.target}")
        print(f"   Blast Radius: {decision3.selected_option.blast_radius:.2%}")
    print()
    
    # Scenario 4: Gradual Degradation
    print("=" * 80)
    print("📉 SCENARIO 4: Gradual Degradation")
    print("=" * 80)
    simulate_payment_stream(agent, "gradual_degradation")
    print("\n🔄 Running Agent Cycle...")
    decision4, explanation4 = agent.execute_cycle()
    print(f"\n✅ Decision: {'ACT' if decision4.should_act else 'NO ACTION'}")
    print(f"   Confidence: {explanation4.confidence:.2%}")
    print(f"   Executive Summary: {explanation4.executive_summary}")
    if decision4.should_act and decision4.selected_option:
        print(f"\n🎯 Recommended Action:")
        print(f"   Type: {decision4.selected_option.type.value}")
        print(f"   Target: {decision4.selected_option.target}")
        print(f"   Blast Radius: {decision4.selected_option.blast_radius:.2%}")
    print()
    
    # Final Summary
    print("=" * 80)
    print("📈 FINAL SUMMARY")
    print("=" * 80)
    status = agent.get_status()
    print(f"   Total Cycles: {status['cycle_count']}")
    print(f"   System Health: {status['system_health']:.2f}")
    print(f"   Uncertainty: {status['uncertainty']:.2f}")
    print(f"   Active Interventions: {status['active_interventions']}")
    print()
    print("📁 Generated Files:")
    print(f"   State: .payops_state/current_state.json")
    print(f"   Audit Log: .payops_logs/audit_*.jsonl")
    print(f"   Backups: .payops_state/backups/")
    print()
    print("✅ All scenarios complete!")
    print()


if __name__ == "__main__":
    main()
