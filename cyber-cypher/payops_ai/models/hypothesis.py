"""Hypothesis and belief state data models."""

from typing import List
from pydantic import BaseModel, Field
from payops_ai.models.pattern import Evidence


class ImpactEstimate(BaseModel):
    """Estimated impact of a hypothesis or intervention."""
    success_rate_impact: float = Field(..., description="Expected change in success rate")
    latency_impact: float = Field(..., description="Expected change in latency")
    cost_impact: float = Field(..., description="Expected change in cost")
    risk_impact: float = Field(..., description="Expected change in risk")

    class Config:
        """Pydantic configuration."""
        frozen = False


class Hypothesis(BaseModel):
    """A hypothesis about the root cause of a pattern."""
    id: str = Field(..., min_length=1, description="Unique hypothesis identifier")
    description: str = Field(..., description="Human-readable description")
    root_cause: str = Field(..., description="Proposed root cause")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence level (0-1)")
    supporting_evidence: List[Evidence] = Field(
        default_factory=list,
        description="Evidence supporting this hypothesis"
    )
    contradicting_evidence: List[Evidence] = Field(
        default_factory=list,
        description="Evidence contradicting this hypothesis"
    )
    expected_impact: ImpactEstimate = Field(..., description="Expected impact if hypothesis is true")

    class Config:
        """Pydantic configuration."""
        frozen = False


class BeliefState(BaseModel):
    """Current belief state of the agent."""
    active_hypotheses: List[Hypothesis] = Field(
        default_factory=list,
        description="Currently active hypotheses"
    )
    system_health_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall system health score"
    )
    uncertainty_level: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Level of uncertainty in current beliefs"
    )
    last_updated: int = Field(..., gt=0, description="Last update timestamp")

    class Config:
        """Pydantic configuration."""
        frozen = False
