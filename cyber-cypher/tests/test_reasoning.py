"""Property-based tests for reasoning engine.

Feature: payops-ai-agent
Tests anomaly detection, pattern detection, and hypothesis generation.
"""

from hypothesis import given, strategies as st, assume
from hypothesis.strategies import composite
import pytest
import time

from payops_ai.models.baseline import BaselineStats
from payops_ai.models.aggregate import AggregateStats
from payops_ai.models.transaction import TransactionSignal, Outcome, PaymentMethod
from payops_ai.models.pattern import PatternType
from payops_ai.reasoning.anomaly import AnomalyDetector
from payops_ai.reasoning.pattern import PatternDetector


# Property 4: Anomaly Detection Sensitivity
# For any transaction stream where success rate deviates from baseline by more than
# the configured threshold, the reasoning engine should flag an anomaly.

@composite
def baseline_and_deviated_stats(draw):
    """Generate baseline and current stats with known deviation."""
    # Create baseline
    baseline_rate = draw(st.floats(min_value=0.7, max_value=0.99, allow_nan=False))
    baseline = BaselineStats(
        dimension="issuer:TEST",
        success_rate=baseline_rate,
        p50_latency_ms=100.0,
        p95_latency_ms=200.0,
        p99_latency_ms=500.0,
        avg_retry_count=0.5,
        sample_size=1000,
        period_start=1000,
        period_end=10000
    )
    
    # Create deviated stats (significant deviation)
    deviation = draw(st.floats(min_value=0.1, max_value=0.3, allow_nan=False))
    current_rate = max(0.0, min(1.0, baseline_rate - deviation))
    
    total_txns = draw(st.integers(min_value=50, max_value=500))
    success_count = int(total_txns * current_rate)
    
    current_stats = AggregateStats(
        total_transactions=total_txns,
        success_count=success_count,
        soft_fail_count=total_txns - success_count,
        hard_fail_count=0,
        success_rate=current_rate,
        avg_latency_ms=150.0,
        p95_latency_ms=250.0,
        p99_latency_ms=600.0,
        avg_retry_count=0.8,
        unique_issuers=1,
        unique_methods=1
    )
    
    return baseline, current_stats, deviation


@given(data=baseline_and_deviated_stats())
def test_property_4_anomaly_detection_sensitivity(data):
    """
    Feature: payops-ai-agent, Property 4: Anomaly Detection Sensitivity
    Validates: Requirements 2.1
    
    Test that anomalies are detected when success rate deviates significantly.
    """
    baseline, current_stats, deviation = data
    
    detector = AnomalyDetector(anomaly_threshold=2.0)
    timestamp = 50000
    
    # Detect anomalies
    patterns = detector.detect_anomalies(
        current_stats, baseline, "issuer:TEST", timestamp
    )
    
    # With significant deviation, should detect anomaly
    if deviation >= 0.1 and current_stats.total_transactions >= 10:
        assert len(patterns) > 0, f"Should detect anomaly with {deviation:.2%} deviation"
        
        # Check that pattern has evidence
        for pattern in patterns:
            assert len(pattern.evidence) > 0
            assert pattern.severity > 0.0
            assert pattern.detected_at == timestamp


@given(
    baseline_rate=st.floats(min_value=0.8, max_value=0.99, allow_nan=False),
    current_rate=st.floats(min_value=0.75, max_value=0.99, allow_nan=False)
)
def test_property_4_no_false_positives(baseline_rate, current_rate):
    """
    Feature: payops-ai-agent, Property 4: Anomaly Detection Sensitivity
    Validates: Requirements 2.1
    
    Test that small deviations don't trigger false positives.
    """
    assume(abs(baseline_rate - current_rate) < 0.05)  # Small deviation
    
    baseline = BaselineStats(
        dimension="issuer:TEST",
        success_rate=baseline_rate,
        p50_latency_ms=100.0,
        p95_latency_ms=200.0,
        p99_latency_ms=500.0,
        avg_retry_count=0.5,
        sample_size=1000,
        period_start=1000,
        period_end=10000
    )
    
    current_stats = AggregateStats(
        total_transactions=100,
        success_count=int(100 * current_rate),
        soft_fail_count=int(100 * (1 - current_rate)),
        hard_fail_count=0,
        success_rate=current_rate,
        avg_latency_ms=110.0,
        p95_latency_ms=210.0,
        p99_latency_ms=510.0,
        avg_retry_count=0.5,
        unique_issuers=1,
        unique_methods=1
    )
    
    detector = AnomalyDetector(anomaly_threshold=2.0)
    patterns = detector.detect_anomalies(current_stats, baseline, "issuer:TEST", 50000)
    
    # Small deviations should not trigger anomalies
    success_rate_patterns = [p for p in patterns if "success rate" in str(p.evidence)]
    assert len(success_rate_patterns) == 0, "Small deviation should not trigger anomaly"


