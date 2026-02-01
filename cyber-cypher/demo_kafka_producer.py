"""Kafka Producer Demo: Stream realistic payment transactions.

This script simulates a production payment gateway streaming transactions to Kafka.
"""

import logging
import argparse
from payops_ai.streaming.kafka_producer import PaymentStreamProducer
from payops_ai.streaming.payment_generator import PaymentDataGenerator

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    parser = argparse.ArgumentParser(description='Stream payment transactions to Kafka')
    parser.add_argument('--bootstrap-servers', default='localhost:9092', help='Kafka bootstrap servers')
    parser.add_argument('--topic', default='payment-transactions', help='Kafka topic')
    parser.add_argument('--scenario', default='normal', 
                       choices=['normal', 'hdfc_degradation', 'retry_storm', 'method_fatigue', 'black_friday'],
                       help='Scenario to simulate')
    parser.add_argument('--duration', type=int, default=300, help='Duration in seconds (0 for infinite)')
    parser.add_argument('--tps', type=int, help='Transactions per second (default: realistic based on time)')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("  Kafka Payment Stream Producer")
    print("=" * 80)
    print()
    print(f"Configuration:")
    print(f"  Bootstrap Servers: {args.bootstrap_servers}")
    print(f"  Topic: {args.topic}")
    print(f"  Scenario: {args.scenario}")
    print(f"  Duration: {args.duration}s {'(infinite)' if args.duration == 0 else ''}")
    print(f"  TPS: {args.tps or 'realistic (time-based)'}")
    print()
    
    # Initialize producer
    generator = PaymentDataGenerator()
    producer = PaymentStreamProducer(
        bootstrap_servers=args.bootstrap_servers,
        topic=args.topic,
        generator=generator
    )
    
    # Show scenario details
    scenario_config = generator.scenarios[args.scenario]
    print(f"Scenario Details ({args.scenario}):")
    print(f"  Success Rate: {scenario_config['success_rate']:.0%}")
    print(f"  Avg Latency: {scenario_config['avg_latency']}ms")
    print(f"  Retry Rate: {scenario_config['retry_rate']:.0%}")
    if 'affected_issuer' in scenario_config:
        print(f"  Affected Issuer: {scenario_config['affected_issuer']}")
    if 'affected_method' in scenario_config:
        print(f"  Affected Method: {scenario_config['affected_method']}")
    print()
    
    print("Starting stream...")
    print("Press Ctrl+C to stop")
    print()
    
    # Stream transactions
    try:
        duration = None if args.duration == 0 else args.duration
        producer.stream_continuous(
            duration_seconds=duration,
            tps=args.tps,
            scenario=args.scenario
        )
    except KeyboardInterrupt:
        print("\nStopped by user")
    
    print()
    print("Stream complete!")


if __name__ == "__main__":
    main()
