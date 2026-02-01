"""Agent state data models."""

from typing import List, Dict, Any
from pydantic import BaseModel, Field
from payops_ai.models.hypothesis import BeliefState
from payops_ai.models.execution import ExecutionResult


class ModelParameters(BaseModel):
    """Tunable model parameters."""
    anomaly_threshold: float = Field(
        default=2.0,
        gt=0.0,
        description="Statistical significance threshold (std devs)"
    )
    min_confidence_for_action: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence to act autonomously"
    )
    max_blast_radius_for_autonomy: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Max blast radius for autonomous action"
    )
    learning_rate: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="How quickly to update from outcomes"
    )
    conservativeness_level: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="How conservative to be (0=aggressive, 1=very conservative)"
    )

    class Config:
        """Pydantic configuration."""
        frozen = False


class ObservationWindow(BaseModel):
    """Window of recent observations."""
    transactions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Recent transaction signals"
    )
    time_range_ms: tuple[int, int] = Field(..., description="Time range (start, end)")
    aggregate_stats: Dict[str, Any] = Field(
        default_factory=dict,
        description="Aggregate statistics"
    )

    class Config:
        """Pydantic configuration."""
        frozen = False


class AgentState(BaseModel):
    """Complete agent state for persistence."""
    current_beliefs: BeliefState = Field(..., description="Current belief state")
    active_interventions: List[ExecutionResult] = Field(
        default_factory=list,
        description="Currently active interventions"
    )
    recent_observations: ObservationWindow = Field(..., description="Recent observation window")
    model_parameters: ModelParameters = Field(
        default_factory=ModelParameters,
        description="Model parameters"
    )
    last_updated: int = Field(..., gt=0, description="Last update timestamp")
    
    # Professional upgrade fields
    nrv_projection: float = Field(
        default=0.0,
        description="Net Recovery Value projection for current intervention"
    )
    z_score: float = Field(
        default=0.0,
        description="Statistical Z-score for anomaly detection"
    )
    risk_acknowledged: bool = Field(
        default=False,
        description="Whether pre-mortem risks have been acknowledged"
    )

    class Config:
        """Pydantic configuration."""
        frozen = False
