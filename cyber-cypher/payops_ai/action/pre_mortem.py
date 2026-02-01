"""Adversarial pre-mortem safety check for interventions.

Identifies worst-case scenarios before executing interventions.
"""

import logging
from typing import Dict, Any, List
from payops_ai.models.intervention import InterventionOption, InterventionType

logger = logging.getLogger(__name__)


class PreMortemAnalyzer:
    """Performs adversarial pre-mortem analysis on interventions."""
    
    def __init__(self):
        """Initialize pre-mortem analyzer."""
        self.risk_scenarios = {
            InterventionType.ADJUST_RETRY: [
                "Retry storm amplifies load on already degraded issuer",
                "Increased retries cause cascading failures in payment gateway",
                "User experiences multiple duplicate charges"
            ],
            InterventionType.SUPPRESS_PATH: [
                "Legitimate transactions blocked, revenue loss",
                "Users unable to complete purchases, cart abandonment",
                "Suppression persists beyond recovery, manual intervention needed"
            ],
            InterventionType.REROUTE_TRAFFIC: [
                "Alternative path has lower success rate than original",
                "Rerouting causes unexpected latency spikes",
                "Alternative provider rate limits kick in"
            ],
            InterventionType.REDUCE_RETRY_ATTEMPTS: [
                "Transient failures become permanent, success rate drops",
                "Users give up before successful retry",
                "Revenue loss from recoverable transactions"
            ],
            InterventionType.ALERT_OPS: [
                "Alert fatigue, genuine issues ignored",
                "Ops team overwhelmed during incident",
                "Delayed response due to unclear alert"
            ]
        }
    
    def analyze(
        self,
        option: InterventionOption,
        current_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform pre-mortem analysis on intervention.
        
        Args:
            option: Intervention option to analyze
            current_state: Current system state
            
        Returns:
            Pre-mortem analysis with worst-case scenarios and risk assessment
        """
        # Identify worst-case scenarios
        worst_case_scenarios = self.risk_scenarios.get(
            option.type,
            ["Unknown intervention type, unpredictable risks"]
        )
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(option, current_state)
        
        # Identify mitigation strategies
        mitigations = self._identify_mitigations(option)
        
        # Determine if risk is acceptable
        risk_acceptable = risk_score < 0.7  # Threshold for acceptable risk
        
        analysis = {
            "worst_case_scenarios": worst_case_scenarios,
            "risk_score": risk_score,
            "risk_acceptable": risk_acceptable,
            "mitigations": mitigations,
            "requires_acknowledgment": not risk_acceptable,
            "blast_radius": option.blast_radius,
            "reversible": option.reversible
        }
        
        logger.info(
            f"Pre-Mortem Analysis: {option.type.value} - "
            f"Risk Score: {risk_score:.2f}, "
            f"Acceptable: {risk_acceptable}, "
            f"Scenarios: {len(worst_case_scenarios)}"
        )
        
        for scenario in worst_case_scenarios:
            logger.warning(f"  Worst-case: {scenario}")
        
        return analysis
    
    def _calculate_risk_score(
        self,
        option: InterventionOption,
        current_state: Dict[str, Any]
    ) -> float:
        """Calculate overall risk score for intervention.
        
        Args:
            option: Intervention option
            current_state: Current system state
            
        Returns:
            Risk score between 0.0 (low risk) and 1.0 (high risk)
        """
        # Base risk from blast radius
        blast_risk = option.blast_radius
        
        # Risk from irreversibility
        reversibility_risk = 0.0 if option.reversible else 0.3
        
        # Risk from trade-offs
        tradeoff_risk = (
            abs(option.tradeoffs.risk_impact) * 0.4 +
            abs(option.tradeoffs.user_friction_impact) * 0.3
        )
        
        # Risk from uncertainty
        uncertainty_risk = 1.0 - option.expected_outcome.confidence
        
        # Combined risk score
        risk_score = min(1.0, (
            blast_risk * 0.3 +
            reversibility_risk * 0.2 +
            tradeoff_risk * 0.3 +
            uncertainty_risk * 0.2
        ))
        
        return risk_score
    
    def _identify_mitigations(self, option: InterventionOption) -> List[str]:
        """Identify mitigation strategies for intervention.
        
        Args:
            option: Intervention option
            
        Returns:
            List of mitigation strategies
        """
        mitigations = []
        
        # Blast radius mitigation
        if option.blast_radius > 0.5:
            mitigations.append("Reduce blast radius to < 50% of traffic")
        
        # Reversibility mitigation
        if not option.reversible:
            mitigations.append("Implement manual rollback procedure")
        
        # Duration mitigation
        if "duration_ms" in option.parameters:
            duration_min = option.parameters["duration_ms"] / 60000
            if duration_min > 10:
                mitigations.append(f"Reduce duration from {duration_min:.0f} to < 10 minutes")
        
        # Monitoring mitigation
        mitigations.append("Enable real-time monitoring of success rate and latency")
        mitigations.append("Set automatic rollback if success rate drops > 5%")
        
        return mitigations
    
    def create_risk_acknowledgment(
        self,
        option: InterventionOption,
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create risk acknowledgment document.
        
        Args:
            option: Intervention option
            analysis: Pre-mortem analysis
            
        Returns:
            Risk acknowledgment document
        """
        acknowledgment = {
            "intervention_type": option.type.value,
            "target": option.target,
            "risk_score": analysis["risk_score"],
            "worst_case_scenarios": analysis["worst_case_scenarios"],
            "mitigations": analysis["mitigations"],
            "blast_radius": option.blast_radius,
            "reversible": option.reversible,
            "risk_acknowledged": False,  # Must be set to True by human operator
            "acknowledged_by": None,
            "acknowledged_at": None
        }
        
        return acknowledgment
