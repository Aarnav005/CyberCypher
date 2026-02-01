"""Kafka producer for payment transaction streams."""

import json
import logging
import time
from typing import Dict, Any, Optional
from kafka import KafkaProducer
from kafka.errors import KafkaError

from payops_ai.streaming.payment_generator import PaymentDataGenerator

logger = logging.getLogger(__name__)


class PaymentStreamProducer:
    """Produces payment transaction events to Kafka topic."""
    
    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        topic: str = "payment-transactions",
        generator: Optional[PaymentDataGenerator] = None
    ):
        """Initialize Kafka producer.
        
        Args:
            bootstrap_servers: Kafka bootstrap servers
            topic: Kafka topic name
            generator: Payment data generator (creates one if not provided)
        """
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.generator = generator or PaymentDataGenerator()
        
        # Initialize Kafka producer
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',  # Wait for all replicas
                retries=3,
                max_in_flight_requests_per_connection=1,  # Ensure ordering
            )
            logger.info(f"Kafka producer initialized (servers={bootstrap_servers}, topic={topic})")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            self.producer = None
    
    def send_transaction(self, transaction: Dict[str, Any]) -> bool:
        """Send a single transaction to Kafka.
        
        Args:
            transaction: Transaction data dictionary
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.producer:
            logger.warning("Kafka producer not initialized, skipping send")
            return False
        
        try:
            # Use transaction_id as key for partitioning
            key = transaction.get("transaction_id")
            
            # Send to Kafka
            future = self.producer.send(self.topic, key=key, value=transaction)
            
            # Wait for send to complete (with timeout)
            record_metadata = future.get(timeout=10)
            
            logger.debug(f"Sent transaction {key} to {record_metadata.topic}:{record_metadata.partition}:{record_metadata.offset}")
            return True
            
        except KafkaError as e:
            logger.error(f"Failed to send transaction: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending transaction: {e}")
            return False
    
    def stream_continuous(
        self,
        duration_seconds: Optional[int] = None,
        tps: Optional[int] = None,
        scenario: str = "normal"
    ):
        """Stream transactions continuously.
        
        Args:
            duration_seconds: Duration to stream (None for infinite)
            tps: Transactions per second (None for realistic based on time of day)
            scenario: Scenario to simulate (normal, hdfc_degradation, etc.)
        """
        if not self.producer:
            logger.error("Kafka producer not initialized, cannot stream")
            return
        
        # Set scenario
        self.generator.set_scenario(scenario)
        logger.info(f"Starting continuous stream (scenario={scenario}, duration={duration_seconds}s)")
        
        start_time = time.time()
        transactions_sent = 0
        
        try:
            while True:
                # Check duration
                if duration_seconds and (time.time() - start_time) >= duration_seconds:
                    break
                
                # Get TPS (realistic or specified)
                current_tps = tps or self.generator.get_realistic_tps()
                sleep_time = 1.0 / current_tps
                
                # Generate and send transaction
                transaction = self.generator.generate_transaction()
                if self.send_transaction(transaction):
                    transactions_sent += 1
                
                # Log progress every 100 transactions
                if transactions_sent % 100 == 0:
                    elapsed = time.time() - start_time
                    actual_tps = transactions_sent / elapsed if elapsed > 0 else 0
                    logger.info(f"Sent {transactions_sent} transactions (actual TPS: {actual_tps:.1f})")
                
                # Sleep to maintain TPS
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            logger.info("Stream interrupted by user")
        finally:
            elapsed = time.time() - start_time
            logger.info(f"Stream complete: {transactions_sent} transactions in {elapsed:.1f}s")
            self.close()
    
    def stream_batch(self, count: int, scenario: str = "normal"):
        """Stream a batch of transactions.
        
        Args:
            count: Number of transactions to send
            scenario: Scenario to simulate
        """
        if not self.producer:
            logger.error("Kafka producer not initialized, cannot stream")
            return
        
        self.generator.set_scenario(scenario)
        logger.info(f"Streaming batch of {count} transactions (scenario={scenario})")
        
        transactions_sent = 0
        for i in range(count):
            transaction = self.generator.generate_transaction()
            if self.send_transaction(transaction):
                transactions_sent += 1
            
            # Log progress
            if (i + 1) % 100 == 0:
                logger.info(f"Sent {i + 1}/{count} transactions")
        
        logger.info(f"Batch complete: {transactions_sent}/{count} transactions sent")
        self.close()
    
    def close(self):
        """Close Kafka producer."""
        if self.producer:
            logger.info("Flushing and closing Kafka producer...")
            self.producer.flush()
            self.producer.close()
            logger.info("Kafka producer closed")
