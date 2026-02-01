"""Intervention planning."""

import logging
from typing import List

from payops_ai.models.pattern import DetectedPattern, PatternType
from payops_ai.models.hypothesis import Hypothesis
from payops_ai.models.intervention import (
    InterventionOption, InterventionType, Tradeoffs, OutcomeEstimate
)

logger = logging.getLogger(__name__)


class InterventionPlanner:
    """Plans intervention options based on detected patterns."""
    
    def __init__(self):
        """Initialize intervention planner."""
        pass
    
    def generate_options(
        self,
        patterns: List[DetectedPattern],
        hypotheses: List[Hypothesis]
    ) -> List[InterventionOption]:
        """Generate intervention options."""
        options = []
        
        # Always include no-action option
        options.append(self._create_no_action_option())
        
        for pattern in patterns:
            if pattern.type == PatternType.ISSUER_DEGRADATION:
                options.append(self._create_suppress_issuer_option(pattern))
            elif pattern.type == PatternType.RETRY_STORM:
                options.append(self._create_reduce_retry_option(pattern))
            elif pattern.type == PatternType.METHOD_FATIGUE:
                options.append(self._create_reroute_option(pattern))
            elif pattern.type == PatternType.LATENCY_SPIKE:
                options.append(self._create_alert_option(pattern))
        
        return options
    
    def _create_no_action_option(self) -> InterventionOption:
        """Create no-action option."""
        return InterventionOption(
            type=InterventionType.NO_ACTION,
            target="none",
            parameters={},
            expected_outcome=OutcomeEstimate(
                expected_success_rate_change=0.0,
                expected_latency_change=0.0,
                expected_cost_change=0.0,
                confidence=1.0
            ),
            tradeoffs=Tradeoffs(
                success_rate_impact=0.0,
                latency_impact=0.0,
                cost_impact=0.0,
                risk_impact=0.0,
                user_friction_impact=0.0
            ),
            reversible=True,
            blast_radius=0.0
        )
    
    def _create_suppress_issuer_option(self, pattern: DetectedPattern) -> InterventionOption:
        """Create option to suppress failing issuer."""
        return InterventionOption(
            type=InterventionType.SUPPRESS_PATH,
            target=pattern.affected_dimension,
            parameters={
                "duration_ms": 300000,  # 5 minutes
                "reason": "issuer_degradation"
            },
            expected_outcome=OutcomeEstimate(
                expected_success_rate_change=0.1,
                expected_latency_change=-50.0,
                expected_cost_change=0.05,
                confidence=0.7
            ),
            tradeoffs=Tradeoffs(
                success_rate_impact=0.1,
                latency_impact=-50.0,
                cost_impact=0.05,
                risk_impact=0.1,
                user_friction_impact=0.2
            ),
            reversible=True,
            blast_radius=0.2
        )
    
    def _create_reduce_retry_option(self, pattern: DetectedPattern) -> InterventionOption:
        """Create option to reduce retry attempts."""
        return InterventionOption(
            type=InterventionType.REDUCE_RETRY_ATTEMPTS,
            target="system",
            parameters={
                "max_retries": 2,
                "duration_ms": 600000  # 10 minutes
            },
            expected_outcome=OutcomeEstimate(
                expected_success_rate_change=-0.05,
                expected_latency_change=-100.0,
                expected_cost_change=-0.1,
                confidence=0.8
            ),
            tradeoffs=Tradeoffs(
                success_rate_impact=-0.05,
                latency_impact=-100.0,
                cost_impact=-0.1,
                risk_impact=0.05,
                user_friction_impact=0.1
            ),
            reversible=True,
            blast_radius=0.5
        )
    
    def _create_reroute_option(self, pattern: DetectedPattern) -> InterventionOption:
        """Create option to reroute traffic."""
        return InterventionOption(
            type=InterventionType.REROUTE_TRAFFIC,
            target=pattern.affected_dimension,
            parameters={
                "alternative_method": "card",
                "duration_ms": 300000
            },
            expected_outcome=OutcomeEstimate(
                expected_success_rate_change=0.15,
                expected_latency_change=20.0,
                expected_cost_change=0.02,
                confidence=0.6
            ),
            tradeoffs=Tradeoffs(
                success_rate_impact=0.15,
                latency_impact=20.0,
                cost_impact=0.02,
                risk_impact=0.15,
                user_friction_impact=0.3
            ),
            reversible=True,
            blast_radius=0.3
        )
    
    def _create_alert_option(self, pattern: DetectedPattern) -> InterventionOption:
        """Create option to alert ops team."""
        return InterventionOption(
            type=InterventionType.ALERT_OPS,
            target="ops_team",
            parameters={
                "severity": "high",
                "pattern_type": pattern.type.value
            },
            expected_outcome=OutcomeEstimate(
                expected_success_rate_change=0.0,
                expected_latency_change=0.0,
                expected_cost_change=0.0,
                confidence=1.0
            ),
            tradeoffs=Tradeoffs(
                success_rate_impact=0.0,
                latency_impact=0.0,
                cost_impact=0.0,
                risk_impact=0.0,
                user_friction_impact=0.0
            ),
            reversible=True,
            blast_radius=0.0
        )
