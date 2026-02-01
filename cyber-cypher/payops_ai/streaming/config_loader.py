"""Configuration loader for continuous payment stream."""

import logging
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class StreamConfig:
    """Complete configuration for continuous stream simulation."""
    
    # Drift parameters
    drift_theta: float
    drift_sigma: float
    drift_mean_success: float
    drift_mean_latency: float
    drift_mean_retry: float
    drift_sigma_success: float
    drift_sigma_latency: float
    drift_sigma_retry: float
    drift_retry_spike_prob: float
    drift_retry_spike_magnitude: float
    drift_retry_decay_rate: float
    
    # Issuer configurations
    issuers: Dict[str, Dict[str, float]]
    
    # Generator parameters
    transaction_rate: float
    buffer_size: int
    
    # Agent parameters
    cycle_interval: float
    window_duration_ms: int
    anomaly_threshold: float
    min_confidence: float
    max_blast_radius: float
    min_action_frequency_cycles: int
    
    # Simulation parameters
    time_scale: float
    duration_seconds: Optional[float]
    loop_rate: float
    
    # Logging
    log_level: str
    log_format: str
    
    # Optional checkpoint
    checkpoint_cycles: Optional[int] = None
    
    def validate(self) -> None:
        """Validate configuration parameters."""
        errors = []
        
        # Validate drift parameters
        if not 0.0 <= self.drift_theta <= 1.0:
            errors.append(f"drift_theta must be in [0.0, 1.0], got {self.drift_theta}")
        if self.drift_sigma < 0.0:
            errors.append(f"drift_sigma must be >= 0.0, got {self.drift_sigma}")
        if not 0.0 <= self.drift_mean_success <= 1.0:
            errors.append(f"drift_mean_success must be in [0.0, 1.0], got {self.drift_mean_success}")
        if not 50.0 <= self.drift_mean_latency <= 2000.0:
            errors.append(f"drift_mean_latency must be in [50.0, 2000.0], got {self.drift_mean_latency}")
        if not 0.0 <= self.drift_mean_retry <= 0.5:
            errors.append(f"drift_mean_retry must be in [0.0, 0.5], got {self.drift_mean_retry}")
        
        # Validate issuer configurations
        if not self.issuers:
            errors.append("At least one issuer must be configured")
        for issuer_name, config in self.issuers.items():
            if not 0.0 <= config.get('initial_success', 0.0) <= 1.0:
                errors.append(f"{issuer_name}: initial_success must be in [0.0, 1.0]")
            if not 50.0 <= config.get('initial_latency', 0.0) <= 2000.0:
                errors.append(f"{issuer_name}: initial_latency must be in [50.0, 2000.0]")
            if not 0.0 <= config.get('initial_retry_prob', 0.0) <= 0.5:
                errors.append(f"{issuer_name}: initial_retry_prob must be in [0.0, 0.5]")
        
        # Validate generator parameters
        if self.transaction_rate <= 0.0:
            errors.append(f"transaction_rate must be > 0.0, got {self.transaction_rate}")
        if self.buffer_size <= 0:
            errors.append(f"buffer_size must be > 0, got {self.buffer_size}")
        
        # Validate agent parameters
        if self.cycle_interval <= 0.0:
            errors.append(f"cycle_interval must be > 0.0, got {self.cycle_interval}")
        if self.window_duration_ms <= 0:
            errors.append(f"window_duration_ms must be > 0, got {self.window_duration_ms}")
        if self.anomaly_threshold <= 0.0:
            errors.append(f"anomaly_threshold must be > 0.0, got {self.anomaly_threshold}")
        if not 0.0 <= self.min_confidence <= 1.0:
            errors.append(f"min_confidence must be in [0.0, 1.0], got {self.min_confidence}")
        if not 0.0 <= self.max_blast_radius <= 1.0:
            errors.append(f"max_blast_radius must be in [0.0, 1.0], got {self.max_blast_radius}")
        if self.min_action_frequency_cycles <= 0:
            errors.append(f"min_action_frequency_cycles must be > 0, got {self.min_action_frequency_cycles}")
        
        # Validate simulation parameters
        if self.time_scale <= 0.0:
            errors.append(f"time_scale must be > 0.0, got {self.time_scale}")
        if self.duration_seconds is not None and self.duration_seconds <= 0.0:
            errors.append(f"duration_seconds must be > 0.0 or None, got {self.duration_seconds}")
        if self.loop_rate <= 0.0:
            errors.append(f"loop_rate must be > 0.0, got {self.loop_rate}")
        
        if errors:
            raise ValueError(f"Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors))
        
        logger.info("Configuration validated successfully")


class ConfigLoader:
    """Loads and validates configuration from YAML file."""
    
    @staticmethod
    def load(config_path: str) -> StreamConfig:
        """Load configuration from YAML file.
        
        Args:
            config_path: Path to YAML configuration file
            
        Returns:
            StreamConfig object
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If configuration is invalid
        """
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        logger.info(f"Loading configuration from {config_path}")
        
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        
        # Extract configuration sections
        drift = data.get('drift', {})
        issuers = data.get('issuers', {})
        generator = data.get('generator', {})
        agent = data.get('agent', {})
        simulation = data.get('simulation', {})
        logging_config = data.get('logging', {})
        
        # Create StreamConfig
        config = StreamConfig(
            # Drift parameters
            drift_theta=drift.get('theta', 0.1),
            drift_sigma=drift.get('sigma', 0.05),
            drift_mean_success=drift.get('mean_success', 0.95),
            drift_mean_latency=drift.get('mean_latency', 200.0),
            drift_mean_retry=drift.get('mean_retry', 0.05),
            drift_sigma_success=drift.get('sigma_success', 0.05),
            drift_sigma_latency=drift.get('sigma_latency', 20.0),
            drift_sigma_retry=drift.get('sigma_retry', 0.02),
            drift_retry_spike_prob=drift.get('retry_spike_prob', 0.01),
            drift_retry_spike_magnitude=drift.get('retry_spike_magnitude', 0.2),
            drift_retry_decay_rate=drift.get('retry_decay_rate', 0.99),
            
            # Issuer configurations
            issuers=issuers,
            
            # Generator parameters
            transaction_rate=generator.get('transaction_rate', 20.0),
            buffer_size=generator.get('buffer_size', 1000),
            
            # Agent parameters
            cycle_interval=agent.get('cycle_interval', 15.0),
            window_duration_ms=agent.get('window_duration_ms', 300000),
            anomaly_threshold=agent.get('anomaly_threshold', 2.0),
            min_confidence=agent.get('min_confidence', 0.7),
            max_blast_radius=agent.get('max_blast_radius', 0.3),
            min_action_frequency_cycles=agent.get('min_action_frequency_cycles', 6),
            
            # Simulation parameters
            time_scale=simulation.get('time_scale', 1.0),
            duration_seconds=simulation.get('duration_seconds'),
            loop_rate=simulation.get('loop_rate', 10.0),
            
            # Logging
            log_level=logging_config.get('level', 'INFO'),
            log_format=logging_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            
            # Optional checkpoint
            checkpoint_cycles=simulation.get('checkpoint_cycles')
        )
        
        # Validate configuration
        config.validate()
        
        logger.info(f"Configuration loaded: {len(config.issuers)} issuers, "
                   f"rate={config.transaction_rate} txns/s, "
                   f"cycle={config.cycle_interval}s")
        
        return config
    
    @staticmethod
    def get_default_config() -> StreamConfig:
        """Get default configuration.
        
        Returns:
            StreamConfig with default values
        """
        return StreamConfig(
            drift_theta=0.1,
            drift_sigma=0.05,
            drift_mean_success=0.95,
            drift_mean_latency=200.0,
            drift_mean_retry=0.05,
            drift_sigma_success=0.05,
            drift_sigma_latency=20.0,
            drift_sigma_retry=0.02,
            drift_retry_spike_prob=0.01,
            drift_retry_spike_magnitude=0.2,
            drift_retry_decay_rate=0.99,
            issuers={
                'HDFC': {'initial_success': 0.95, 'initial_latency': 200, 'initial_retry_prob': 0.05},
                'ICICI': {'initial_success': 0.97, 'initial_latency': 180, 'initial_retry_prob': 0.03},
                'AXIS': {'initial_success': 0.93, 'initial_latency': 220, 'initial_retry_prob': 0.07},
                'SBI': {'initial_success': 0.94, 'initial_latency': 210, 'initial_retry_prob': 0.06}
            },
            transaction_rate=20.0,
            buffer_size=1000,
            cycle_interval=15.0,
            window_duration_ms=300000,
            anomaly_threshold=2.0,
            min_confidence=0.7,
            max_blast_radius=0.3,
            min_action_frequency_cycles=6,
            time_scale=1.0,
            duration_seconds=600.0,
            loop_rate=10.0,
            log_level='INFO',
            log_format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
