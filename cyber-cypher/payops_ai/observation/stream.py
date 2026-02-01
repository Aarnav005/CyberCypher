"""Observation stream for ingesting payment signals."""

import logging
from typing import Optional, Dict, Any, List
from collections import deque

from payops_ai.models.transaction import TransactionSignal
from payops_ai.models.system_metrics import SystemMetrics
from payops_ai.observation.validator import DataValidator

logger = logging.getLogger(__name__)


class ObservationStream:
    """Manages ingestion of transaction signals and system metrics.
    
    Provides a stream interface for consuming real-time payment data.
    Validates incoming data and handles errors gracefully.
    """
    
    def __init__(self, max_buffer_size: int = 10000):
        """Initialize observation stream.
        
        Args:
            max_buffer_size: Maximum number of transactions to buffer
        """
        self.validator = DataValidator()
        self.transaction_buffer: deque[TransactionSignal] = deque(maxlen=max_buffer_size)
        self.latest_system_metrics: Optional[SystemMetrics] = None
        self._total_ingested = 0
        self._total_invalid = 0
    
    def ingest_transaction(self, data: Dict[str, Any]) -> bool:
        """Ingest a transaction signal.
        
        Args:
            data: Raw transaction data
            
        Returns:
            True if successfully ingested, False if invalid
        """
        signal = self.validator.validate_transaction(data)
        
        if signal is not None:
            self.transaction_buffer.append(signal)
            self._total_ingested += 1
            logger.debug(f"Ingested transaction {signal.transaction_id}")
            return True
        else:
            self._total_invalid += 1
            logger.warning(f"Rejected invalid transaction data")
            return False
    
    def ingest_transaction_batch(self, batch: List[Dict[str, Any]]) -> int:
        """Ingest a batch of transaction signals.
        
        Args:
            batch: List of raw transaction data
            
        Returns:
            Number of successfully ingested transactions
        """
        success_count = 0
        for data in batch:
            if self.ingest_transaction(data):
                success_count += 1
        
        logger.info(f"Ingested batch: {success_count}/{len(batch)} successful")
        return success_count
    
    def ingest_system_metrics(self, data: Dict[str, Any]) -> bool:
        """Ingest system metrics.
        
        Args:
            data: Raw system metrics data
            
        Returns:
            True if successfully ingested, False if invalid
        """
        metrics = self.validator.validate_system_metrics(data)
        
        if metrics is not None:
            self.latest_system_metrics = metrics
            logger.debug(f"Updated system metrics at {metrics.timestamp}")
            return True
        else:
            logger.warning(f"Rejected invalid system metrics")
            return False
    
    def add_transaction(self, transaction: TransactionSignal) -> None:
        """Add a transaction signal directly (for continuous stream integration).
        
        Args:
            transaction: Transaction signal to add
        """
        self.transaction_buffer.append(transaction)
        self._total_ingested += 1
        logger.debug(f"Added transaction {transaction.transaction_id}")
    
    def add_transaction_batch(self, transactions: List[TransactionSignal]) -> None:
        """Add a batch of transaction signals directly (for continuous stream integration).
        
        Args:
            transactions: List of transaction signals to add
        """
        self.transaction_buffer.extend(transactions)
        self._total_ingested += len(transactions)
        logger.debug(f"Added batch of {len(transactions)} transactions")
    
    def get_recent_transactions(self, count: Optional[int] = None) -> List[TransactionSignal]:
        """Get recent transactions from buffer.
        
        Args:
            count: Number of transactions to retrieve (None for all)
            
        Returns:
            List of recent transaction signals
        """
        if count is None:
            return list(self.transaction_buffer)
        else:
            # Get last N transactions
            return list(self.transaction_buffer)[-count:] if count <= len(self.transaction_buffer) else list(self.transaction_buffer)
    
    def get_latest_system_metrics(self) -> Optional[SystemMetrics]:
        """Get the latest system metrics."""
        return self.latest_system_metrics
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get stream statistics."""
        return {
            "total_ingested": self._total_ingested,
            "total_invalid": self._total_invalid,
            "buffer_size": len(self.transaction_buffer),
            "success_rate": self._total_ingested / (self._total_ingested + self._total_invalid) if (self._total_ingested + self._total_invalid) > 0 else 0.0,
            "quality_issues": len(self.validator.get_quality_issues())
        }
    
    def clear_buffer(self) -> None:
        """Clear the transaction buffer."""
        self.transaction_buffer.clear()
        logger.info("Cleared transaction buffer")
