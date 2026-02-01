"""Model parameter updates based on learning."""

import logging
from typing import Dict, List, Optional
from payops_ai.models.outcome import Evaluation, ModelAdjustment

logger = logging.getLogger(__name__)


class ModelUpdater:
    """Updates model parameters based on learning outcomes."""
    
    def __init__(
        self,
        learning_rate: float = 0.1,
        min_confidence: float = 0.3,
        max_confidence: float = 0.95
    ):
        """Initialize model updater.
        
        Args:
            learning_rate: Rate of parameter adjustment
            min_confidence: Minimum confidence threshold
            max_confidence: Maximum confidence threshold
        """
        self.learning_rate = learning_rate
        self.min_confidence = min_confidence
        self.max_confidence = max_confidence
        self.parameter_history: Dict[str, List[float]] = {}
    
    def adjust_confidence(
        self,
        current_confidence: float,
        accuracy_score: float,
        success: bool
    ) -> float:
        """Adjust confidence based on outcome accuracy.
        
        Args:
            current_confidence: Current confidence level
            accuracy_score: Accuracy of prediction (0-1)
            success: Whether intervention succeeded
            
        Returns:
            Adjusted confidence level
        """
        if success and accuracy_score > 0.8:
            # Increase confidence for accurate successes
            adjustment = self.learning_rate * (accuracy_score - 0.5)
            new_confidence = current_confidence + adjustment
        elif not success:
            # Decrease confidence for failures
            adjustment = -self.learning_rate * (1.0 - accuracy_score)
            new_confidence = current_confidence + adjustment
        else:
            # Minor adjustment for moderate accuracy
            adjustment = self.learning_rate * (accuracy_score - 0.7) * 0.5
            new_confidence = current_confidence + adjustment
        
        # Clamp to bounds
        new_confidence = max(self.min_confidence, min(self.max_confidence, new_confidence))
        
        logger.info(
            f"Confidence adjusted: {current_confidence:.2f} -> {new_confidence:.2f} "
            f"(accuracy={accuracy_score:.2f}, success={success})"
        )
        
        return new_confidence
    
    def learn_from_denial(
        self,
        intervention_type: str,
        blast_radius: float,
        reason: str
    ) -> ModelAdjustment:
        """Learn from human denial of intervention.
        
        Args:
            intervention_type: Type of intervention denied
            blast_radius: Blast radius of denied intervention
            reason: Reason for denial
            
        Returns:
            Recommended adjustment
        """
        # Suggest lowering blast radius threshold for this intervention type
        current_threshold = 0.3  # Default
        recommended_threshold = max(0.1, blast_radius * 0.8)
        
        adjustment = ModelAdjustment(
            parameter=f"{intervention_type}_max_blast_radius",
            current_value=current_threshold,
            recommended_value=recommended_threshold,
            rationale=f"Human denied intervention with blast_radius={blast_radius:.2f}: {reason}"
        )
        
        logger.info(f"Learning from denial: {adjustment.rationale}")
        
        return adjustment
    
    def update_thresholds(
        self,
        evaluation: Evaluation
    ) -> List[ModelAdjustment]:
        """Update decision thresholds based on evaluation.
        
        Args:
            evaluation: Outcome evaluation
            
        Returns:
            List of recommended adjustments
        """
        adjustments = []
        
        # Adjust confidence threshold
        if not evaluation.success and evaluation.accuracy_score < 0.5:
            # Intervention failed badly - increase confidence requirement
            adjustments.append(ModelAdjustment(
                parameter="min_confidence_for_action",
                current_value=0.7,
                recommended_value=0.8,
                rationale=f"Low accuracy ({evaluation.accuracy_score:.2f}) suggests need for higher confidence"
            ))
        
        # Adjust blast radius threshold
        if not evaluation.success and len(evaluation.actual_outcome.unexpected_effects) > 0:
            # Unexpected effects - be more conservative
            adjustments.append(ModelAdjustment(
                parameter="max_blast_radius_for_autonomy",
                current_value=0.3,
                recommended_value=0.2,
                rationale=f"Unexpected effects detected: {', '.join(evaluation.actual_outcome.unexpected_effects)}"
            ))
        
        # Log adjustments
        for adj in adjustments:
            logger.info(f"Recommended adjustment: {adj.parameter} {adj.current_value} -> {adj.recommended_value}")
        
        # Store in history
        for adj in adjustments:
            if adj.parameter not in self.parameter_history:
                self.parameter_history[adj.parameter] = []
            self.parameter_history[adj.parameter].append(adj.recommended_value)
        
        return adjustments
    
    def get_parameter_trend(self, parameter: str) -> Optional[str]:
        """Get trend for a parameter.
        
        Args:
            parameter: Parameter name
            
        Returns:
            Trend description or None
        """
        if parameter not in self.parameter_history or len(self.parameter_history[parameter]) < 2:
            return None
        
        history = self.parameter_history[parameter]
        recent = history[-3:]  # Last 3 values
        
        if all(recent[i] < recent[i+1] for i in range(len(recent)-1)):
            return "increasing"
        elif all(recent[i] > recent[i+1] for i in range(len(recent)-1)):
            return "decreasing"
        else:
            return "stable"
