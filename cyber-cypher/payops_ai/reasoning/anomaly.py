"""Anomaly detection for payment signals with proper Z-score calculation."""

import logging
import statistics
from typing import List, Optional

from payops_ai.models.baseline import BaselineStats, RollingBaseline
from payops_ai.models.aggregate import AggregateStats
from payops_ai.models.pattern import DetectedPattern, PatternType, Evidence
from payops_ai.reasoning.confidence_scorer import ConfidenceScorer

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Detects statistical deviations from baseline using Z-scores.
    
    Uses rolling EWMA baselines for proper anomaly detection.
    """
    
    def __init__(self, anomaly_threshold: float = 2.0):
        """Initialize anomaly detector.
        
        Args:
            anomaly_threshold: Number of standard deviations for significance
        """
        self.anomaly_threshold = anomaly_threshold
        self.confidence_scorer = ConfidenceScorer(min_sample_size=50)
    
    def detect_success_rate_anomaly_with_rolling_baseline(
        self,
        current_stats: AggregateStats,
        rolling_baseline: RollingBaseline,
        dimension: str,
        timestamp: int,
        transactions: List = None
    ) -> Optional[DetectedPattern]:
        """Detect anomaly in success rate using rolling baseline and proper Z-score.
        
        Args:
            current_stats: Current aggregate statistics
            rolling_baseline: Rolling EWMA baseline
            dimension: Dimension being analyzed
            timestamp: Current timestamp
            transactions: List of transaction dictionaries for confidence scoring
            
        Returns:
            DetectedPattern if anomaly detected, None otherwise
        """
        if current_stats.total_transactions < 10:
            # Not enough data
            return None
        
        current_rate = current_stats.success_rate
        baseline_rate = rolling_baseline.success_rate_ewma
        baseline_std = rolling_baseline.get_std("success_rate")
        
        # Calculate proper Z-score: z = (current - baseline_mean) / baseline_std
        z_score = abs(current_rate - baseline_rate) / baseline_std
        
        if z_score >= self.anomaly_threshold:
            # Calculate multi-factor confidence if transactions provided
            confidence_details = None
            if transactions:
                failed_count = int(current_stats.total_transactions * (1 - current_rate))
                confidence_details = self.confidence_scorer.calculate_confidence(
                    failed_transactions=failed_count,
                    transactions=transactions,
                    current_failure_rate=1.0 - current_rate,
                    historical_mean=1.0 - baseline_rate,
                    historical_std=baseline_std,
                    dimension="error_code"
                )
            
            # Use confidence score if available, otherwise use z_score
            if confidence_details:
                severity = confidence_details["confidence"]
                logger.info(f"Multi-factor confidence: {severity:.3f} (Z={confidence_details['z_score']:.2f})")
            else:
                severity = min(z_score / (self.anomaly_threshold * 2), 1.0)
            
            deviation = abs(current_rate - baseline_rate)
            evidence = [
                Evidence(
                    type="statistical",
                    description=f"Success rate deviation: {deviation:.2%} (current={current_rate:.2%}, baseline={baseline_rate:.2%})",
                    value=deviation,
                    timestamp=timestamp,
                    source="anomaly_detector"
                ),
                Evidence(
                    type="statistical",
                    description=f"Z-score: {z_score:.2f} (threshold={self.anomaly_threshold:.1f})",
                    value=z_score,
                    timestamp=timestamp,
                    source="anomaly_detector"
                ),
                Evidence(
                    type="statistical",
                    description=f"Baseline: μ={baseline_rate:.3f}, σ={baseline_std:.3f}, samples={rolling_baseline.sample_count}",
                    value=baseline_std,
                    timestamp=timestamp,
                    source="rolling_baseline"
                )
            ]
            
            # Add confidence details to evidence
            if confidence_details:
                evidence.append(
                    Evidence(
                        type="statistical",
                        description=f"Confidence: {confidence_details['confidence']:.3f} (S={confidence_details['sample_score']:.2f}, C={confidence_details['consistency_score']:.2f}, B={confidence_details['baseline_score']:.2f})",
                        value=confidence_details['confidence'],
                        timestamp=timestamp,
                        source="confidence_scorer"
                    )
                )
            
            pattern = DetectedPattern(
                type=PatternType.ISSUER_DEGRADATION if "issuer" in dimension else PatternType.LOCALIZED_FAILURE,
                affected_dimension=dimension,
                severity=severity,
                evidence=evidence,
                detected_at=timestamp
            )
            
            logger.warning(f"Anomaly detected in {dimension}: Z={z_score:.2f}, success rate {current_rate:.2%} vs baseline {baseline_rate:.2%}")
            return pattern
        
        return None
    
    def detect_success_rate_anomaly(
        self,
        current_stats: AggregateStats,
        baseline: BaselineStats,
        dimension: str,
        timestamp: int,
        transactions: List = None
    ) -> Optional[DetectedPattern]:
        """Detect anomaly in success rate with multi-factor confidence scoring (legacy static baseline).
        
        Args:
            current_stats: Current aggregate statistics
            baseline: Historical baseline
            dimension: Dimension being analyzed
            timestamp: Current timestamp
            transactions: List of transaction dictionaries for confidence scoring
            
        Returns:
            DetectedPattern if anomaly detected, None otherwise
        """
        if current_stats.total_transactions < 10:
            # Not enough data
            return None
        
        current_rate = current_stats.success_rate
        baseline_rate = baseline.success_rate
        
        # Calculate deviation
        deviation = abs(current_rate - baseline_rate)
        
        # Use baseline std directly (already provided in baseline)
        std_dev = baseline.success_rate_std
        
        if std_dev == 0 or std_dev < 0.001:
            std_dev = 0.01  # Avoid division by zero
        
        z_score = deviation / std_dev
        
        # Use small epsilon for floating point comparison
        if z_score >= self.anomaly_threshold - 1e-9:
            # Calculate multi-factor confidence if transactions provided
            confidence_details = None
            if transactions:
                failed_count = int(current_stats.total_transactions * (1 - current_rate))
                confidence_details = self.confidence_scorer.calculate_confidence(
                    failed_transactions=failed_count,
                    transactions=transactions,
                    current_failure_rate=1.0 - current_rate,
                    historical_mean=1.0 - baseline_rate,
                    historical_std=std_dev,
                    dimension="error_code"
                )
            
            # Use confidence score if available, otherwise use z_score
            if confidence_details:
                severity = confidence_details["confidence"]
                logger.info(f"Multi-factor confidence: {severity:.3f} (Z={confidence_details['z_score']:.2f})")
            else:
                severity = min(z_score / (self.anomaly_threshold * 2), 1.0)
            
            evidence = [
                Evidence(
                    type="statistical",
                    description=f"Success rate deviation: {deviation:.2%}",
                    value=deviation,
                    timestamp=timestamp,
                    source="anomaly_detector"
                ),
                Evidence(
                    type="statistical",
                    description=f"Z-score: {z_score:.2f}",
                    value=z_score,
                    timestamp=timestamp,
                    source="anomaly_detector"
                )
            ]
            
            # Add confidence details to evidence
            if confidence_details:
                evidence.append(
                    Evidence(
                        type="statistical",
                        description=f"Confidence: {confidence_details['confidence']:.3f} (S={confidence_details['sample_score']:.2f}, C={confidence_details['consistency_score']:.2f}, B={confidence_details['baseline_score']:.2f})",
                        value=confidence_details['confidence'],
                        timestamp=timestamp,
                        source="confidence_scorer"
                    )
                )
            
            pattern = DetectedPattern(
                type=PatternType.ISSUER_DEGRADATION if "issuer" in dimension else PatternType.LOCALIZED_FAILURE,
                affected_dimension=dimension,
                severity=severity,
                evidence=evidence,
                detected_at=timestamp
            )
            
            logger.warning(f"Anomaly detected in {dimension}: success rate {current_rate:.2%} vs baseline {baseline_rate:.2%}")
            return pattern
        
        return None
    
    def detect_latency_anomaly(
        self,
        current_stats: AggregateStats,
        baseline: BaselineStats,
        dimension: str,
        timestamp: int
    ) -> Optional[DetectedPattern]:
        """Detect anomaly in latency.
        
        Args:
            current_stats: Current aggregate statistics
            baseline: Historical baseline
            dimension: Dimension being analyzed
            timestamp: Current timestamp
            
        Returns:
            DetectedPattern if anomaly detected, None otherwise
        """
        if current_stats.total_transactions < 10:
            return None
        
        current_p95 = current_stats.p95_latency_ms
        baseline_p95 = baseline.p95_latency_ms
        
        # Check if latency increased significantly
        if current_p95 > baseline_p95 * 1.5:  # 50% increase
            severity = min((current_p95 / baseline_p95 - 1.0) / 2.0, 1.0)
            
            evidence = [
                Evidence(
                    type="statistical",
                    description=f"P95 latency spike: {current_p95:.0f}ms vs baseline {baseline_p95:.0f}ms",
                    value=current_p95 - baseline_p95,
                    timestamp=timestamp,
                    source="anomaly_detector"
                )
            ]
            
            pattern = DetectedPattern(
                type=PatternType.LATENCY_SPIKE,
                affected_dimension=dimension,
                severity=severity,
                evidence=evidence,
                detected_at=timestamp
            )
            
            logger.warning(f"Latency anomaly detected in {dimension}: {current_p95:.0f}ms vs {baseline_p95:.0f}ms")
            return pattern
        
        return None
    
    def detect_anomalies(
        self,
        current_stats: AggregateStats,
        baseline: BaselineStats,
        dimension: str,
        timestamp: int,
        transactions: List = None
    ) -> List[DetectedPattern]:
        """Detect all types of anomalies (legacy method for static baselines).
        
        Args:
            current_stats: Current aggregate statistics
            baseline: Historical baseline
            dimension: Dimension being analyzed
            timestamp: Current timestamp
            transactions: List of transaction dictionaries for confidence scoring
            
        Returns:
            List of detected patterns
        """
        patterns = []
        
        # Check success rate
        success_rate_pattern = self.detect_success_rate_anomaly(
            current_stats, baseline, dimension, timestamp, transactions
        )
        if success_rate_pattern:
            patterns.append(success_rate_pattern)
        
        # Check latency
        latency_pattern = self.detect_latency_anomaly(
            current_stats, baseline, dimension, timestamp
        )
        if latency_pattern:
            patterns.append(latency_pattern)
        
        return patterns
    
    def detect_anomalies_with_rolling_baseline(
        self,
        current_stats: AggregateStats,
        rolling_baseline: RollingBaseline,
        dimension: str,
        timestamp: int,
        transactions: List = None
    ) -> List[DetectedPattern]:
        """Detect all types of anomalies using rolling baseline.
        
        Args:
            current_stats: Current aggregate statistics
            rolling_baseline: Rolling EWMA baseline
            dimension: Dimension being analyzed
            timestamp: Current timestamp
            transactions: List of transaction dictionaries for confidence scoring
            
        Returns:
            List of detected patterns
        """
        patterns = []
        
        # Check success rate with rolling baseline
        success_rate_pattern = self.detect_success_rate_anomaly_with_rolling_baseline(
            current_stats, rolling_baseline, dimension, timestamp, transactions
        )
        if success_rate_pattern:
            patterns.append(success_rate_pattern)
        
        # TODO: Add latency anomaly detection with rolling baseline
        
        return patterns
