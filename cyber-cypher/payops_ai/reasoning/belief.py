"""Belief state management."""

import logging
from typing import List
import time

from payops_ai.models.hypothesis import Hypothesis, BeliefState

logger = logging.getLogger(__name__)


class BeliefStateManager:
    """Manages the agent's belief state."""
    
    def __init__(self):
        """Initialize belief state manager."""
        self.current_state = BeliefState(
            active_hypotheses=[],
            system_health_score=1.0,
            uncertainty_level=0.0,
            last_updated=int(time.time() * 1000)
        )
    
    def update_beliefs(
        self,
        new_hypotheses: List[Hypothesis],
        timestamp: int
    ) -> BeliefState:
        """Update belief state with new hypotheses."""
        # Merge with existing hypotheses
        all_hypotheses = self.current_state.active_hypotheses + new_hypotheses
        
        # Calculate system health based on hypotheses
        if all_hypotheses:
            avg_confidence = sum(h.confidence for h in all_hypotheses) / len(all_hypotheses)
            health_score = 1.0 - (avg_confidence * 0.5)  # Simplified
        else:
            health_score = 1.0
        
        # Calculate uncertainty
        if all_hypotheses:
            confidence_variance = sum((h.confidence - 0.5) ** 2 for h in all_hypotheses) / len(all_hypotheses)
            uncertainty = min(confidence_variance * 2, 1.0)
        else:
            uncertainty = 0.0
        
        self.current_state = BeliefState(
            active_hypotheses=all_hypotheses,
            system_health_score=health_score,
            uncertainty_level=uncertainty,
            last_updated=timestamp
        )
        
        return self.current_state
    
    def get_current_beliefs(self) -> BeliefState:
        """Get current belief state."""
        return self.current_state
    
    def clear_beliefs(self) -> None:
        """Clear all beliefs."""
        self.current_state = BeliefState(
            active_hypotheses=[],
            system_health_score=1.0,
            uncertainty_level=0.0,
            last_updated=int(time.time() * 1000)
        )
