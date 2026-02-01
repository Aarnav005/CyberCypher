"""Streaming components for payment data."""

# Kafka components (optional, requires kafka-python)
try:
    from payops_ai.streaming.kafka_producer import PaymentStreamProducer
    from payops_ai.streaming.kafka_consumer import PaymentStreamConsumer
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    PaymentStreamProducer = None
    PaymentStreamConsumer = None

# Core streaming components (always available)
from payops_ai.streaming.payment_generator import PaymentDataGenerator
from payops_ai.streaming.drift_engine import StochasticDriftEngine, DriftConfig, IssuerState
from payops_ai.streaming.continuous_generator import ContinuousPaymentGenerator, CircularBuffer
from payops_ai.streaming.feedback_controller import FeedbackController, ActiveIntervention
from payops_ai.streaming.continuous_loop import ContinuousAgentLoop, LoopConfig
from payops_ai.streaming.config_loader import ConfigLoader, StreamConfig

__all__ = [
    "PaymentDataGenerator",
    "StochasticDriftEngine",
    "DriftConfig",
    "IssuerState",
    "ContinuousPaymentGenerator",
    "CircularBuffer",
    "FeedbackController",
    "ActiveIntervention",
    "ContinuousAgentLoop",
    "LoopConfig",
    "ConfigLoader",
    "StreamConfig",
]

# Add Kafka components if available
if KAFKA_AVAILABLE:
    __all__.extend(["PaymentStreamProducer", "PaymentStreamConsumer"])
