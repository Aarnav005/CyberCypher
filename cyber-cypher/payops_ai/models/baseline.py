"""Baseline statistics data models."""

from pydantic import BaseModel, Field


class BaselineStats(BaseModel):
    """Historical baseline statistics for comparison.
    
    Used to detect deviations from normal operating parameters.
    """
    dimension: str = Field(..., min_length=1, description="Dimension identifier (e.g., 'issuer:HDFC')")
    success_rate: float = Field(..., ge=0.0, le=1.0, description="Historical success rate")
    p50_latency_ms: float = Field(..., ge=0.0, description="50th percentile latency")
    p95_latency_ms: float = Field(..., ge=0.0, description="95th percentile latency")
    p99_latency_ms: float = Field(..., ge=0.0, description="99th percentile latency")
    avg_retry_count: float = Field(..., ge=0.0, description="Average retry count")
    sample_size: int = Field(..., gt=0, description="Number of samples in baseline")
    period_start: int = Field(..., gt=0, description="Baseline period start timestamp")
    period_end: int = Field(..., gt=0, description="Baseline period end timestamp")
    
    # Rolling baseline fields (EWMA)
    success_rate_std: float = Field(default=0.05, ge=0.0, description="Standard deviation of success rate")
    latency_std: float = Field(default=50.0, ge=0.0, description="Standard deviation of latency")
    retry_count_std: float = Field(default=0.5, ge=0.0, description="Standard deviation of retry count")

    class Config:
        """Pydantic configuration."""
        frozen = False


class RollingBaseline(BaseModel):
    """Rolling baseline with EWMA tracking.
    
    Tracks exponentially weighted moving averages and variance for anomaly detection.
    """
    dimension: str = Field(..., min_length=1, description="Dimension identifier")
    
    # EWMA values
    success_rate_ewma: float = Field(default=0.95, ge=0.0, le=1.0, description="EWMA of success rate")
    latency_ewma: float = Field(default=200.0, ge=0.0, description="EWMA of latency")
    retry_count_ewma: float = Field(default=0.5, ge=0.0, description="EWMA of retry count")
    
    # Variance tracking (for Z-score calculation)
    success_rate_variance: float = Field(default=0.0025, ge=0.0, description="Variance of success rate")
    latency_variance: float = Field(default=2500.0, ge=0.0, description="Variance of latency")
    retry_count_variance: float = Field(default=0.25, ge=0.0, description="Variance of retry count")
    
    # Metadata
    sample_count: int = Field(default=0, ge=0, description="Number of samples processed")
    last_updated: int = Field(..., gt=0, description="Last update timestamp")
    alpha: float = Field(default=0.2, ge=0.0, le=1.0, description="EWMA smoothing factor")
    
    class Config:
        """Pydantic configuration."""
        frozen = False
    
    def update(self, success_rate: float, latency: float, retry_count: float, timestamp: int) -> None:
        """Update rolling baseline with new observation.
        
        Args:
            success_rate: Current success rate
            latency: Current latency
            retry_count: Current retry count
            timestamp: Current timestamp
        """
        if self.sample_count == 0:
            # Initialize with first observation
            self.success_rate_ewma = success_rate
            self.latency_ewma = latency
            self.retry_count_ewma = retry_count
        else:
            # Update EWMA: new_ewma = alpha * current + (1 - alpha) * old_ewma
            self.success_rate_ewma = self.alpha * success_rate + (1 - self.alpha) * self.success_rate_ewma
            self.latency_ewma = self.alpha * latency + (1 - self.alpha) * self.latency_ewma
            self.retry_count_ewma = self.alpha * retry_count + (1 - self.alpha) * self.retry_count_ewma
            
            # Update variance: var = alpha * (x - ewma)^2 + (1 - alpha) * old_var
            self.success_rate_variance = self.alpha * (success_rate - self.success_rate_ewma) ** 2 + (1 - self.alpha) * self.success_rate_variance
            self.latency_variance = self.alpha * (latency - self.latency_ewma) ** 2 + (1 - self.alpha) * self.latency_variance
            self.retry_count_variance = self.alpha * (retry_count - self.retry_count_ewma) ** 2 + (1 - self.alpha) * self.retry_count_variance
        
        self.sample_count += 1
        self.last_updated = timestamp
    
    def get_std(self, metric: str) -> float:
        """Get standard deviation for a metric.
        
        Args:
            metric: Metric name ('success_rate', 'latency', 'retry_count')
            
        Returns:
            Standard deviation
        """
        if metric == "success_rate":
            return max(self.success_rate_variance ** 0.5, 0.01)  # Minimum std to avoid division by zero
        elif metric == "latency":
            return max(self.latency_variance ** 0.5, 10.0)
        elif metric == "retry_count":
            return max(self.retry_count_variance ** 0.5, 0.1)
        else:
            return 1.0
    
    def calculate_z_score(self, current_value: float, metric: str) -> float:
        """Calculate Z-score for current value.
        
        Args:
            current_value: Current metric value
            metric: Metric name
            
        Returns:
            Z-score
        """
        if metric == "success_rate":
            mean = self.success_rate_ewma
        elif metric == "latency":
            mean = self.latency_ewma
        elif metric == "retry_count":
            mean = self.retry_count_ewma
        else:
            return 0.0
        
        std = self.get_std(metric)
        return abs(current_value - mean) / std
