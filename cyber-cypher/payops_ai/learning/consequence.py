"""Consequence detection for unintended effects."""

import logging
from typing import List, Optional
from payops_ai.models.outcome import Outcome

logger = logging.getLogger(__name__)


class ConsequenceDetector:
    """Detects unintended consequences of interventions."""
    
    def __init__(
        self,
        degradation_threshold: float = 0.05,  # 5% degradation triggers rollback
        unexpected_effect_threshold: int = 1  # Any unexpected effect triggers review
    ):
        """Initialize consequence detector.
        
        Args:
            degradation_threshold: Threshold for triggering rollback
            unexpected_effect_threshold: Number of unexpected effects to trigger review
        """
        self.degradation_threshold = degradation_threshold
        self.unexpected_effect_threshold = unexpected_effect_threshold
    
    def detect_degradation(self, outcome: Outcome) -> tuple[bool, str]:
        """Detect if intervention caused degradation.
        
        Args:
            outcome: Actual outcome of intervention
            
        Returns:
            Tuple of (should_rollback, reason)
        """
        reasons = []
        
        # Check success rate degradation
        if outcome.success_rate_change < -self.degradation_threshold:
            reasons.append(
                f"Success rate degraded by {abs(outcome.success_rate_change):.1%} "
                f"(threshold: {self.degradation_threshold:.1%})"
            )
        
        # Check latency degradation (increase is bad)
        if outcome.latency_change > 100.0:  # 100ms increase
            reasons.append(
                f"Latency increased by {outcome.latency_change:.0f}ms"
            )
        
        # Check risk increase
        if outcome.risk_change > 0.1:  # 10% risk increase
            reasons.append(
                f"Risk increased by {outcome.risk_change:.1%}"
            )
        
        # Check unexpected effects
        if len(outcome.unexpected_effects) >= self.unexpected_effect_threshold:
            reasons.append(
                f"Unexpected effects detected: {', '.join(outcome.unexpected_effects)}"
            )
        
        should_rollback = len(reasons) > 0
        reason = "; ".join(reasons) if reasons else ""
        
        if should_rollback:
            logger.warning(f"Degradation detected for {outcome.intervention_id}: {reason}")
        
        return should_rollback, reason
    
    def analyze_consequences(
        self,
        outcome: Outcome,
        expected_success_rate_change: float
    ) -> dict:
        """Analyze consequences of intervention.
        
        Args:
            outcome: Actual outcome
            expected_success_rate_change: Expected change
            
        Returns:
            Analysis dictionary
        """
        analysis = {
            "intervention_id": outcome.intervention_id,
            "success_rate_delta": outcome.success_rate_change - expected_success_rate_change,
            "latency_impact": outcome.latency_change,
            "risk_impact": outcome.risk_change,
            "unexpected_effects": outcome.unexpected_effects,
            "severity": "none"
        }
        
        # Determine severity
        if outcome.success_rate_change < -self.degradation_threshold:
            analysis["severity"] = "critical"
        elif len(outcome.unexpected_effects) > 0:
            analysis["severity"] = "moderate"
        elif abs(outcome.success_rate_change - expected_success_rate_change) > 0.05:
            analysis["severity"] = "minor"
        
        return analysis
