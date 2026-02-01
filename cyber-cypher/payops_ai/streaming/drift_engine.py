"""Stochastic drift engine for payment parameters using Ornstein-Uhlenbeck process."""

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class IssuerState:
    """Current state of an issuer with drifting parameters."""
    issuer_name: str
    success_rate: float  # 0.0 - 1.0
    latency_ms: float    # 50 - 2000
    retry_prob: float    # 0.0 - 0.5
    last_updated: float  # timestamp
    
    def __post_init__(self):
        """Validate and clip parameters to valid ranges."""
        self.success_rate = np.clip(self.success_rate, 0.0, 1.0)
        self.latency_ms = np.clip(self.latency_ms, 50.0, 2000.0)
        self.retry_prob = np.clip(self.retry_prob, 0.0, 0.5)


@dataclass
class DriftConfig:
    """Configuration for stochastic drift parameters."""
    theta: float = 0.1          # Mean reversion strength
    sigma: float = 0.05         # Volatility
    mean_success: float = 0.95  # Long-term mean success rate
    mean_latency: float = 200.0 # Long-term mean latency
    mean_retry: float = 0.05    # Long-term mean retry probability
    
    # Volatility per parameter type
    sigma_success: float = 0.05
    sigma_latency: float = 20.0
    sigma_retry: float = 0.02
    
    # Spike parameters for retry storms
    retry_spike_prob: float = 0.01  # Probability per second
    retry_spike_magnitude: float = 0.2
    retry_decay_rate: float = 0.99


class StochasticDriftEngine:
    """Manages parameter drift using Ornstein-Uhlenbeck process.
    
    The Ornstein-Uhlenbeck process is a mean-reverting stochastic process:
    dx = θ(μ - x)dt + σdW
    
    Where:
    - θ: mean reversion strength (higher = faster reversion)
    - μ: long-term mean
    - σ: volatility (higher = more random fluctuation)
    - dW: Wiener process (Brownian motion)
    """
    
    def __init__(self, config: DriftConfig):
        """Initialize drift engine.
        
        Args:
            config: Drift configuration parameters
        """
        self.config = config
        self.issuers: Dict[str, IssuerState] = {}
        self.time_scale = 1.0  # For accelerated time simulation
        
        logger.info(f"Initialized StochasticDriftEngine with theta={config.theta}, sigma={config.sigma}")
    
    def add_issuer(self, issuer_name: str, initial_success: float = 0.95,
                   initial_latency: float = 200.0, initial_retry_prob: float = 0.05) -> None:
        """Add an issuer with initial state.
        
        Args:
            issuer_name: Name of the issuer
            initial_success: Initial success rate
            initial_latency: Initial latency in ms
            initial_retry_prob: Initial retry probability
        """
        state = IssuerState(
            issuer_name=issuer_name,
            success_rate=initial_success,
            latency_ms=initial_latency,
            retry_prob=initial_retry_prob,
            last_updated=0.0
        )
        self.issuers[issuer_name] = state
        logger.info(f"Added issuer {issuer_name}: success={initial_success:.2%}, "
                   f"latency={initial_latency:.0f}ms, retry={initial_retry_prob:.2%}")
    
    def update(self, dt: float, current_time: float) -> None:
        """Update all issuer parameters using stochastic drift.
        
        Args:
            dt: Time step in seconds
            current_time: Current simulation time
        """
        # Scale dt by time_scale for accelerated simulation
        scaled_dt = dt * self.time_scale
        
        for issuer in self.issuers.values():
            # Update success rate using Ornstein-Uhlenbeck process
            drift_success = self.config.theta * (self.config.mean_success - issuer.success_rate) * scaled_dt
            diffusion_success = self.config.sigma_success * np.random.normal(0, np.sqrt(scaled_dt))
            issuer.success_rate += drift_success + diffusion_success
            issuer.success_rate = np.clip(issuer.success_rate, 0.0, 1.0)
            
            # Update latency using Ornstein-Uhlenbeck process
            drift_latency = self.config.theta * (self.config.mean_latency - issuer.latency_ms) * scaled_dt
            diffusion_latency = self.config.sigma_latency * np.random.normal(0, np.sqrt(scaled_dt))
            issuer.latency_ms += drift_latency + diffusion_latency
            issuer.latency_ms = np.clip(issuer.latency_ms, 50.0, 2000.0)
            
            # Update retry probability with occasional spikes (retry storms)
            if np.random.random() < self.config.retry_spike_prob * scaled_dt:
                # Spike event
                issuer.retry_prob += self.config.retry_spike_magnitude
                logger.debug(f"{issuer.issuer_name}: Retry spike! New retry_prob={issuer.retry_prob:.2%}")
            else:
                # Normal decay with mean reversion
                drift_retry = self.config.theta * (self.config.mean_retry - issuer.retry_prob) * scaled_dt
                decay = issuer.retry_prob * (1.0 - self.config.retry_decay_rate) * scaled_dt
                diffusion_retry = self.config.sigma_retry * np.random.normal(0, np.sqrt(scaled_dt))
                issuer.retry_prob += drift_retry - decay + diffusion_retry
            
            issuer.retry_prob = np.clip(issuer.retry_prob, 0.0, 0.5)
            issuer.last_updated = current_time
        
        logger.debug(f"Updated drift: {', '.join([f'{i.issuer_name}={i.success_rate:.2%}' for i in self.issuers.values()])}")
    
    def get_issuer_state(self, issuer_name: str) -> Optional[IssuerState]:
        """Get current state for an issuer.
        
        Args:
            issuer_name: Name of the issuer
            
        Returns:
            IssuerState if found, None otherwise
        """
        return self.issuers.get(issuer_name)
    
    def get_all_issuers(self) -> Dict[str, IssuerState]:
        """Get all issuer states.
        
        Returns:
            Dictionary of issuer name to state
        """
        return self.issuers.copy()
    
    def set_time_scale(self, time_scale: float) -> None:
        """Set time scale for accelerated simulation.
        
        Args:
            time_scale: Multiplier for time (1.0 = real-time, 10.0 = 10x speed)
        """
        self.time_scale = time_scale
        logger.info(f"Set time scale to {time_scale}x")
