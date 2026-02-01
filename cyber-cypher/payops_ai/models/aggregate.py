"""Aggregate statistics data models."""

from pydantic import BaseModel, Field


class AggregateStats(BaseModel):
    """Aggregate statistics for a window of transactions."""
    total_transactions: int = Field(..., ge=0, description="Total number of transactions")
    success_count: int = Field(..., ge=0, description="Number of successful transactions")
    soft_fail_count: int = Field(..., ge=0, description="Number of soft failures")
    hard_fail_count: int = Field(..., ge=0, description="Number of hard failures")
    success_rate: float = Field(..., ge=0.0, le=1.0, description="Success rate")
    avg_latency_ms: float = Field(..., ge=0.0, description="Average latency")
    p95_latency_ms: float = Field(..., ge=0.0, description="95th percentile latency")
    p99_latency_ms: float = Field(..., ge=0.0, description="99th percentile latency")
    avg_retry_count: float = Field(..., ge=0.0, description="Average retry count")
    unique_issuers: int = Field(..., ge=0, description="Number of unique issuers")
    unique_methods: int = Field(..., ge=0, description="Number of unique payment methods")

    class Config:
        """Pydantic configuration."""
        frozen = False
