"""Intervention decision data models."""

from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class InterventionType(str, Enum):
    """Types of interventions the agent can perform."""
    ADJUST_RETRY = "adjust_retry"
    SUPPRESS_PATH = "suppress_path"
    REROUTE_TRAFFIC = "reroute_traffic"
    REDUCE_RETRY_ATTEMPTS = "reduce_retry_attempts"
    ALERT_OPS = "alert_ops"
    NO_ACTION = "no_action"


class Tradeoffs(BaseModel):
    """Multi-dimensional trade-offs for an intervention."""
    success_rate_impact: float = Field(..., description="Expected change in success rate")
    latency_impact: float = Field(..., description="Expected change in latency (ms)")
    cost_impact: float = Field(..., description="Expected change in processing cost")
    risk_impact: float = Field(..., description="Expected change in risk exposure")
    user_friction_impact: float = Field(..., description="Expected change in user experience")

    class Config:
        """Pydantic configuration."""
        frozen = False


class OutcomeEstimate(BaseModel):
    """Estimated outcome of an intervention."""
    expected_success_rate_change: float = Field(..., description="Expected success rate change")
    expected_latency_change: float = Field(..., description="Expected latency change")
    expected_cost_change: float = Field(..., description="Expected cost change")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in estimate")

    class Config:
        """Pydantic configuration."""
        frozen = False


class InterventionOption(BaseModel):
    """A possible intervention option."""
    type: InterventionType = Field(..., description="Type of intervention")
    target: str = Field(..., description="What will be affected")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Intervention parameters")
    expected_outcome: OutcomeEstimate = Field(..., description="Expected outcome")
    tradeoffs: Tradeoffs = Field(..., description="Multi-dimensional trade-offs")
    reversible: bool = Field(..., description="Whether intervention is reversible")
    blast_radius: float = Field(..., ge=0.0, le=1.0, description="Blast radius (0-1)")

    class Config:
        """Pydantic configuration."""
        frozen = False


class InterventionDecision(BaseModel):
    """Decision about whether and how to intervene."""
    should_act: bool = Field(..., description="Whether to take action")
    selected_option: Optional[InterventionOption] = Field(
        None,
        description="Selected intervention option"
    )
    rationale: str = Field(..., description="Reasoning for the decision")
    alternatives_considered: List[InterventionOption] = Field(
        default_factory=list,
        description="Alternative options that were considered"
    )
    requires_human_approval: bool = Field(..., description="Whether human approval is required")

    class Config:
        """Pydantic configuration."""
        frozen = False
