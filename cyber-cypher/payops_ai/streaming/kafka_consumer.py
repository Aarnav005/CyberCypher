"""Kafka consumer for payment transaction streams."""

import json
import logging
from typing import Callable, Optional, Dict, Any
from kafka import KafkaConsumer
from kafka.errors import KafkaError

logger = logging.getLogger(__name__)


class PaymentStreamConsumer:
    """Consumes payment transaction events from Kafka topic."""
    
    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        topic: str = "payment-transactions",
        group_id: str = "payops-ai-agent",
        auto_offset_reset: str = "latest"
    ):
        """Initialize Kafka consumer.
        
        Args:
            bootstrap_servers: Kafka bootstrap servers
            topic: Kafka topic name
            group_id: Consumer group ID
            auto_offset_reset: Where to start reading (earliest or latest)
        """
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.group_id = group_id
        
        # Initialize Kafka consumer
        try:
            self.consumer = KafkaConsumer(
                topic,
                bootstrap_servers=bootstrap_servers,
                group_id=group_id,
                auto_offset_reset=auto_offset_reset,
                enable_auto_commit=True,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
            )
            logger.info(f"Kafka consumer initialized (servers={bootstrap_servers}, topic={topic}, group={group_id})")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka consumer: {e}")
            self.consumer = None
    
    def consume_continuous(
        self,
        callback: Callable[[Dict[str, Any]], None],
        max_messages: Optional[int] = None
    ):
        """Consume messages continuously and invoke callback for each.
        
        Args:
            callback: Function to call for each transaction
            max_messages: Maximum messages to consume (None for infinite)
        """
        if not self.consumer:
            logger.error("Kafka consumer not initialized, cannot consume")
            return
        
        logger.info(f"Starting continuous consumption (max_messages={max_messages})")
        
        messages_consumed = 0
        
        try:
            for message in self.consumer:
                # Extract transaction data
                transaction = message.value
                
                # Invoke callback
                try:
                    callback(transaction)
                    messages_consumed += 1
                    
                    # Log progress
                    if messages_consumed % 100 == 0:
                        logger.info(f"Consumed {messages_consumed} messages")
                    
                    # Check max messages
                    if max_messages and messages_consumed >= max_messages:
                        break
                        
                except Exception as e:
                    logger.error(f"Error in callback for transaction {transaction.get('transaction_id')}: {e}")
                    
        except KeyboardInterrupt:
            logger.info("Consumption interrupted by user")
        finally:
            logger.info(f"Consumption complete: {messages_consumed} messages processed")
            self.close()
    
    def consume_batch(
        self,
        count: int,
        timeout_ms: int = 10000
    ) -> list[Dict[str, Any]]:
        """Consume a batch of messages.
        
        Args:
            count: Number of messages to consume
            timeout_ms: Timeout for polling
            
        Returns:
            List of transaction dictionaries
        """
        if not self.consumer:
            logger.error("Kafka consumer not initialized, cannot consume")
            return []
        
        logger.info(f"Consuming batch of {count} messages")
        
        transactions = []
        
        try:
            while len(transactions) < count:
                # Poll for messages
                messages = self.consumer.poll(timeout_ms=timeout_ms, max_records=count - len(transactions))
                
                if not messages:
                    logger.warning(f"No messages received, timeout after {timeout_ms}ms")
                    break
                
                # Extract transactions
                for topic_partition, records in messages.items():
                    for record in records:
                        transactions.append(record.value)
                
                logger.info(f"Consumed {len(transactions)}/{count} messages")
                
        except Exception as e:
            logger.error(f"Error consuming batch: {e}")
        
        return transactions
    
    def close(self):
        """Close Kafka consumer."""
        if self.consumer:
            logger.info("Closing Kafka consumer...")
            self.consumer.close()
            logger.info("Kafka consumer closed")
