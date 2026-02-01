"""Safety and ethical constraints for agent decisions."""

import logging
from typing import List
from enum import Enum

from payops_ai.models.intervention import InterventionOption, InterventionType

logger = logging.getLogger(__name__)


class Priority(str, Enum):
    """Decision priority levels."""
    FRAUD_COMPLIANCE = "fraud_compliance"
    SAFETY = "safety"
    REVENUE = "revenue"
    COST = "cost"
    LATENCY = "latency"


class SafetyConstraints:
    """Enforces safety and ethical constraints on agent decisions."""
    
    def __init__(
        self,
        fraud_compliance_override: bool = True,
        prefer_minimal_intervention: bool = True,
        prefer_reversible: bool = True
    ):
        """Initialize safety constraints.
        
        Args:
            fraud_compliance_override: Fraud/compliance always takes priority
            prefer_minimal_intervention: Prefer smaller interventions
            prefer_reversible: Prefer reversible interventions
        """
        self.fraud_compliance_override = fraud_compliance_override
        self.prefer_minimal_intervention = prefer_minimal_intervention
        self.prefer_reversible = prefer_reversible
    
    def check_fraud_compliance_priority(
        self,
        option: InterventionOption,
        fraud_risk: float = 0.0,
        compliance_risk: float = 0.0
    ) -> tuple[bool, str]:
        """Check if fraud/compliance concerns override profit optimization.
        
        Args:
            option: Intervention option
            fraud_risk: Current fraud risk (0-1)
            compliance_risk: Current compliance risk (0-1)
            
        Returns:
            Tuple of (should_block, reason)
        """
        if not self.fraud_compliance_override:
            return False, ""
        
        # Block interventions that increase fraud/compliance risk
        if fraud_risk > 0.3 and option.tradeoffs.risk_impact > 0:
            return True, f"Fraud risk {fraud_risk:.2f} too high, cannot increase risk further"
        
        if compliance_risk > 0.3 and option.tradeoffs.risk_impact > 0:
            return True, f"Compliance risk {compliance_risk:.2f} too high, cannot increase risk further"
        
        # Block interventions that prioritize revenue over safety
        if fraud_risk > 0.1 and option.tradeoffs.success_rate_impact > 0.1:
            logger.warning(f"Blocking revenue optimization due to fraud risk {fraud_risk:.2f}")
            return True, "Fraud/compliance takes priority over revenue optimization"
        
        return False, ""
    
    def rank_by_minimal_intervention(
        self,
        options: List[InterventionOption]
    ) -> List[InterventionOption]:
        """Rank options preferring minimal interventions.
        
        Args:
            options: List of intervention options
            
        Returns:
            Sorted list (minimal first)
        """
        if not self.prefer_minimal_intervention:
            return options
        
        # Score by intervention magnitude
        def intervention_magnitude(opt: InterventionOption) -> float:
            """Calculate intervention magnitude."""
            if opt.type == InterventionType.NO_ACTION:
                return 0.0
            
            # Combine blast radius and impact
            magnitude = (
                opt.blast_radius * 0.5 +
                abs(opt.tradeoffs.success_rate_impact) * 0.2 +
                abs(opt.tradeoffs.latency_impact) / 1000.0 * 0.1 +
                opt.tradeoffs.user_friction_impact * 0.2
            )
            
            return magnitude
        
        # Sort by magnitude (ascending)
        sorted_options = sorted(options, key=intervention_magnitude)
        
        logger.info(f"Ranked {len(options)} options by minimal intervention preference")
        return sorted_options
    
    def filter_by_reversibility(
        self,
        options: List[InterventionOption]
    ) -> List[InterventionOption]:
        """Filter options to prefer reversible interventions.
        
        Args:
            options: List of intervention options
            
        Returns:
            Filtered list (reversible preferred)
        """
        if not self.prefer_reversible:
            return options
        
        # Separate reversible and non-reversible
        reversible = [opt for opt in options if opt.reversible]
        non_reversible = [opt for opt in options if not opt.reversible]
        
        # Return reversible first, then non-reversible
        filtered = reversible + non_reversible
        
        if len(non_reversible) > 0:
            logger.warning(f"Found {len(non_reversible)} non-reversible options")
        
        return filtered
    
    def apply_constraints(
        self,
        options: List[InterventionOption],
        fraud_risk: float = 0.0,
        compliance_risk: float = 0.0
    ) -> tuple[List[InterventionOption], List[str]]:
        """Apply all safety constraints to options.
        
        Args:
            options: List of intervention options
            fraud_risk: Current fraud risk (0-1)
            compliance_risk: Current compliance risk (0-1)
            
        Returns:
            Tuple of (filtered_options, blocked_reasons)
        """
        filtered_options = []
        blocked_reasons = []
        
        # Check fraud/compliance priority for each option
        for option in options:
            should_block, reason = self.check_fraud_compliance_priority(
                option, fraud_risk, compliance_risk
            )
            
            if should_block:
                blocked_reasons.append(f"{option.type.value}: {reason}")
                logger.warning(f"Blocked {option.type.value}: {reason}")
            else:
                filtered_options.append(option)
        
        # Apply minimal intervention preference
        if self.prefer_minimal_intervention:
            filtered_options = self.rank_by_minimal_intervention(filtered_options)
        
        # Apply reversibility preference
        if self.prefer_reversible:
            filtered_options = self.filter_by_reversibility(filtered_options)
        
        logger.info(f"Safety constraints: {len(options)} options -> {len(filtered_options)} allowed")
        
        return filtered_options, blocked_reasons
