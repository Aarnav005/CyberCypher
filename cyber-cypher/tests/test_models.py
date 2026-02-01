"""Property-based tests for core data models.

Feature: payops-ai-agent
Tests transaction signal parsing robustness and state serialization.
"""

import json
from hypothesis import given, strategies as st
from hypothesis.strategies import composite
import pytest

from payops_ai.models.transaction import TransactionSignal, Outcome, PaymentMethod
from payops_ai.models.state import AgentState, ModelParameters, ObservationWindow
from payops_ai.models.hypothesis import BeliefState


# Strategies for generating test data
@composite
def valid_transaction_signal(draw):
    """Generate a valid transaction signal."""
    outcome = draw(st.sampled_from(list(Outcome)))
    
    # Use printable ASCII characters to avoid unicode validation errors
    return TransactionSignal(
        transaction_id=draw(st.text(min_size=1, max_size=50, alphabet=st.characters(min_codepoint=32, max_codepoint=126, blacklist_characters="\x00"))),
        timestamp=draw(st.integers(min_value=1, max_value=2**53)),
        outcome=outcome,
        error_code=draw(st.one_of(st.none(), st.text(min_size=1, max_size=20, alphabet=st.characters(min_codepoint=32, max_codepoint=126)))) if outcome != Outcome.SUCCESS else None,
        latency_ms=draw(st.integers(min_value=0, max_value=60000)),
        retry_count=draw(st.integers(min_value=0, max_value=10)),
        payment_method=draw(st.sampled_from(list(PaymentMethod))),
        issuer=draw(st.text(min_size=1, max_size=50, alphabet=st.characters(min_codepoint=32, max_codepoint=126, blacklist_characters="\x00"))),
        merchant_id=draw(st.text(min_size=1, max_size=50, alphabet=st.characters(min_codepoint=32, max_codepoint=126, blacklist_characters="\x00"))),
        amount=draw(st.floats(min_value=0.01, max_value=1000000.0, allow_nan=False, allow_infinity=False)),
        geography=draw(st.one_of(st.none(), st.text(min_size=1, max_size=20, alphabet=st.characters(min_codepoint=32, max_codepoint=126))))
    )


@composite
def invalid_transaction_signal_dict(draw):
    """Generate an invalid transaction signal dictionary."""
    invalid_type = draw(st.sampled_from([
        "missing_required_field",
        "negative_latency",
        "negative_amount",
        "invalid_timestamp",
        "empty_string_id"
    ]))
    
    base = {
        "transaction_id": "txn_123",
        "timestamp": 1704067200000,
        "outcome": "success",
        "latency_ms": 100,
        "retry_count": 0,
        "payment_method": "card",
        "issuer": "HDFC",
        "merchant_id": "merchant_1",
        "amount": 100.0
    }
    
    if invalid_type == "missing_required_field":
        field_to_remove = draw(st.sampled_from(["transaction_id", "timestamp", "outcome"]))
        del base[field_to_remove]
    elif invalid_type == "negative_latency":
        base["latency_ms"] = -1
    elif invalid_type == "negative_amount":
        base["amount"] = -100.0
    elif invalid_type == "invalid_timestamp":
        base["timestamp"] = 0
    elif invalid_type == "empty_string_id":
        base["transaction_id"] = ""
    
    return base


# Property 1: Transaction Parsing Robustness
# For any transaction signal (valid or invalid), the observation engine should either
# successfully parse all required fields or gracefully handle the error without crashing.

@given(signal=valid_transaction_signal())
def test_property_1_valid_transaction_parsing(signal):
    """
    Feature: payops-ai-agent, Property 1: Transaction Parsing Robustness
    Validates: Requirements 1.1, 1.4
    
    Test that valid transaction signals are parsed correctly.
    """
    # The signal is already created, so parsing succeeded
    assert signal.transaction_id is not None
    assert signal.timestamp > 0
    assert signal.outcome in Outcome
    assert signal.latency_ms >= 0
    assert signal.retry_count >= 0
    assert signal.payment_method in PaymentMethod
    assert signal.issuer is not None
    assert signal.merchant_id is not None
    assert signal.amount > 0
    
    # Test serialization works
    signal_dict = signal.model_dump()
    assert isinstance(signal_dict, dict)
    
    # Test deserialization works
    signal_reconstructed = TransactionSignal(**signal_dict)
    assert signal_reconstructed.transaction_id == signal.transaction_id
    assert signal_reconstructed.timestamp == signal.timestamp


@given(invalid_dict=invalid_transaction_signal_dict())
def test_property_1_invalid_transaction_handling(invalid_dict):
    """
    Feature: payops-ai-agent, Property 1: Transaction Parsing Robustness
    Validates: Requirements 1.1, 1.4
    
    Test that invalid transaction signals are handled gracefully.
    """
    # Invalid signals should raise validation errors, not crash
    with pytest.raises((ValueError, TypeError, KeyError)):
        TransactionSignal(**invalid_dict)
    
    # The system should not crash - the exception is caught and handled


