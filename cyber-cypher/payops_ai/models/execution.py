"""Action execution data models."""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class RollbackCondition(BaseModel):
    """Condition that triggers intervention rollback."""
    type: str = Field(..., description="Condition type (time_based, metric_based, manual)")
    threshold: Optional[float] = Field(None, description="Threshold value if applicable")
    metric: Optional[str] = Field(None, description="Metric to monitor if applicable")
    description: str = Field(..., description="Human-readable description")

    class Config:
        """Pydantic configuration."""
        frozen = False


class ExecutionResult(BaseModel):
    """Result of executing an intervention."""
    success: bool = Field(..., description="Whether execution succeeded")
    intervention_id: str = Field(..., min_length=1, description="Unique intervention identifier")
    executed_at: int = Field(..., gt=0, description="Execution timestamp")
    expires_at: Optional[int] = Field(None, description="Expiration timestamp if time-bound")
    rollback_conditions: List[RollbackCondition] = Field(
        default_factory=list,
        description="Conditions that trigger rollback"
    )
    actual_parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Actual parameters used"
    )
    error: Optional[str] = Field(None, description="Error message if execution failed")

    class Config:
        """Pydantic configuration."""
        frozen = False


class GuardrailConfig(BaseModel):
    """Configuration for safety guardrails."""
    max_retry_adjustment: int = Field(..., gt=0, description="Maximum retry count adjustment")
    max_suppression_duration_ms: int = Field(..., gt=0, description="Maximum suppression duration")
    protected_merchants: List[str] = Field(
        default_factory=list,
        description="Merchants that require approval"
    )
    protected_methods: List[str] = Field(
        default_factory=list,
        description="Payment methods that require approval"
    )
    require_approval_threshold: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Blast radius threshold requiring approval"
    )

    class Config:
        """Pydantic configuration."""
        frozen = False
