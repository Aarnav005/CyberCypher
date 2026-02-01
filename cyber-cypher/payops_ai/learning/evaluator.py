"""Outcome evaluation for learning."""

import logging
from typing import Dict

from payops_ai.models.outcome import Outcome, Evaluation
from payops_ai.models.intervention import OutcomeEstimate
from payops_ai.models.execution import ExecutionResult

logger = logging.getLogger(__name__)


class OutcomeEvaluator:
    """Evaluates intervention outcomes."""
    
    def __init__(self):
        """Initialize outcome evaluator."""
        self.evaluations: Dict[str, Evaluation] = {}
    
    def evaluate(
        self,
        intervention_id: str,
        expected: OutcomeEstimate,
        actual: Outcome
    ) -> Evaluation:
        """Evaluate an intervention outcome.
        
        Args:
            intervention_id: Intervention ID
            expected: Expected outcome
            actual: Actual outcome
            
        Returns:
            Evaluation
        """
        # Calculate accuracy
        success_rate_error = abs(expected.expected_success_rate_change - actual.success_rate_change)
        latency_error = abs(expected.expected_latency_change - actual.latency_change)
        
        accuracy = 1.0 - min(1.0, (success_rate_error + latency_error / 1000.0) / 2.0)
        
        # Determine success
        success = (
            actual.success_rate_change >= expected.expected_success_rate_change * 0.5 and
            len(actual.unexpected_effects) == 0
        )
        
        # Generate learnings
        learnings = []
        if success:
            learnings.append(f"Intervention achieved {actual.success_rate_change:.2%} success rate improvement")
        else:
            learnings.append(f"Intervention underperformed: {actual.success_rate_change:.2%} vs expected {expected.expected_success_rate_change:.2%}")
        
        if actual.unexpected_effects:
            learnings.append(f"Unexpected effects: {', '.join(actual.unexpected_effects)}")
        
        evaluation = Evaluation(
            intervention_id=intervention_id,
            expected_outcome=expected,
            actual_outcome=actual,
            accuracy_score=accuracy,
            success=success,
            learnings=learnings,
            recommended_adjustments=[]
        )
        
        self.evaluations[intervention_id] = evaluation
        logger.info(f"Evaluated {intervention_id}: accuracy={accuracy:.2f}, success={success}")
        
        return evaluation
    
    def get_evaluation(self, intervention_id: str) -> Evaluation:
        """Get evaluation for an intervention."""
        return self.evaluations.get(intervention_id)