def test_property_1_edge_cases():
    """
    Feature: payops-ai-agent, Property 1: Transaction Parsing Robustness
    Validates: Requirements 1.1, 1.4
    
    Test edge cases for transaction parsing.
    """
    # Test with minimal valid data
    minimal_signal = TransactionSignal(
        transaction_id="1",
        timestamp=1,
        outcome=Outcome.SUCCESS,
        latency_ms=0,
        retry_count=0,
        payment_method=PaymentMethod.CARD,
        issuer="X",
        merchant_id="M",
        amount=0.01
    )
    assert minimal_signal.transaction_id == "1"
    
    # Test with maximum retry count
    high_retry_signal = TransactionSignal(
        transaction_id="txn_retry",
        timestamp=1704067200000,
        outcome=Outcome.SOFT_FAIL,
        error_code="TIMEOUT",
        latency_ms=5000,
        retry_count=100,
        payment_method=PaymentMethod.UPI,
        issuer="ICICI",
        merchant_id="merchant_1",
        amount=500.0
    )
    assert high_retry_signal.retry_count == 100



# Strategies for generating agent state
@composite
def valid_agent_state(draw):
    """Generate a valid agent state."""
    timestamp = draw(st.integers(min_value=1, max_value=2**53))
    
    # Create a simple belief state
    belief_state = BeliefState(
        active_hypotheses=[],
        system_health_score=draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False)),
        uncertainty_level=draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False)),
        last_updated=timestamp
    )
    
    # Create observation window
    obs_window = ObservationWindow(
        transactions=[],
        time_range_ms=(timestamp - 60000, timestamp),
        aggregate_stats={}
    )
    
    # Create model parameters
    model_params = ModelParameters(
        anomaly_threshold=draw(st.floats(min_value=0.1, max_value=5.0, allow_nan=False)),
        min_confidence_for_action=draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False)),
        max_blast_radius_for_autonomy=draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False)),
        learning_rate=draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False)),
        conservativeness_level=draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
    )
    
    return AgentState(
        current_beliefs=belief_state,
        active_interventions=[],
        recent_observations=obs_window,
        model_parameters=model_params,
        last_updated=timestamp
    )


# Property 30: Long-Term Memory Persistence
# For any agent state, saving and then loading the state should produce an equivalent state (round-trip property).

@given(state=valid_agent_state())
def test_property_30_state_serialization_round_trip(state):
    """
    Feature: payops-ai-agent, Property 30: Long-Term Memory Persistence
    Validates: Requirements 10.5
    
    Test that agent state can be serialized and deserialized without loss.
    """
    # Serialize to dict
    state_dict = state.model_dump()
    assert isinstance(state_dict, dict)
    
    # Serialize to JSON string
    state_json = state.model_dump_json()
    assert isinstance(state_json, str)
    
    # Deserialize from dict
    state_from_dict = AgentState(**state_dict)
    assert state_from_dict.last_updated == state.last_updated
    assert state_from_dict.current_beliefs.system_health_score == state.current_beliefs.system_health_score
    assert state_from_dict.current_beliefs.uncertainty_level == state.current_beliefs.uncertainty_level
    assert state_from_dict.model_parameters.anomaly_threshold == state.model_parameters.anomaly_threshold
    
    # Deserialize from JSON
    state_from_json = AgentState.model_validate_json(state_json)
    assert state_from_json.last_updated == state.last_updated
    assert state_from_json.current_beliefs.system_health_score == state.current_beliefs.system_health_score
    
    # Round-trip should preserve all values
    assert state_from_dict.model_parameters.min_confidence_for_action == state.model_parameters.min_confidence_for_action
    assert state_from_json.model_parameters.max_blast_radius_for_autonomy == state.model_parameters.max_blast_radius_for_autonomy


def test_property_30_state_persistence_edge_cases():
    """
    Feature: payops-ai-agent, Property 30: Long-Term Memory Persistence
    Validates: Requirements 10.5
    
    Test edge cases for state persistence.
    """
    # Test with minimal state
    minimal_state = AgentState(
        current_beliefs=BeliefState(
            active_hypotheses=[],
            system_health_score=0.5,
            uncertainty_level=0.5,
            last_updated=1
        ),
        active_interventions=[],
        recent_observations=ObservationWindow(
            transactions=[],
            time_range_ms=(1, 1),
            aggregate_stats={}
        ),
        model_parameters=ModelParameters(),
        last_updated=1
    )
    
    # Round-trip
    state_json = minimal_state.model_dump_json()
    state_restored = AgentState.model_validate_json(state_json)
    assert state_restored.last_updated == 1
    assert state_restored.current_beliefs.system_health_score == 0.5
    
    # Test with extreme values
    extreme_state = AgentState(
        current_beliefs=BeliefState(
            active_hypotheses=[],
            system_health_score=1.0,
            uncertainty_level=1.0,
            last_updated=2**53 - 1
        ),
        active_interventions=[],
        recent_observations=ObservationWindow(
            transactions=[],
            time_range_ms=(1, 2**53 - 1),
            aggregate_stats={}
        ),
        model_parameters=ModelParameters(
            anomaly_threshold=5.0,
            min_confidence_for_action=1.0,
            max_blast_radius_for_autonomy=1.0,
            learning_rate=1.0,
            conservativeness_level=1.0
        ),
        last_updated=2**53 - 1
    )
    
    # Round-trip
    extreme_json = extreme_state.model_dump_json()
    extreme_restored = AgentState.model_validate_json(extreme_json)
    assert extreme_restored.last_updated == 2**53 - 1
    assert extreme_restored.model_parameters.anomaly_threshold == 5.0
