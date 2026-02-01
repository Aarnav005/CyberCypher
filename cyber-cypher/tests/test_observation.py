"""Property-based tests for observation engine.

Feature: payops-ai-agent
Tests observation window time bounds and state update consistency.
"""

from hypothesis import given, strategies as st, assume
from hypothesis.strategies import composite
import pytest

from payops_ai.models.transaction import TransactionSignal, Outcome, PaymentMethod
from payops_ai.models.baseline import BaselineStats
from payops_ai.observation.window import ObservationWindow
from payops_ai.observation.stream import ObservationStream
from payops_ai.observation.baseline import BaselineManager


@composite
def transaction_with_timestamp(draw, min_time: int = 1000, max_time: int = 10000):
    """Generate a transaction with a specific timestamp range."""
    timestamp = draw(st.integers(min_value=min_time, max_value=max_time))
    
    return TransactionSignal(
        transaction_id=f"txn_{draw(st.integers(min_value=1, max_value=999999))}",
        timestamp=timestamp,
        outcome=draw(st.sampled_from(list(Outcome))),
        error_code=draw(st.one_of(st.none(), st.just("ERROR_CODE"))),
        latency_ms=draw(st.integers(min_value=0, max_value=5000)),
        retry_count=draw(st.integers(min_value=0, max_value=5)),
        payment_method=draw(st.sampled_from(list(PaymentMethod))),
        issuer=draw(st.sampled_from(["HDFC", "ICICI", "SBI", "AXIS"])),
        merchant_id=f"merchant_{draw(st.integers(min_value=1, max_value=100))}",
        amount=draw(st.floats(min_value=1.0, max_value=10000.0, allow_nan=False, allow_infinity=False))
    )


@composite
def transaction_sequence(draw, count: int = 50):
    """Generate a sequence of transactions with varying timestamps."""
    base_time = draw(st.integers(min_value=10000, max_value=100000))
    time_range = draw(st.integers(min_value=1000, max_value=50000))
    
    transactions = []
    for _ in range(count):
        txn = draw(transaction_with_timestamp(
            min_time=base_time,
            max_time=base_time + time_range
        ))
        transactions.append(txn)
    
    return transactions, base_time, time_range


# Property 2: Observation Window Time Bounds
# For any sequence of transactions with timestamps, the sliding window should contain
# only transactions within the configured time range, excluding older transactions.

@given(data=transaction_sequence(count=30))
def test_property_2_window_time_bounds(data):
    """
    Feature: payops-ai-agent, Property 2: Observation Window Time Bounds
    Validates: Requirements 1.5
    
    Test that observation window correctly filters transactions by time.
    """
    transactions, base_time, time_range = data
    
    # Create window with specific duration
    window_duration = time_range // 2
    window = ObservationWindow(window_duration_ms=window_duration)
    
    # Set current time to end of range
    current_time = base_time + time_range
    
    # Update window
    window.update(transactions, current_time)
    
    # Get filtered transactions
    windowed_txns = window.get_transactions()
    
    # All transactions in window should be within time bounds
    window_start = current_time - window_duration
    for txn in windowed_txns:
        assert window_start <= txn.timestamp <= current_time, \
            f"Transaction {txn.transaction_id} at {txn.timestamp} outside window [{window_start}, {current_time}]"
    
    # All transactions outside window should be excluded
    for txn in transactions:
        if txn.timestamp < window_start:
            assert txn not in windowed_txns, \
                f"Transaction {txn.transaction_id} at {txn.timestamp} should be excluded (before {window_start})"


@given(
    transactions=st.lists(
        transaction_with_timestamp(min_time=1000, max_time=100000),
        min_size=1,
        max_size=100
    )
)
def test_property_2_window_excludes_old_transactions(transactions):
    """
    Feature: payops-ai-agent, Property 2: Observation Window Time Bounds
    Validates: Requirements 1.5
    
    Test that old transactions are excluded from the window.
    """
    # Find the latest timestamp
    max_timestamp = max(txn.timestamp for txn in transactions)
    
    # Create a small window
    window_duration = 5000  # 5 seconds
    window = ObservationWindow(window_duration_ms=window_duration)
    
    # Update with current time = max timestamp
    window.update(transactions, max_timestamp)
    
    windowed_txns = window.get_transactions()
    
    # Count how many transactions should be in window
    window_start = max_timestamp - window_duration
    expected_count = sum(1 for txn in transactions if window_start <= txn.timestamp <= max_timestamp)
    
    assert len(windowed_txns) == expected_count, \
        f"Expected {expected_count} transactions in window, got {len(windowed_txns)}"
    
    # Verify all windowed transactions are within bounds
    for txn in windowed_txns:
        assert window_start <= txn.timestamp <= max_timestamp


