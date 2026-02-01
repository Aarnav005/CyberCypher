"""Configuration management for PayOps-AI.

Loads configuration from environment variables with sensible defaults.
"""

import os
from typing import Optional


def load_env_file(env_path: str = ".env") -> None:
    """Load environment variables from .env file.
    
    Args:
        env_path: Path to .env file
    """
    if not os.path.exists(env_path):
        return
    
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                if key and value:
                    os.environ[key] = value


class Config:
    """Configuration container for PayOps-AI agent."""
    
    def __init__(self):
        """Initialize configuration from environment variables."""
        # Load .env file if it exists
        load_env_file()
        
        # API Keys
        self.groq_api_key: Optional[str] = os.getenv("GROQ_API_KEY")
        self.gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY")
        
        # Kafka Configuration
        self.kafka_bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.kafka_topic: str = os.getenv("KAFKA_TOPIC", "payment-transactions")
        
        # Agent Configuration
        self.simulation_mode: bool = os.getenv("SIMULATION_MODE", "true").lower() == "true"
        self.anomaly_threshold: float = float(os.getenv("ANOMALY_THRESHOLD", "2.0"))
        self.min_confidence: float = float(os.getenv("MIN_CONFIDENCE", "0.7"))
        self.max_blast_radius: float = float(os.getenv("MAX_BLAST_RADIUS", "0.3"))
        self.window_duration_ms: int = int(os.getenv("WINDOW_DURATION_MS", "300000"))
        
        # NRV Calculator Configuration
        self.avg_ticket_value: float = float(os.getenv("AVG_TICKET_VALUE", "100.0"))
        self.latency_penalty_per_ms: float = float(os.getenv("LATENCY_PENALTY_PER_MS", "0.01"))
        self.cost_per_intervention: float = float(os.getenv("COST_PER_INTERVENTION", "5.0"))
    
    def validate(self) -> list[str]:
        """Validate configuration.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if not self.gemini_api_key:
            errors.append("GEMINI_API_KEY not set - RAG features will be disabled")
        
        if self.anomaly_threshold <= 0:
            errors.append("ANOMALY_THRESHOLD must be > 0")
        
        if not 0 <= self.min_confidence <= 1:
            errors.append("MIN_CONFIDENCE must be between 0 and 1")
        
        if not 0 <= self.max_blast_radius <= 1:
            errors.append("MAX_BLAST_RADIUS must be between 0 and 1")
        
        if self.window_duration_ms <= 0:
            errors.append("WINDOW_DURATION_MS must be > 0")
        
        return errors
    
    def __repr__(self) -> str:
        """String representation of configuration."""
        return (
            f"Config("
            f"simulation_mode={self.simulation_mode}, "
            f"anomaly_threshold={self.anomaly_threshold}, "
            f"min_confidence={self.min_confidence}, "
            f"max_blast_radius={self.max_blast_radius}, "
            f"gemini_api_key={'SET' if self.gemini_api_key else 'NOT SET'}, "
            f"groq_api_key={'SET' if self.groq_api_key else 'NOT SET'}"
            f")"
        )


# Global configuration instance
config = Config()
