"""Net Recovery Value (NRV) calculator for intervention optimization.

Calculates the expected net value of an intervention:
NRV = (Expected_SR_Lift * Volume * Avg_Ticket) - Delta_Cost - Latency_Penalty
"""

import logging
from typing import Dict, Any
from payops_ai.models.intervention import InterventionOption

logger = logging.getLogger(__name__)


class NRVCalculator:
    """Calculates Net Recovery Value for interventions."""
    
    def __init__(
        self,
        avg_ticket_value: float = 100.0,
        latency_penalty_per_ms: float = 0.01,
        cost_per_intervention: float = 5.0
    ):
        """Initialize NRV calculator.
        
        Args:
            avg_ticket_value: Average transaction value in currency units
            latency_penalty_per_ms: Penalty per millisecond of added latency
            cost_per_intervention: Base cost of executing intervention
        """
        self.avg_ticket_value = avg_ticket_value
        self.latency_penalty_per_ms = latency_penalty_per_ms
        self.cost_per_intervention = cost_per_intervention
    
    def calculate_nrv(
        self,
        option: InterventionOption,
        current_volume: int,
        current_success_rate: float
    ) -> Dict[str, float]:
        """Calculate Net Recovery Value for an intervention.
        
        Formula:
        NRV = (Expected_SR_Lift * Volume * Avg_Ticket) - Delta_Cost - Latency_Penalty
        
        Where:
        - Expected_SR_Lift: Expected improvement in success rate (0.0 to 1.0)
        - Volume: Number of transactions affected
        - Avg_Ticket: Average transaction value
        - Delta_Cost: Cost of executing intervention
        - Latency_Penalty: Cost of added latency
        
        Args:
            option: Intervention option to evaluate
            current_volume: Current transaction volume
            current_success_rate: Current success rate (0.0 to 1.0)
            
        Returns:
            Dictionary with NRV components and total
        """
        # Calculate expected success rate lift
        sr_lift = option.tradeoffs.success_rate_impact
        
        # Calculate affected volume (based on blast radius)
        affected_volume = int(current_volume * option.blast_radius)
        
        # Calculate revenue recovery
        revenue_recovery = sr_lift * affected_volume * self.avg_ticket_value
        
        # Calculate intervention cost
        delta_cost = self.cost_per_intervention + abs(option.tradeoffs.cost_impact)
        
        # Calculate latency penalty
        latency_penalty = abs(option.tradeoffs.latency_impact) * self.latency_penalty_per_ms
        
        # Calculate NRV
        nrv = revenue_recovery - delta_cost - latency_penalty
        
        result = {
            "nrv": nrv,
            "revenue_recovery": revenue_recovery,
            "delta_cost": delta_cost,
            "latency_penalty": latency_penalty,
            "affected_volume": affected_volume,
            "sr_lift": sr_lift
        }
        
        logger.info(
            f"NRV Calculation: {option.type.value} on {option.target} = ${nrv:.2f} "
            f"(recovery=${revenue_recovery:.2f}, cost=${delta_cost:.2f}, "
            f"latency_penalty=${latency_penalty:.2f})"
        )
        
        return result
    
    def should_act_based_on_nrv(self, nrv: float) -> bool:
        """Determine if action should be taken based on NRV.
        
        Rule: Only act if NRV > 0
        
        Args:
            nrv: Net Recovery Value
            
        Returns:
            True if should act, False otherwise
        """
        should_act = nrv > 0
        
        if not should_act:
            logger.info(f"NRV Decision: NO ACTION (NRV=${nrv:.2f} <= 0)")
        else:
            logger.info(f"NRV Decision: ACT (NRV=${nrv:.2f} > 0)")
        
        return should_act
    
    def rank_options_by_nrv(
        self,
        options: list[InterventionOption],
        current_volume: int,
        current_success_rate: float
    ) -> list[tuple[InterventionOption, Dict[str, float]]]:
        """Rank intervention options by NRV.
        
        Args:
            options: List of intervention options
            current_volume: Current transaction volume
            current_success_rate: Current success rate
            
        Returns:
            List of (option, nrv_details) tuples sorted by NRV (descending)
        """
        ranked = []
        
        for option in options:
            nrv_details = self.calculate_nrv(option, current_volume, current_success_rate)
            ranked.append((option, nrv_details))
        
        # Sort by NRV (descending)
        ranked.sort(key=lambda x: x[1]["nrv"], reverse=True)
        
        logger.info(f"Ranked {len(ranked)} options by NRV")
        for i, (opt, details) in enumerate(ranked[:3]):  # Log top 3
            logger.info(f"  {i+1}. {opt.type.value}: NRV=${details['nrv']:.2f}")
        
        return ranked
