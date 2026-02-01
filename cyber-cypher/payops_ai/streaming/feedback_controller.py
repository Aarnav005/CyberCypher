"""Feedback controller for applying agent interventions to payment generation."""

import logging
import time
from dataclasses import dataclass
from typing import List, Optional

from payops_ai.models.intervention import InterventionOption, InterventionType
from payops_ai.streaming.continuous_generator import ContinuousPaymentGenerator

logger = logging.getLogger(__name__)


@dataclass
class ActiveIntervention:
    """Tracks an active intervention and its effects."""
    intervention: InterventionOption
    start_time: float
    end_time: float
    
    def is_active(self, current_time: float) -> bool:
        """Check if intervention is still active.
        
        Args:
            current_time: Current timestamp
            
        Returns:
            True if active, False if expired
        """
        return current_time < self.end_time
    
    def time_remaining(self, current_time: float) -> float:
        """Get remaining time for intervention.
        
        Args:
            current_time: Current timestamp
            
        Returns:
            Remaining time in seconds
        """
        return max(0.0, self.end_time - current_time)


class FeedbackController:
    """Applies agent interventions to payment generation parameters.
    
    Creates closed-loop feedback where agent decisions affect future transaction generation.
    """
    
    def __init__(self, generator: ContinuousPaymentGenerator):
        """Initialize feedback controller.
        
        Args:
            generator: Continuous payment generator to control
        """
        self.generator = generator
        self.active_interventions: List[ActiveIntervention] = []
        
        logger.info("Initialized FeedbackController")
    
    def apply_intervention(self, intervention: InterventionOption) -> None:
        """Apply an intervention and track its effects.
        
        Args:
            intervention: Intervention to apply
        """
        current_time = time.time()
        duration_ms = intervention.parameters.get('duration_ms', 300000)  # Default 5 minutes
        duration_s = duration_ms / 1000.0
        
        active = ActiveIntervention(
            intervention=intervention,
            start_time=current_time,
            end_time=current_time + duration_s
        )
        
        self.active_interventions.append(active)
        
        # Apply effects immediately
        self._apply_effects()
        
        logger.info(f"Applied intervention: {intervention.type.value} on {intervention.target} "
                   f"for {duration_s:.0f}s")
    
    def _apply_effects(self) -> None:
        """Apply all active intervention effects to generator."""
        # Reset multipliers
        self.generator.clear_multipliers()
        
        # Apply each active intervention
        for active in self.active_interventions:
            intervention = active.intervention
            
            if intervention.type == InterventionType.SUPPRESS_PATH:
                # Extract issuer from target (format: "issuer:HDFC")
                if ":" in intervention.target:
                    issuer = intervention.target.split(":")[1]
                    # Suppress path: reduce volume by 90% and success by 90%
                    self.generator.set_volume_multiplier(issuer, 0.1)
                    self.generator.set_success_multiplier(issuer, 0.1)
                    logger.debug(f"Suppressing path for {issuer}")
            
            elif intervention.type == InterventionType.REDUCE_RETRY_ATTEMPTS:
                # Reduce retry probability by 50%
                self.generator.set_retry_multiplier(0.5)
                logger.debug("Reducing retry attempts")
            
            elif intervention.type == InterventionType.REROUTE_TRAFFIC:
                # Extract issuer from target
                if ":" in intervention.target:
                    issuer = intervention.target.split(":")[1]
                    # Reroute traffic: reduce volume by 70%
                    self.generator.set_volume_multiplier(issuer, 0.3)
                    logger.debug(f"Rerouting traffic from {issuer}")
            
            elif intervention.type == InterventionType.ADJUST_RETRY:
                # Increase retry probability to improve recovery chance
                self.generator.set_retry_multiplier(1.5)
                logger.debug("Adjusting retry parameters: increasing retry probability")
    
    def update(self, current_time: float) -> None:
        """Update active interventions and remove expired ones.
        
        Args:
            current_time: Current timestamp
        """
        # Remove expired interventions
        before_count = len(self.active_interventions)
        self.active_interventions = [
            active for active in self.active_interventions
            if active.is_active(current_time)
        ]
        after_count = len(self.active_interventions)
        
        if before_count != after_count:
            expired_count = before_count - after_count
            logger.info(f"Expired {expired_count} intervention(s), {after_count} still active")
            
            # Reapply effects after expiration
            self._apply_effects()
    
    def get_active_interventions(self) -> List[ActiveIntervention]:
        """Get list of currently active interventions.
        
        Returns:
            List of active interventions
        """
        return self.active_interventions.copy()
    
    def get_active_count(self) -> int:
        """Get count of active interventions.
        
        Returns:
            Number of active interventions
        """
        return len(self.active_interventions)
    
    def clear_all(self) -> None:
        """Clear all active interventions."""
        self.active_interventions.clear()
        self.generator.clear_multipliers()
        logger.info("Cleared all interventions")
    
    def get_status_summary(self, current_time: float) -> str:
        """Get human-readable status summary.
        
        Args:
            current_time: Current timestamp
            
        Returns:
            Status summary string
        """
        if not self.active_interventions:
            return "No active interventions"
        
        lines = [f"{len(self.active_interventions)} active intervention(s):"]
        for i, active in enumerate(self.active_interventions, 1):
            remaining = active.time_remaining(current_time)
            lines.append(f"  {i}. {active.intervention.type.value} on {active.intervention.target} "
                        f"({remaining:.0f}s remaining)")
        
        return "\n".join(lines)
