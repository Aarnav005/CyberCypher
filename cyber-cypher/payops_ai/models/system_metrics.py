"""System metrics data models."""

from typing import Dict, Optional
from pydantic import BaseModel, Field


class SystemMetrics(BaseModel):
    """System health and performance metrics.
    
    Represents the current state of payment infrastructure.
    """
    timestamp: int = Field(..., gt=0, description="Unix timestamp in milliseconds")
    gateway_health: float = Field(..., ge=0.0, le=1.0, description="Gateway health score (0-1)")
    bank_availability: Dict[str, float] = Field(
        default_factory=dict,
        description="Bank availability scores by issuer (0-1)"
    )
    throttling_indicators: Dict[str, int] = Field(
        default_factory=dict,
        description="Throttling indicators by dimension"
    )
    retry_queue_depth: int = Field(..., ge=0, description="Number of transactions in retry queue")
    sla_breach_count: int = Field(default=0, ge=0, description="Number of SLA breaches")
    active_alerts: int = Field(default=0, ge=0, description="Number of active alerts")

    class Config:
        """Pydantic configuration."""
        frozen = False
