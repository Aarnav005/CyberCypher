"""Sliding time window for transaction observations."""

import logging
from typing import List, Tuple
import statistics

from payops_ai.models.transaction import TransactionSignal, Outcome
from payops_ai.models.aggregate import AggregateStats

logger = logging.getLogger(__name__)


class ObservationWindow:
    """Maintains a sliding time window of recent transactions.
    
    Filters transactions by time range and calculates aggregate statistics.
    """
    
    def __init__(self, window_duration_ms: int = 300000):  # Default 5 minutes
        """Initialize observation window.
        
        Args:
            window_duration_ms: Window duration in milliseconds
        """
        self.window_duration_ms = window_duration_ms
        self.transactions: List[TransactionSignal] = []
        self._cached_stats: Optional[AggregateStats] = None
        self._stats_cache_timestamp: Optional[int] = None
    
    def update(self, transactions: List[TransactionSignal], current_time_ms: int) -> None:
        """Update window with new transactions and filter by time.
        
        Args:
            transactions: All available transactions
            current_time_ms: Current timestamp in milliseconds
        """
        # Filter transactions within the time window
        window_start = current_time_ms - self.window_duration_ms
        
        # FIX #1: Ensure we get enough transactions for statistical significance
        # If we have transactions, take at least the last 50 or all within window
        time_filtered = [
            txn for txn in transactions
            if window_start <= txn.timestamp <= current_time_ms
        ]
        
        # Ensure minimum sample size for statistical validity
        MIN_SAMPLE_SIZE = 50
        if len(time_filtered) < MIN_SAMPLE_SIZE and len(transactions) >= MIN_SAMPLE_SIZE:
            # Take last N transactions regardless of time window
            self.transactions = list(transactions[-MIN_SAMPLE_SIZE:])
            logger.debug(f"Using last {MIN_SAMPLE_SIZE} transactions (insufficient in time window)")
        else:
            self.transactions = time_filtered
        
        # Invalidate cache
        self._cached_stats = None
        self._stats_cache_timestamp = None
        
        logger.debug(f"Updated window: {len(self.transactions)} transactions (window: [{window_start}, {current_time_ms}])")
    
    def get_time_range(self) -> Tuple[int, int]:
        """Get the time range of transactions in the window.
        
        Returns:
            Tuple of (min_timestamp, max_timestamp)
        """
        if not self.transactions:
            return (0, 0)
        
        timestamps = [txn.timestamp for txn in self.transactions]
        return (min(timestamps), max(timestamps))
    
    def get_transactions(self) -> List[TransactionSignal]:
        """Get all transactions in the window."""
        return self.transactions.copy()
    
    def calculate_aggregate_stats(self) -> AggregateStats:
        """Calculate aggregate statistics for the window.
        
        Returns:
            AggregateStats with computed metrics
        """
        # Return cached stats if available
        if self._cached_stats is not None:
            return self._cached_stats
        
        if not self.transactions:
            # Return empty stats
            return AggregateStats(
                total_transactions=0,
                success_count=0,
                soft_fail_count=0,
                hard_fail_count=0,
                success_rate=0.0,
                avg_latency_ms=0.0,
                p95_latency_ms=0.0,
                p99_latency_ms=0.0,
                avg_retry_count=0.0,
                unique_issuers=0,
                unique_methods=0
            )
        
        # Count outcomes
        success_count = sum(1 for txn in self.transactions if txn.outcome == Outcome.SUCCESS)
        soft_fail_count = sum(1 for txn in self.transactions if txn.outcome == Outcome.SOFT_FAIL)
        hard_fail_count = sum(1 for txn in self.transactions if txn.outcome == Outcome.HARD_FAIL)
        total = len(self.transactions)
        
        # Calculate latency statistics
        latencies = [txn.latency_ms for txn in self.transactions]
        avg_latency = statistics.mean(latencies)
        
        # Calculate percentiles
        sorted_latencies = sorted(latencies)
        p95_index = int(0.95 * len(sorted_latencies))
        p99_index = int(0.99 * len(sorted_latencies))
        p95_latency = sorted_latencies[p95_index] if p95_index < len(sorted_latencies) else sorted_latencies[-1]
        p99_latency = sorted_latencies[p99_index] if p99_index < len(sorted_latencies) else sorted_latencies[-1]
        
        # Calculate retry statistics
        avg_retry = statistics.mean([txn.retry_count for txn in self.transactions])
        
        # Count unique dimensions
        unique_issuers = len(set(txn.issuer for txn in self.transactions))
        unique_methods = len(set(txn.payment_method for txn in self.transactions))
        
        stats = AggregateStats(
            total_transactions=total,
            success_count=success_count,
            soft_fail_count=soft_fail_count,
            hard_fail_count=hard_fail_count,
            success_rate=success_count / total if total > 0 else 0.0,
            avg_latency_ms=avg_latency,
            p95_latency_ms=p95_latency,
            p99_latency_ms=p99_latency,
            avg_retry_count=avg_retry,
            unique_issuers=unique_issuers,
            unique_methods=unique_methods
        )
        
        # Cache the stats
        self._cached_stats = stats
        
        return stats
    
    def filter_by_dimension(self, dimension: str, value: str) -> List[TransactionSignal]:
        """Filter transactions by a specific dimension.
        
        Args:
            dimension: Dimension name (e.g., 'issuer', 'payment_method')
            value: Dimension value to filter by
            
        Returns:
            Filtered list of transactions
        """
        if dimension == "issuer":
            return [txn for txn in self.transactions if txn.issuer == value]
        elif dimension == "payment_method":
            return [txn for txn in self.transactions if txn.payment_method.value == value]
        elif dimension == "merchant_id":
            return [txn for txn in self.transactions if txn.merchant_id == value]
        elif dimension == "geography":
            return [txn for txn in self.transactions if txn.geography == value]
        else:
            logger.warning(f"Unknown dimension: {dimension}")
            return []
    
    def get_success_rate_by_dimension(self, dimension: str) -> dict[str, float]:
        """Calculate success rate grouped by dimension.
        
        Args:
            dimension: Dimension to group by
            
        Returns:
            Dictionary mapping dimension values to success rates
        """
        from collections import defaultdict
        
        counts = defaultdict(lambda: {"success": 0, "total": 0})
        
        for txn in self.transactions:
            if dimension == "issuer":
                key = txn.issuer
            elif dimension == "payment_method":
                key = txn.payment_method.value
            elif dimension == "merchant_id":
                key = txn.merchant_id
            else:
                continue
            
            counts[key]["total"] += 1
            if txn.outcome == Outcome.SUCCESS:
                counts[key]["success"] += 1
        
        return {
            key: data["success"] / data["total"] if data["total"] > 0 else 0.0
            for key, data in counts.items()
        }


from typing import Optional
