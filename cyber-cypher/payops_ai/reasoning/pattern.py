"""Pattern detection for payment signals."""

import logging
from typing import List
from collections import defaultdict

from payops_ai.models.transaction import TransactionSignal, Outcome
from payops_ai.models.pattern import DetectedPattern, PatternType, Evidence

logger = logging.getLogger(__name__)


class PatternDetector:
    """Detects patterns in payment behavior."""
    
    def __init__(self):
        """Initialize pattern detector."""
        pass
    
    def detect_retry_storm(
        self,
        transactions: List[TransactionSignal],
        timestamp: int,
        threshold: float = 2.0
    ) -> List[DetectedPattern]:
        """Detect retry storm patterns."""
        if len(transactions) < 5:  # Need minimum sample
            return []
        
        avg_retry = sum(txn.retry_count for txn in transactions) / len(transactions)
        high_retry_count = sum(1 for txn in transactions if txn.retry_count >= 3)
        high_retry_pct = high_retry_count / len(transactions)
        
        # FIX #3: Detect retry storm if >20% of transactions have 3+ retries
        if avg_retry > threshold or high_retry_pct > 0.20:
            evidence = [
                Evidence(
                    type="statistical",
                    description=f"Average retry count: {avg_retry:.2f}, {high_retry_pct:.1%} with 3+ retries",
                    value=avg_retry,
                    timestamp=timestamp,
                    source="pattern_detector"
                )
            ]
            
            pattern = DetectedPattern(
                type=PatternType.RETRY_STORM,
                affected_dimension="system",
                severity=min(max(avg_retry / (threshold * 2), high_retry_pct), 1.0),
                evidence=evidence,
                detected_at=timestamp
            )
            logger.info(f"Detected retry storm: avg={avg_retry:.2f}, high_retry={high_retry_pct:.1%}")
            return [pattern]
        
        return []
    
    def detect_issuer_degradation(
        self,
        transactions: List[TransactionSignal],
        timestamp: int
    ) -> List[DetectedPattern]:
        """Detect issuer-specific degradation."""
        if len(transactions) < 5:  # Need minimum sample
            return []
            
        issuer_stats = defaultdict(lambda: {"total": 0, "failed": 0})
        
        for txn in transactions:
            issuer_stats[txn.issuer]["total"] += 1
            if txn.outcome != Outcome.SUCCESS:
                issuer_stats[txn.issuer]["failed"] += 1
        
        patterns = []
        for issuer, stats in issuer_stats.items():
            # FIX #3: Lower threshold from 10 to 5 for faster detection
            if stats["total"] >= 5:
                failure_rate = stats["failed"] / stats["total"]
                # FIX #3: Lower threshold from 30% to 20% for earlier detection
                if failure_rate > 0.20:
                    evidence = [
                        Evidence(
                            type="statistical",
                            description=f"Failure rate: {failure_rate:.2%} ({stats['failed']}/{stats['total']} transactions)",
                            value=failure_rate,
                            timestamp=timestamp,
                            source="pattern_detector"
                        )
                    ]
                    
                    pattern = DetectedPattern(
                        type=PatternType.ISSUER_DEGRADATION,
                        affected_dimension=f"issuer:{issuer}",
                        severity=failure_rate,
                        evidence=evidence,
                        detected_at=timestamp
                    )
                    patterns.append(pattern)
                    logger.info(f"Detected issuer degradation: {issuer} at {failure_rate:.2%} failure rate")
        
        return patterns
    
    def detect_method_fatigue(
        self,
        transactions: List[TransactionSignal],
        timestamp: int
    ) -> List[DetectedPattern]:
        """Detect method fatigue patterns."""
        method_stats = defaultdict(lambda: {"total": 0, "failed": 0})
        
        for txn in transactions:
            method_stats[txn.payment_method.value]["total"] += 1
            if txn.outcome != Outcome.SUCCESS:
                method_stats[txn.payment_method.value]["failed"] += 1
        
        patterns = []
        for method, stats in method_stats.items():
            if stats["total"] >= 10:
                failure_rate = stats["failed"] / stats["total"]
                if failure_rate > 0.4:  # 40% failure rate
                    evidence = [
                        Evidence(
                            type="statistical",
                            description=f"Method failure rate: {failure_rate:.2%}",
                            value=failure_rate,
                            timestamp=timestamp,
                            source="pattern_detector"
                        )
                    ]
                    
                    pattern = DetectedPattern(
                        type=PatternType.METHOD_FATIGUE,
                        affected_dimension=f"method:{method}",
                        severity=failure_rate,
                        evidence=evidence,
                        detected_at=timestamp
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def detect_patterns(
        self,
        transactions: List[TransactionSignal],
        timestamp: int
    ) -> List[DetectedPattern]:
        """Detect all patterns."""
        patterns = []
        patterns.extend(self.detect_retry_storm(transactions, timestamp))
        patterns.extend(self.detect_issuer_degradation(transactions, timestamp))
        patterns.extend(self.detect_method_fatigue(transactions, timestamp))
        return patterns