def test_property_2_empty_window():
    """
    Feature: payops-ai-agent, Property 2: Observation Window Time Bounds
    Validates: Requirements 1.5
    
    Test window behavior with no transactions.
    """
    window = ObservationWindow(window_duration_ms=10000)
    window.update([], current_time_ms=50000)
    
    assert len(window.get_transactions()) == 0
    assert window.get_time_range() == (0, 0)
    
    stats = window.calculate_aggregate_stats()
    assert stats.total_transactions == 0
    assert stats.success_rate == 0.0


def test_property_2_single_transaction():
    """
    Feature: payops-ai-agent, Property 2: Observation Window Time Bounds
    Validates: Requirements 1.5
    
    Test window with a single transaction.
    """
    txn = TransactionSignal(
        transaction_id="txn_1",
        timestamp=5000,
        outcome=Outcome.SUCCESS,
        latency_ms=100,
        retry_count=0,
        payment_method=PaymentMethod.CARD,
        issuer="HDFC",
        merchant_id="merchant_1",
        amount=100.0
    )
    
    window = ObservationWindow(window_duration_ms=10000)
    window.update([txn], current_time_ms=10000)
    
    windowed_txns = window.get_transactions()
    assert len(windowed_txns) == 1
    assert windowed_txns[0].transaction_id == "txn_1"


def test_property_2_window_boundary():
    """
    Feature: payops-ai-agent, Property 2: Observation Window Time Bounds
    Validates: Requirements 1.5
    
    Test transactions exactly at window boundaries.
    """
    # Create transactions at exact boundaries
    txn_before = TransactionSignal(
        transaction_id="txn_before",
        timestamp=999,  # Just before window
        outcome=Outcome.SUCCESS,
        latency_ms=100,
        retry_count=0,
        payment_method=PaymentMethod.CARD,
        issuer="HDFC",
        merchant_id="merchant_1",
        amount=100.0
    )
    
    txn_at_start = TransactionSignal(
        transaction_id="txn_at_start",
        timestamp=1000,  # Exactly at window start
        outcome=Outcome.SUCCESS,
        latency_ms=100,
        retry_count=0,
        payment_method=PaymentMethod.CARD,
        issuer="HDFC",
        merchant_id="merchant_1",
        amount=100.0
    )
    
    txn_at_end = TransactionSignal(
        transaction_id="txn_at_end",
        timestamp=6000,  # Exactly at current time
        outcome=Outcome.SUCCESS,
        latency_ms=100,
        retry_count=0,
        payment_method=PaymentMethod.CARD,
        issuer="HDFC",
        merchant_id="merchant_1",
        amount=100.0
    )
    
    window = ObservationWindow(window_duration_ms=5000)
    window.update([txn_before, txn_at_start, txn_at_end], current_time_ms=6000)
    
    windowed_txns = window.get_transactions()
    windowed_ids = [txn.transaction_id for txn in windowed_txns]
    
    # Transaction before window should be excluded
    assert "txn_before" not in windowed_ids
    
    # Transactions at boundaries should be included
    assert "txn_at_start" in windowed_ids
    assert "txn_at_end" in windowed_ids



# Property 3: State Update Consistency
# For any sequence of system metrics or baseline data updates, the internal state should
# reflect the most recent update and maintain consistency across all state components.

@composite
def system_metrics_dict(draw):
    """Generate a system metrics dictionary."""
    return {
        "timestamp": draw(st.integers(min_value=1000, max_value=100000)),
        "gateway_health": draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False)),
        "bank_availability": {},
        "throttling_indicators": {},
        "retry_queue_depth": draw(st.integers(min_value=0, max_value=1000))
    }


@given(
    metrics_sequence=st.lists(
        system_metrics_dict(),
        min_size=1,
        max_size=20
    )
)
def test_property_3_system_metrics_update_consistency(metrics_sequence):
    """
    Feature: payops-ai-agent, Property 3: State Update Consistency
    Validates: Requirements 1.2, 1.3, 3.4, 10.1, 10.3
    
    Test that system metrics updates maintain consistency.
    """
    stream = ObservationStream()
    
    # Ingest sequence of metrics
    for metrics_data in metrics_sequence:
        stream.ingest_system_metrics(metrics_data)
    
    # Latest metrics should reflect the last update
    latest = stream.get_latest_system_metrics()
    
    if latest is not None:
        # Should have the timestamp from the last valid metrics
        last_valid_metrics = [m for m in metrics_sequence if m.get("timestamp", 0) > 0]
        if last_valid_metrics:
            assert latest.timestamp == last_valid_metrics[-1]["timestamp"]


