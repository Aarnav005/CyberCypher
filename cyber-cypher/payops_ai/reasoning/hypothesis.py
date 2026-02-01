"""Hypothesis generation for root cause analysis."""

import logging
from typing import List
import uuid

from payops_ai.models.pattern import DetectedPattern, PatternType
from payops_ai.models.hypothesis import Hypothesis, ImpactEstimate

logger = logging.getLogger(__name__)


class HypothesisGenerator:
    """Generates hypotheses about root causes."""
    
    def __init__(self):
        """Initialize hypothesis generator."""
        pass
    
    def generate_hypotheses(
        self,
        patterns: List[DetectedPattern]
    ) -> List[Hypothesis]:
        """Generate hypotheses from detected patterns."""
        hypotheses = []
        
        for pattern in patterns:
            if pattern.type == PatternType.ISSUER_DEGRADATION:
                hypotheses.extend(self._generate_issuer_hypotheses(pattern))
            elif pattern.type == PatternType.RETRY_STORM:
                hypotheses.extend(self._generate_retry_hypotheses(pattern))
            elif pattern.type == PatternType.METHOD_FATIGUE:
                hypotheses.extend(self._generate_method_hypotheses(pattern))
            elif pattern.type == PatternType.LATENCY_SPIKE:
                hypotheses.extend(self._generate_latency_hypotheses(pattern))
        
        return hypotheses
    
    def _generate_issuer_hypotheses(self, pattern: DetectedPattern) -> List[Hypothesis]:
        """Generate hypotheses for issuer degradation."""
        hypotheses = []
        
        # Hypothesis 1: Issuer downtime
        h1 = Hypothesis(
            id=str(uuid.uuid4()),
            description="Issuer experiencing downtime or degraded service",
            root_cause="issuer_downtime",
            confidence=0.7,
            supporting_evidence=pattern.evidence,
            contradicting_evidence=[],
            expected_impact=ImpactEstimate(
                success_rate_impact=-0.2,
                latency_impact=100.0,
                cost_impact=0.0,
                risk_impact=0.1
            )
        )
        hypotheses.append(h1)
        
        # Hypothesis 2: Network issues
        h2 = Hypothesis(
            id=str(uuid.uuid4()),
            description="Network connectivity issues with issuer",
            root_cause="network_issues",
            confidence=0.5,
            supporting_evidence=pattern.evidence,
            contradicting_evidence=[],
            expected_impact=ImpactEstimate(
                success_rate_impact=-0.15,
                latency_impact=200.0,
                cost_impact=0.0,
                risk_impact=0.05
            )
        )
        hypotheses.append(h2)
        
        return hypotheses
    
    def _generate_retry_hypotheses(self, pattern: DetectedPattern) -> List[Hypothesis]:
        """Generate hypotheses for retry storms."""
        h = Hypothesis(
            id=str(uuid.uuid4()),
            description="Excessive retry attempts amplifying load",
            root_cause="retry_storm",
            confidence=0.8,
            supporting_evidence=pattern.evidence,
            contradicting_evidence=[],
            expected_impact=ImpactEstimate(
                success_rate_impact=-0.1,
                latency_impact=150.0,
                cost_impact=0.2,
                risk_impact=0.15
            )
        )
        return [h]
    
    def _generate_method_hypotheses(self, pattern: DetectedPattern) -> List[Hypothesis]:
        """Generate hypotheses for method fatigue."""
        h = Hypothesis(
            id=str(uuid.uuid4()),
            description="Payment method experiencing high failure rate",
            root_cause="method_fatigue",
            confidence=0.6,
            supporting_evidence=pattern.evidence,
            contradicting_evidence=[],
            expected_impact=ImpactEstimate(
                success_rate_impact=-0.25,
                latency_impact=50.0,
                cost_impact=0.0,
                risk_impact=0.1
            )
        )
        return [h]
    
    def _generate_latency_hypotheses(self, pattern: DetectedPattern) -> List[Hypothesis]:
        """Generate hypotheses for latency spikes."""
        hypotheses = []
        
        h1 = Hypothesis(
            id=str(uuid.uuid4()),
            description="System overload causing latency spike",
            root_cause="system_overload",
            confidence=0.6,
            supporting_evidence=pattern.evidence,
            contradicting_evidence=[],
            expected_impact=ImpactEstimate(
                success_rate_impact=-0.05,
                latency_impact=300.0,
                cost_impact=0.1,
                risk_impact=0.2
            )
        )
        hypotheses.append(h1)
        
        return hypotheses
