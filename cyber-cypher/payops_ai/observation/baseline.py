"""Baseline statistics manager with EWMA rolling baselines."""

import logging
from typing import Dict, Optional, List
from collections import defaultdict

from payops_ai.models.baseline import BaselineStats, RollingBaseline
from payops_ai.models.transaction import TransactionSignal, Outcome

logger = logging.getLogger(__name__)


class BaselineManager:
    """Manages historical baseline statistics with rolling EWMA updates.
    
    Maintains both static baselines and rolling baselines for anomaly detection.
    """
    
    def __init__(self, alpha: float = 0.2):
        """Initialize baseline manager.
        
        Args:
            alpha: EWMA smoothing factor (0.0-1.0, higher = more weight on recent data)
        """
        self.baselines: Dict[str, BaselineStats] = {}
        self.rolling_baselines: Dict[str, RollingBaseline] = {}
        self.alpha = alpha
    
    def load_baseline(self, dimension: str, stats: BaselineStats) -> None:
        """Load baseline statistics for a dimension.
        
        Args:
            dimension: Dimension identifier (e.g., 'issuer:HDFC', 'method:UPI')
            stats: Baseline statistics
        """
        self.baselines[dimension] = stats
        logger.info(f"Loaded baseline for {dimension}")
    
    def get_baseline(self, dimension: str) -> Optional[BaselineStats]:
        """Get baseline statistics for a dimension.
        
        Args:
            dimension: Dimension identifier
            
        Returns:
            BaselineStats if available, None otherwise
        """
        return self.baselines.get(dimension)
    
    def get_rolling_baseline(self, dimension: str) -> Optional[RollingBaseline]:
        """Get rolling baseline for a dimension.
        
        Args:
            dimension: Dimension identifier
            
        Returns:
            RollingBaseline if available, None otherwise
        """
        return self.rolling_baselines.get(dimension)
    
    def update_rolling_baselines(self, transactions: List[TransactionSignal], timestamp: int) -> None:
        """Update rolling baselines with new transaction batch.
        
        Args:
            transactions: List of transactions to process
            timestamp: Current timestamp
        """
        if not transactions:
            return
        
        # Group transactions by dimension
        by_issuer = defaultdict(list)
        by_method = defaultdict(list)
        
        for txn in transactions:
            by_issuer[f"issuer:{txn.issuer}"].append(txn)
            by_method[f"method:{txn.payment_method.value}"].append(txn)
        
        # Update issuer baselines
        for dimension, txns in by_issuer.items():
            self._update_dimension_baseline(dimension, txns, timestamp)
        
        # Update method baselines
        for dimension, txns in by_method.items():
            self._update_dimension_baseline(dimension, txns, timestamp)
        
        # Update global baseline
        self._update_dimension_baseline("global", transactions, timestamp)
    
    def _update_dimension_baseline(self, dimension: str, transactions: List[TransactionSignal], timestamp: int) -> None:
        """Update rolling baseline for a specific dimension.
        
        Args:
            dimension: Dimension identifier
            transactions: Transactions for this dimension
            timestamp: Current timestamp
        """
        if not transactions:
            return
        
        # Calculate current metrics
        success_count = sum(1 for txn in transactions if txn.outcome == Outcome.SUCCESS)
        success_rate = success_count / len(transactions)
        avg_latency = sum(txn.latency_ms for txn in transactions) / len(transactions)
        avg_retry = sum(txn.retry_count for txn in transactions) / len(transactions)
        
        # Get or create rolling baseline
        if dimension not in self.rolling_baselines:
            self.rolling_baselines[dimension] = RollingBaseline(
                dimension=dimension,
                last_updated=timestamp,
                alpha=self.alpha
            )
        
        # Update rolling baseline
        baseline = self.rolling_baselines[dimension]
        baseline.update(success_rate, avg_latency, avg_retry, timestamp)
        
        logger.debug(f"Updated rolling baseline for {dimension}: "
                    f"success_rate={baseline.success_rate_ewma:.3f}, "
                    f"latency={baseline.latency_ewma:.1f}ms, "
                    f"samples={baseline.sample_count}")
    
    def has_baseline(self, dimension: str) -> bool:
        """Check if baseline exists for a dimension.
        
        Args:
            dimension: Dimension identifier
            
        Returns:
            True if baseline exists
        """
        return dimension in self.baselines or dimension in self.rolling_baselines
    
    def get_all_dimensions(self) -> list[str]:
        """Get all dimensions with baselines."""
        # Combine static and rolling baseline dimensions
        all_dims = set(self.baselines.keys()) | set(self.rolling_baselines.keys())
        return list(all_dims)
    
    def clear(self) -> None:
        """Clear all baselines."""
        self.baselines.clear()
        self.rolling_baselines.clear()
        logger.info("Cleared all baselines")
