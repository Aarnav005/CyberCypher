"""Multi-factor confidence scoring for pattern detection.

Implements mathematical confidence calculation based on:
1. Sample Size (statistical significance)
2. Signal Consistency (error code/provider clustering)
3. Historical Baseline (Z-score deviation)
"""

import logging
import math
from typing import List, Dict, Any
from collections import Counter

logger = logging.getLogger(__name__)


class ConfidenceScorer:
    """Calculates multi-factor confidence scores for detected patterns."""
    
    def __init__(self, min_sample_size: int = 50):
        """Initialize confidence scorer.
        
        Args:
            min_sample_size: Minimum transactions needed for statistical significance
        """
        self.min_sample_size = min_sample_size
    
    def calculate_sample_size_score(self, failed_transactions: int) -> float:
        """Calculate sample size score (S).
        
        Formula: S = min(1.0, failed_transactions / min_sample_size)
        
        Args:
            failed_transactions: Number of failed transactions
            
        Returns:
            Score between 0.0 and 1.0
        """
        score = min(1.0, failed_transactions / self.min_sample_size)
        logger.debug(f"Sample Size Score: {score:.3f} (failed_txns={failed_transactions}, min={self.min_sample_size})")
        return score
    
    def calculate_signal_consistency_score(
        self,
        transactions: List[Dict[str, Any]],
        dimension: str = "error_code"
    ) -> float:
        """Calculate signal consistency score (C).
        
        Measures percentage of failures sharing the same error_code or provider.
        
        Args:
            transactions: List of transaction dictionaries
            dimension: Dimension to check consistency ('error_code' or 'issuer')
            
        Returns:
            Score between 0.0 and 1.0
        """
        if not transactions:
            return 0.0
        
        # Filter failed transactions - support both dict and object access
        failed = [t for t in transactions if (t.get('outcome') if isinstance(t, dict) else getattr(t, 'outcome', None)) in ['soft_fail', 'hard_fail']]
        
        if not failed:
            return 0.0
        
        # Count occurrences of dimension values
        values = [(t.get(dimension) if isinstance(t, dict) else getattr(t, dimension, None)) for t in failed]
        values = [v for v in values if v is not None]
        
        if not values:
            return 0.0
        
        # Calculate consistency as percentage of most common value
        counter = Counter(values)
        most_common_count = counter.most_common(1)[0][1]
        consistency = most_common_count / len(failed)
        
        logger.debug(f"Signal Consistency Score: {consistency:.3f} (dimension={dimension}, most_common={most_common_count}/{len(failed)})")
        return consistency
    
    def calculate_z_score(
        self,
        current_failure_rate: float,
        historical_mean: float,
        historical_std: float
    ) -> float:
        """Calculate Z-score for current failure rate.
        
        Formula: Z = (current_rate - mean) / std
        
        Args:
            current_failure_rate: Current failure rate (0.0 to 1.0)
            historical_mean: Historical mean failure rate
            historical_std: Historical standard deviation
            
        Returns:
            Z-score (can be negative or positive)
        """
        if historical_std == 0:
            # No variance in historical data
            return 0.0
        
        z_score = (current_failure_rate - historical_mean) / historical_std
        logger.debug(f"Z-Score: {z_score:.3f} (current={current_failure_rate:.3f}, mean={historical_mean:.3f}, std={historical_std:.3f})")
        return z_score
    
    def calculate_baseline_score(self, z_score: float) -> float:
        """Calculate baseline score (B) from Z-score.
        
        Logic:
        - If Z > 3: score = 1.0 (highly anomalous)
        - If Z < 1: score = 0.0 (within normal range)
        - Otherwise: linear interpolation
        
        Args:
            z_score: Z-score from calculate_z_score()
            
        Returns:
            Score between 0.0 and 1.0
        """
        if z_score > 3.0:
            score = 1.0
        elif z_score < 1.0:
            score = 0.0
        else:
            # Linear interpolation between 1 and 3
            score = (z_score - 1.0) / 2.0
        
        logger.debug(f"Baseline Score: {score:.3f} (z_score={z_score:.3f})")
        return score
    
    def calculate_confidence(
        self,
        failed_transactions: int,
        transactions: List[Dict[str, Any]],
        current_failure_rate: float,
        historical_mean: float,
        historical_std: float,
        dimension: str = "error_code"
    ) -> Dict[str, float]:
        """Calculate final multi-factor confidence score.
        
        Formula: Confidence = (S * 0.3) + (C * 0.4) + (B * 0.3)
        
        Where:
        - S = Sample Size Score
        - C = Signal Consistency Score
        - B = Baseline Score (from Z-score)
        
        Args:
            failed_transactions: Number of failed transactions
            transactions: List of all transactions
            current_failure_rate: Current failure rate (0.0 to 1.0)
            historical_mean: Historical mean failure rate
            historical_std: Historical standard deviation
            dimension: Dimension for consistency check
            
        Returns:
            Dictionary with confidence score and components
        """
        # Calculate individual scores
        sample_score = self.calculate_sample_size_score(failed_transactions)
        consistency_score = self.calculate_signal_consistency_score(transactions, dimension)
        z_score = self.calculate_z_score(current_failure_rate, historical_mean, historical_std)
        baseline_score = self.calculate_baseline_score(z_score)
        
        # Weighted combination
        confidence = (sample_score * 0.3) + (consistency_score * 0.4) + (baseline_score * 0.3)
        
        result = {
            "confidence": confidence,
            "sample_score": sample_score,
            "consistency_score": consistency_score,
            "baseline_score": baseline_score,
            "z_score": z_score,
        }
        
        logger.info(f"Multi-Factor Confidence: {confidence:.3f} (S={sample_score:.2f}, C={consistency_score:.2f}, B={baseline_score:.2f}, Z={z_score:.2f})")
        
        return result
