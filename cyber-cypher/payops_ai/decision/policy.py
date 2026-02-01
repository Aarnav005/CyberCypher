"""Decision policy for selecting interventions."""

import logging
from typing import List, Optional

from payops_ai.models.hypothesis import BeliefState
from payops_ai.models.intervention import (
    InterventionOption, InterventionDecision, InterventionType,
    OutcomeEstimate, Tradeoffs
)
from payops_ai.decision.nrv_calculator import NRVCalculator

logger = logging.getLogger(__name__)


class DecisionPolicy:
    """Decides whether and how to intervene using NRV optimization."""
    
    def __init__(
        self,
        min_confidence: float = 0.7,
        max_blast_radius: float = 0.3,
        avg_ticket_value: float = 100.0,
        min_action_frequency_cycles: int = 6
    ):
        """Initialize decision policy.
        
        Args:
            min_confidence: Minimum confidence to act autonomously
            max_blast_radius: Maximum blast radius for autonomous action
            avg_ticket_value: Average transaction value for NRV calculation
            min_action_frequency_cycles: Minimum cycles between actions (guarantee action every N cycles)
        """
        self.min_confidence = min_confidence
        self.max_blast_radius = max_blast_radius
        self.nrv_calculator = NRVCalculator(avg_ticket_value=avg_ticket_value)
        self.min_action_frequency_cycles = min_action_frequency_cycles
        self.cycles_since_last_action = 0
    
    def make_decision(
        self,
        options: List[InterventionOption],
        beliefs: BeliefState,
        current_volume: int = 1000,
        current_success_rate: float = 0.95
    ) -> InterventionDecision:
        """Make intervention decision using NRV optimization with minimum action frequency.
        
        Args:
            options: Available intervention options
            beliefs: Current belief state
            current_volume: Current transaction volume
            current_success_rate: Current success rate
            
        Returns:
            InterventionDecision with NRV-optimized selection
        """
        if not options:
            self.cycles_since_last_action += 1
            return self._create_no_action_decision("No options available")
        
        # Filter out no-action
        action_options = [opt for opt in options if opt.type != InterventionType.NO_ACTION]
        
        # Check minimum action frequency rule BEFORE checking if action_options is empty
        # This ensures the counter triggers even when no patterns are detected
        if self.cycles_since_last_action >= (self.min_action_frequency_cycles - 1):
            # 6th cycle: guarantee action
            if not action_options:
                # No real options available, generate a baseline alert action
                logger.warning(f"MINIMUM FREQUENCY RULE TRIGGERED (cycle {self.cycles_since_last_action + 1}) but no action options available")
                logger.warning("Generating baseline ALERT_OPS action to satisfy minimum frequency requirement")
                
                # Create a baseline alert option
                baseline_option = InterventionOption(
                    type=InterventionType.ALERT_OPS,
                    target="ops_team",
                    parameters={
                        "severity": "low",
                        "reason": "minimum_action_frequency",
                        "message": "No anomalies detected but minimum action frequency rule triggered"
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
                
                # Reset counter
                self.cycles_since_last_action = 0
                
                return InterventionDecision(
                    should_act=True,
                    selected_option=baseline_option,
                    rationale=f"[MIN FREQUENCY RULE] Generated baseline ALERT_OPS action after {self.min_action_frequency_cycles} cycles with no anomalies detected",
                    alternatives_considered=[],
                    requires_human_approval=False
                )
            else:
                # Have real options, select best one
                ranked_options = self.nrv_calculator.rank_options_by_nrv(
                    action_options, current_volume, current_success_rate
                )
                best_option, best_nrv_details = ranked_options[0]
                best_nrv = best_nrv_details["nrv"]
                
                logger.info(f"MINIMUM FREQUENCY RULE TRIGGERED (cycle {self.cycles_since_last_action + 1} since last action)")
                logger.info(f"Forcing action with best option: {best_option.type.value} (NRV=${best_nrv:.2f})")
                
                # Reset counter
                self.cycles_since_last_action = 0
                
                # Check if requires escalation
                requires_approval = (
                    best_option.blast_radius > self.max_blast_radius or
                    beliefs.uncertainty_level > 0.5
                )
                
                return InterventionDecision(
                    should_act=True,
                    selected_option=best_option,
                    rationale=f"[MIN FREQUENCY RULE] Selected {best_option.type.value} with NRV=${best_nrv:.2f} (recovery=${best_nrv_details['revenue_recovery']:.2f}, cost=${best_nrv_details['delta_cost']:.2f}) - Guaranteed action after {self.min_action_frequency_cycles} cycles",
                    alternatives_considered=[opt for opt, _ in ranked_options[1:]],
                    requires_human_approval=requires_approval
                )
        
        if not action_options:
            self.cycles_since_last_action += 1
            return self._create_no_action_decision(f"Only no-action option available (cycle {self.cycles_since_last_action} since last action)")
        
        # Rank options by NRV
        ranked_options = self.nrv_calculator.rank_options_by_nrv(
            action_options, current_volume, current_success_rate
        )
        
        # Get best option
        best_option, best_nrv_details = ranked_options[0]
        best_nrv = best_nrv_details["nrv"]
        
        # Normal NRV Rule: Only act if NRV > 0
        if not self.nrv_calculator.should_act_based_on_nrv(best_nrv):
            self.cycles_since_last_action += 1
            return self._create_no_action_decision(
                f"Best option NRV=${best_nrv:.2f} <= 0, no economic value (cycle {self.cycles_since_last_action} since last action)"
            )
        
        # Act with positive NRV
        self.cycles_since_last_action = 0
        
        # Check if requires escalation
        requires_approval = (
            best_option.blast_radius > self.max_blast_radius or
            beliefs.uncertainty_level > 0.5
        )
        
        return InterventionDecision(
            should_act=True,
            selected_option=best_option,
            rationale=f"Selected {best_option.type.value} with NRV=${best_nrv:.2f} (recovery=${best_nrv_details['revenue_recovery']:.2f}, cost=${best_nrv_details['delta_cost']:.2f})",
            alternatives_considered=[opt for opt, _ in ranked_options[1:]],
            requires_human_approval=requires_approval
        )
    
    def _score_option(self, option: InterventionOption, beliefs: BeliefState) -> float:
        """Score an intervention option.
        
        Args:
            option: Intervention option
            beliefs: Current belief state
            
        Returns:
            Score between 0 and 1
        """
        # Calculate benefit (success rate improvement)
        benefit = option.tradeoffs.success_rate_impact
        
        # Calculate cost (latency, user friction, risk)
        cost = (
            abs(option.tradeoffs.latency_impact) / 1000.0 +
            option.tradeoffs.user_friction_impact +
            option.tradeoffs.risk_impact
        ) / 3.0
        
        # Adjust for confidence
        confidence_factor = option.expected_outcome.confidence
        
        # Adjust for blast radius (prefer smaller)
        blast_penalty = option.blast_radius * 0.5
        
        # Calculate final score
        score = (benefit - cost) * confidence_factor - blast_penalty
        
        # Normalize to 0-1
        score = max(0.0, min(1.0, (score + 1.0) / 2.0))
        
        return score
    
    def _create_no_action_decision(self, rationale: str) -> InterventionDecision:
        """Create a no-action decision."""
        return InterventionDecision(
            should_act=False,
            selected_option=None,
            rationale=rationale,
            alternatives_considered=[],
            requires_human_approval=False
        )