@composite
def baseline_stats(draw):
    """Generate baseline statistics."""
    return BaselineStats(
        dimension=f"issuer:{draw(st.sampled_from(['HDFC', 'ICICI', 'SBI']))}",
        success_rate=draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False)),
        p50_latency_ms=draw(st.floats(min_value=10.0, max_value=1000.0, allow_nan=False)),
        p95_latency_ms=draw(st.floats(min_value=100.0, max_value=2000.0, allow_nan=False)),
        p99_latency_ms=draw(st.floats(min_value=200.0, max_value=5000.0, allow_nan=False)),
        avg_retry_count=draw(st.floats(min_value=0.0, max_value=5.0, allow_nan=False)),
        sample_size=draw(st.integers(min_value=100, max_value=10000)),
        period_start=draw(st.integers(min_value=1000, max_value=50000)),
        period_end=draw(st.integers(min_value=50001, max_value=100000))
    )


@given(baseline_data=baseline_stats())
def test_property_3_baseline_update_consistency(baseline_data):
    """
    Feature: payops-ai-agent, Property 3: State Update Consistency
    Validates: Requirements 1.2, 1.3, 3.4, 10.1, 10.3
    
    Test that baseline updates maintain consistency.
    """
    manager = BaselineManager()
    
    # Load baseline
    manager.load_baseline(baseline_data.dimension, baseline_data)
    
    # Retrieve baseline
    retrieved = manager.get_baseline(baseline_data.dimension)
    
    # Should match what was loaded
    assert retrieved is not None
    assert retrieved.dimension == baseline_data.dimension
    assert retrieved.success_rate == baseline_data.success_rate
    assert retrieved.sample_size == baseline_data.sample_size


def test_property_3_state_consistency_edge_cases():
    """
    Feature: payops-ai-agent, Property 3: State Update Consistency
    Validates: Requirements 1.2, 1.3, 3.4, 10.1, 10.3
    
    Test edge cases for state consistency.
    """
    # Test multiple baseline updates for same dimension
    manager = BaselineManager()
    
    baseline1 = BaselineStats(
        dimension="issuer:HDFC",
        success_rate=0.95,
        p50_latency_ms=100.0,
        p95_latency_ms=200.0,
        p99_latency_ms=500.0,
        avg_retry_count=0.5,
        sample_size=1000,
        period_start=1000,
        period_end=10000
    )
    
    baseline2 = BaselineStats(
        dimension="issuer:HDFC",
        success_rate=0.90,  # Different value
        p50_latency_ms=150.0,
        p95_latency_ms=250.0,
        p99_latency_ms=600.0,
        avg_retry_count=0.8,
        sample_size=2000,
        period_start=10001,
        period_end=20000
    )
    
    # Load first baseline
    manager.load_baseline(baseline1.dimension, baseline1)
    retrieved1 = manager.get_baseline("issuer:HDFC")
    assert retrieved1.success_rate == 0.95
    
    # Update with second baseline
    manager.load_baseline(baseline2.dimension, baseline2)
    retrieved2 = manager.get_baseline("issuer:HDFC")
    
    # Should reflect the most recent update
    assert retrieved2.success_rate == 0.90
    assert retrieved2.sample_size == 2000


def test_property_3_observation_stream_consistency():
    """
    Feature: payops-ai-agent, Property 3: State Update Consistency
    Validates: Requirements 1.2, 1.3, 3.4, 10.1, 10.3
    
    Test that observation stream maintains consistent state.
    """
    stream = ObservationStream()
    
    # Ingest valid transactions
    valid_txn = {
        "transaction_id": "txn_1",
        "timestamp": 5000,
        "outcome": "success",
        "latency_ms": 100,
        "retry_count": 0,
        "payment_method": "card",
        "issuer": "HDFC",
        "merchant_id": "merchant_1",
        "amount": 100.0
    }
    
    assert stream.ingest_transaction(valid_txn) == True
    
    # Ingest invalid transaction
    invalid_txn = {
        "transaction_id": "",  # Invalid: empty ID
        "timestamp": 5000,
        "outcome": "success"
    }
    
    assert stream.ingest_transaction(invalid_txn) == False
    
    # Statistics should be consistent
    stats = stream.get_statistics()
    assert stats["total_ingested"] == 1
    assert stats["total_invalid"] == 1
    assert stats["buffer_size"] == 1
