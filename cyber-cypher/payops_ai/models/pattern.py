"""Pattern detection data models."""

from enum import Enum
from typing import List
from pydantic import BaseModel, Field


class PatternType(str, Enum):
    """Types of patterns that can be detected."""
    ISSUER_DEGRADATION = "issuer_degradation"
    RETRY_STORM = "retry_storm"
    METHOD_FATIGUE = "method_fatigue"
    LATENCY_SPIKE = "latency_spike"
    SYSTEMIC_FAILURE = "systemic_failure"
    LOCALIZED_FAILURE = "localized_failure"


class Evidence(BaseModel):
    """Evidence supporting a pattern or hypothesis."""
    type: str = Field(..., description="Evidence type (statistical, historical, system_metric)")
    description: str = Field(..., description="Human-readable description")
    value: float = Field(..., description="Numeric value")
    timestamp: int = Field(..., gt=0, description="When evidence was observed")
    source: str = Field(..., description="Source of evidence")

    class Config:
        """Pydantic configuration."""
        frozen = False


class DetectedPattern(BaseModel):
    """A detected pattern in payment behavior."""
    type: PatternType = Field(..., description="Type of pattern detected")
    affected_dimension: str = Field(..., description="Affected dimension (e.g., 'issuer:HDFC')")
    severity: float = Field(..., ge=0.0, le=1.0, description="Severity score (0-1)")
    evidence: List[Evidence] = Field(default_factory=list, description="Supporting evidence")
    detected_at: int = Field(..., gt=0, description="Detection timestamp")

    class Config:
        """Pydantic configuration."""
        frozen = False
