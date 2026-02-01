"""Kafka Agent Demo: Run PayOps-AI agent with real-time Kafka stream.

This script runs the PayOps-AI agent consuming transactions from Kafka in real-time.
"""

import logging
import argparse
from payops_ai.streaming.kafka_orchestrator import KafkaAgentOrchestrator
from payops_ai.models.baseline import BaselineStats

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    parser = argparse.ArgumentParser(description='Run PayOps-AI agent with Kafka stream')
    parser.add_argument('--bootstrap-servers', default='localhost:9092', help='Kafka bootstrap servers')
    parser.add_argument('--topic', default='payment-transactions', help='Kafka topic')
    parser.add_argument('--group-id', default='payops-ai-agent', help='Consumer group ID')
    parser.add_argument('--cycle-interval', type=int, default=60, help='Seconds between agent cycles')
    parser.add_argument('--max-cycles', type=int, help='Maximum cycles to run (default: infinite)')
    parser.add_argument('--enable-rag', action='store_true', help='Enable RAG with Gemini')
    parser.add_argument('--gemini-key', help='Google Gemini API key')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("  PayOps-AI Agent with Kafka Streaming")
    print("=" * 80)
    print()
    print(f"Configuration:")
    print(f"  Bootstrap Servers: {args.bootstrap_servers}")
    print(f"  Topic: {args.topic}")
    print(f"  Consumer Group: {args.group_id}")
    print(f"  Cycle Interval: {args.cycle_interval}s")
    print(f"  Max Cycles: {args.max_cycles or 'infinite'}")
    print(f"  RAG Enabled: {args.enable_rag}")
    print()
    
    # Get Gemini API key
    gemini_api_key = None
    if args.enable_rag:
        gemini_api_key = args.gemini_key or "AIzaSyDfMtIt7Dg-EoySAGXgbs8q5MsSGwYVyTE"
        print(f"  RAG: Enabled with Gemini")
    else:
        print(f"  RAG: Disabled")
    print()
    
    # Initialize agent
    print("Initializing agent...")
    agent = KafkaAgentOrchestrator(
        kafka_bootstrap_servers=args.bootstrap_servers,
        kafka_topic=args.topic,
        kafka_group_id=args.group_id,
        window_duration_ms=300000,  # 5 minutes
        anomaly_threshold=2.0,
        min_confidence=0.6,
        max_blast_radius=0.5,
        simulation_mode=True,
        gemini_api_key=gemini_api_key
    )
    print("✓ Agent initialized")
    print()
    
    # Load baselines
    print("Loading baselines...")
    baselines = [
        BaselineStats(
            dimension="issuer:HDFC",
            success_rate=0.95,
            p50_latency_ms=100.0,
            p95_latency_ms=200.0,
            p99_latency_ms=500.0,
            avg_retry_count=0.5,
            sample_size=10000,
            period_start=1000000,
            period_end=2000000
        ),
        BaselineStats(
            dimension="issuer:ICICI",
            success_rate=0.94,
            p50_latency_ms=110.0,
            p95_latency_ms=220.0,
            p99_latency_ms=550.0,
            avg_retry_count=0.6,
            sample_size=8000,
            period_start=1000000,
            period_end=2000000
        ),
        BaselineStats(
            dimension="issuer:SBI",
            success_rate=0.93,
            p50_latency_ms=120.0,
            p95_latency_ms=240.0,
            p99_latency_ms=600.0,
            avg_retry_count=0.7,
            sample_size=7000,
            period_start=1000000,
            period_end=2000000
        ),
    ]
    
    for baseline in baselines:
        agent.baseline_manager.load_baseline(baseline.dimension, baseline)
    print(f"✓ Loaded {len(baselines)} baselines")
    print()
    
    # Show RAG memory
    if agent.enable_rag and agent.incident_store:
        stats = agent.incident_store.get_statistics()
        print(f"Historical Incident Store:")
        print(f"  • Total incidents: {stats['total_incidents']}")
        print(f"  • Successful resolutions: {stats['successful_resolutions']}")
        print(f"  • Unique issuers: {stats['unique_issuers']}")
        print()
    
    print("Starting agent with Kafka stream...")
    print("The agent will:")
    print("  1. Consume transactions from Kafka in real-time")
    print("  2. Execute agent cycles every", args.cycle_interval, "seconds")
    print("  3. Detect patterns and make decisions")
    if args.enable_rag:
        print("  4. Query historical incidents with RAG")
        print("  5. Apply lessons learned from past resolutions")
    print()
    print("Press Ctrl+C to stop")
    print()
    print("-" * 80)
    print()
    
    # Run agent
    try:
        agent.run_with_kafka_stream(
            cycle_interval_seconds=args.cycle_interval,
            max_cycles=args.max_cycles
        )
    except KeyboardInterrupt:
        print("\nStopped by user")
    
    # Show final stats
    print()
    print("-" * 80)
    print()
    print("Agent Statistics:")
    status = agent.get_status()
    print(f"  • Total cycles: {status['cycle_count']}")
    print(f"  • Transactions ingested: {agent.transactions_ingested}")
    print(f"  • System health: {status['system_health']:.2f}")
    print(f"  • Active interventions: {status['active_interventions']}")
    print()
    print("Agent stopped!")


if __name__ == "__main__":
    main()
