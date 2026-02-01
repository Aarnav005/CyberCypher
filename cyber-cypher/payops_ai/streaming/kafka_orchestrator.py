"""Kafka-integrated agent orchestrator for real-time streaming."""

import logging
from typing import Optional

from payops_ai.orchestrator import AgentOrchestrator
from payops_ai.streaming.kafka_consumer import PaymentStreamConsumer

logger = logging.getLogger(__name__)


class KafkaAgentOrchestrator(AgentOrchestrator):
    """Agent orchestrator with Kafka streaming integration."""
    
    def __init__(
        self,
        kafka_bootstrap_servers: str = "localhost:9092",
        kafka_topic: str = "payment-transactions",
        kafka_group_id: str = "payops-ai-agent",
        window_duration_ms: int = 300000,
        anomaly_threshold: float = 2.0,
        min_confidence: float = 0.7,
        max_blast_radius: float = 0.3,
        simulation_mode: bool = True,
        gemini_api_key: Optional[str] = None
    ):
        """Initialize Kafka-integrated orchestrator.
        
        Args:
            kafka_bootstrap_servers: Kafka bootstrap servers
            kafka_topic: Kafka topic to consume from
            kafka_group_id: Consumer group ID
            window_duration_ms: Observation window duration
            anomaly_threshold: Anomaly detection threshold
            min_confidence: Minimum confidence for autonomous action
            max_blast_radius: Maximum blast radius for autonomous action
            simulation_mode: If True, simulate actions without executing
            gemini_api_key: Google Gemini API key for RAG
        """
        # Initialize base orchestrator
        super().__init__(
            window_duration_ms=window_duration_ms,
            anomaly_threshold=anomaly_threshold,
            min_confidence=min_confidence,
            max_blast_radius=max_blast_radius,
            simulation_mode=simulation_mode,
            gemini_api_key=gemini_api_key
        )
        
        # Initialize Kafka consumer
        self.kafka_consumer = PaymentStreamConsumer(
            bootstrap_servers=kafka_bootstrap_servers,
            topic=kafka_topic,
            group_id=kafka_group_id,
            auto_offset_reset="latest"
        )
        
        self.transactions_ingested = 0
        
        logger.info(f"Kafka-integrated orchestrator initialized (topic={kafka_topic})")
    
    def _ingest_transaction(self, transaction: dict):
        """Ingest a transaction from Kafka stream.
        
        Args:
            transaction: Transaction data from Kafka
        """
        try:
            self.stream.ingest_transaction(transaction)
            self.transactions_ingested += 1
            
            # Log progress
            if self.transactions_ingested % 100 == 0:
                logger.info(f"Ingested {self.transactions_ingested} transactions from Kafka")
                
        except Exception as e:
            logger.error(f"Failed to ingest transaction {transaction.get('transaction_id')}: {e}")
    
    def run_with_kafka_stream(
        self,
        cycle_interval_seconds: int = 60,
        max_cycles: Optional[int] = None
    ):
        """Run agent with Kafka stream consumption.
        
        This runs two concurrent processes:
        1. Kafka consumer continuously ingesting transactions
        2. Agent executing cycles at regular intervals
        
        Args:
            cycle_interval_seconds: Seconds between agent cycles
            max_cycles: Maximum cycles to run (None for infinite)
        """
        import threading
        import time
        
        logger.info(f"Starting Kafka-integrated agent (cycle_interval={cycle_interval_seconds}s)")
        
        # Flag to stop threads
        stop_flag = threading.Event()
        
        # Thread 1: Kafka consumer
        def consume_stream():
            """Consume Kafka stream continuously."""
            try:
                self.kafka_consumer.consume_continuous(
                    callback=self._ingest_transaction,
                    max_messages=None  # Infinite
                )
            except Exception as e:
                logger.error(f"Kafka consumer error: {e}")
                stop_flag.set()
        
        # Thread 2: Agent cycles
        def run_agent_cycles():
            """Run agent cycles at regular intervals."""
            cycles_run = 0
            try:
                while not stop_flag.is_set() and (max_cycles is None or cycles_run < max_cycles):
                    # Execute agent cycle
                    decision, explanation = self.execute_cycle()
                    cycles_run += 1
                    
                    # Sleep until next cycle
                    if max_cycles is None or cycles_run < max_cycles:
                        time.sleep(cycle_interval_seconds)
                        
            except KeyboardInterrupt:
                logger.info("Agent cycles interrupted by user")
                stop_flag.set()
            except Exception as e:
                logger.error(f"Agent cycle error: {e}", exc_info=True)
                stop_flag.set()
        
        # Start threads
        consumer_thread = threading.Thread(target=consume_stream, daemon=True)
        agent_thread = threading.Thread(target=run_agent_cycles, daemon=False)
        
        consumer_thread.start()
        logger.info("Kafka consumer thread started")
        
        time.sleep(2)  # Give consumer time to connect
        
        agent_thread.start()
        logger.info("Agent cycle thread started")
        
        # Wait for agent thread to complete
        try:
            agent_thread.join()
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            stop_flag.set()
        
        # Cleanup
        logger.info(f"Shutting down (ingested {self.transactions_ingested} transactions)")
        self.kafka_consumer.close()
