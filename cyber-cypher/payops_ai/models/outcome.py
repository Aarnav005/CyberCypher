"""Outcome evaluation data models."""

from typing import List
from pydantic import BaseModel, Field


class Outcome(BaseModel):
    """Actual outcome of an intervention."""
    intervention_id: str = Field(..., min_length=1, description="Intervention identifier")
    measured_at: int = Field(..., gt=0, description="Measurement timestamp")
    success_rate_change: float = Field(..., description="Actual success rate change")
    latency_change: float = Field(..., description="Actual latency change")
    cost_change: float = Field(..., description="Actual cost change")
    risk_change: float = Field(..., description="Actual risk change")
    unexpected_effects: List[str] = Field(
        default_factory=list,
        description="Unexpected side effects"
    )

    class Config:
        """Pydantic configuration."""
        frozen = False


class ModelAdjustment(BaseModel):
    """Recommended adjustment to model parameters."""
    parameter: str = Field(..., description="Parameter name")
    current_value: float = Field(..., description="Current value")
    recommended_value: float = Field(..., description="Recommended new value")
    rationale: str = Field(..., description="Reason for adjustment")

    class Config:
        """Pydantic configuration."""
        frozen = False


class Evaluation(BaseModel):
    """Evaluation of an intervention outcome."""
    intervention_id: str = Field(..., min_length=1, description="Intervention identifier")
    expected_outcome: "OutcomeEstimate" = Field(..., description="Expected outcome")  # type: ignore
    actual_outcome: Outcome = Field(..., description="Actual outcome")
    accuracy_score: float = Field(..., ge=0.0, le=1.0, description="Prediction accuracy")
    success: bool = Field(..., description="Whether intervention achieved its goal")
    learnings: List[str] = Field(default_factory=list, description="Key learnings")
    recommended_adjustments: List[ModelAdjustment] = Field(
        default_factory=list,
        description="Recommended model adjustments"
    )

    class Config:
        """Pydantic configuration."""
        frozen = False


# Import for forward reference
from payops_ai.models.intervention import OutcomeEstimate
Evaluation.model_rebuild()