def test_property_4_latency_spike_detection():
    """
    Feature: payops-ai-agent, Property 4: Anomaly Detection Sensitivity
    Validates: Requirements 2.1
    
    Test that latency spikes are detected.
    """
    baseline = BaselineStats(
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
    
    # Current stats with latency spike (2x baseline)
    current_stats = AggregateStats(
        total_transactions=100,
        success_count=95,
        soft_fail_count=5,
        hard_fail_count=0,
        success_rate=0.95,
        avg_latency_ms=200.0,
        p95_latency_ms=400.0,  # 2x baseline
        p99_latency_ms=1000.0,
        avg_retry_count=0.5,
        unique_issuers=1,
        unique_methods=1
    )
    
    detector = AnomalyDetector(anomaly_threshold=2.0)
    patterns = detector.detect_anomalies(current_stats, baseline, "issuer:HDFC", 50000)
    
    # Should detect latency anomaly
    latency_patterns = [p for p in patterns if p.type.value == "latency_spike"]
    assert len(latency_patterns) > 0, "Should detect latency spike"


def test_property_4_insufficient_data():
    """
    Feature: payops-ai-agent, Property 4: Anomaly Detection Sensitivity
    Validates: Requirements 2.1
    
    Test that insufficient data doesn't trigger anomalies.
    """
    baseline = BaselineStats(
        dimension="issuer:TEST",
        success_rate=0.95,
        p50_latency_ms=100.0,
        p95_latency_ms=200.0,
        p99_latency_ms=500.0,
        avg_retry_count=0.5,
        sample_size=1000,
        period_start=1000,
        period_end=10000
    )
    
    # Very few transactions
    current_stats = AggregateStats(
        total_transactions=5,
        success_count=2,
        soft_fail_count=3,
        hard_fail_count=0,
        success_rate=0.4,  # Low but insufficient data
        avg_latency_ms=150.0,
        p95_latency_ms=250.0,
        p99_latency_ms=600.0,
        avg_retry_count=0.8,
        unique_issuers=1,
        unique_methods=1
    )
    
    detector = AnomalyDetector(anomaly_threshold=2.0)
    patterns = detector.detect_anomalies(current_stats, baseline, "issuer:TEST", 50000)
    
    # Should not detect anomaly with insufficient data
    assert len(patterns) == 0, "Should not detect anomaly with insufficient data"


# Property 5: Pattern Detection Completeness
# Feature: payops-ai-agent, Property 5: Pattern Detection Completeness
# Validates: Requirements 2.2, 2.3, 2.4, 2.5

def test_property_5_pattern_detection_completeness():
    """Property 5: All embedded patterns should be detected.
    
    For any transaction stream with embedded patterns (issuer degradation,
    retry storm, method fatigue), the pattern detector should identify them.
    """
    detector = PatternDetector()
    timestamp = int(time.time() * 1000)
    
    # Test issuer degradation detection
    transactions_issuer = []
    for i in range(50):
        txn = TransactionSignal(
            transaction_id=f"txn_{i}",
            timestamp=timestamp + i * 100,
            outcome=Outcome.SOFT_FAIL if i % 2 == 0 else Outcome.SUCCESS,  # 50% failure
            error_code="ISSUER_TIMEOUT" if i % 2 == 0 else None,
            latency_ms=200,
            retry_count=0,
            payment_method=PaymentMethod.CARD,
            issuer="HDFC",
            merchant_id="merchant_123",
            amount=100.0,
            geography="IN"
        )
        transactions_issuer.append(txn)
    
    patterns = detector.detect_issuer_degradation(transactions_issuer, timestamp)
    assert len(patterns) > 0, "Should detect issuer degradation with 50% failure rate"
    assert any(p.type == PatternType.ISSUER_DEGRADATION for p in patterns)
    
    # Test retry storm detection
    transactions_retry = []
    for i in range(50):
        txn = TransactionSignal(
            transaction_id=f"txn_{i}",
            timestamp=timestamp + i * 100,
            outcome=Outcome.SUCCESS,
            error_code=None,
            latency_ms=200,
            retry_count=5,  # High retry count
            payment_method=PaymentMethod.CARD,
            issuer="HDFC",
            merchant_id="merchant_123",
            amount=100.0,
            geography="IN"
        )
        transactions_retry.append(txn)
    
    patterns = detector.detect_retry_storm(transactions_retry, timestamp)
    assert len(patterns) > 0, "Should detect retry storm with high retry counts"
    assert any(p.type == PatternType.RETRY_STORM for p in patterns)
    
    # Test method fatigue detection
    transactions_method = []
    for i in range(50):
        txn = TransactionSignal(
            transaction_id=f"txn_{i}",
            timestamp=timestamp + i * 100,
            outcome=Outcome.SOFT_FAIL if i % 2 == 0 else Outcome.SUCCESS,  # 50% failure
            error_code="METHOD_DECLINED" if i % 2 == 0 else None,
            latency_ms=200,
            retry_count=0,
            payment_method=PaymentMethod.UPI,
            issuer="HDFC",
            merchant_id="merchant_123",
            amount=100.0,
            geography="IN"
        )
        transactions_method.append(txn)
    
    patterns = detector.detect_method_fatigue(transactions_method, timestamp)
    assert len(patterns) > 0, "Should detect method fatigue with 50% failure rate"
    assert any(p.type == PatternType.METHOD_FATIGUE for p in patterns)


def test_property_5_no_false_positives():
    """Property 5: Normal operations should not trigger pattern detection."""
    detector = PatternDetector()
    timestamp = int(time.time() * 1000)
    
    # Normal transactions - high success rate, low retries
    transactions = []
    for i in range(100):
        txn = TransactionSignal(
            transaction_id=f"txn_{i}",
            timestamp=timestamp + i * 100,
            outcome=Outcome.SUCCESS,
            error_code=None,
            latency_ms=150,
            retry_count=0,
            payment_method=PaymentMethod.CARD,
            issuer="HDFC",
            merchant_id="merchant_123",
            amount=100.0,
            geography="IN"
        )
        transactions.append(txn)
    
    patterns = detector.detect_patterns(transactions, timestamp)
    assert len(patterns) == 0, "Normal operations should not trigger pattern detection"
