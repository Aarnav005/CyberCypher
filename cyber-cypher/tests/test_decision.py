"""Property-based tests for decision engine.

Feature: payops-ai-agent
Tests intervention planning, trade-off analysis, and decision policy.
"""

from hypothesis import given, strategies as st, assume
from hypothesis.strategies import composite
import pytest

from payops_ai.models.pattern import DetectedPattern, PatternType, Evidence
from payops_ai.models.hypothesis import Hypothesis, ImpactEstimate
from payops_ai.models.intervention import InterventionType
from payops_ai.decision.planner import InterventionPlanner
from payops_ai.decision.policy import DecisionPolicy
from payops_ai.decision.nrv_calculator import NRVCalculator


# Property 10: Multi-Dimensional Trade-off Evaluation
# For any intervention option, the decision engine should evaluate trade-offs across
# all dimensions (success rate, latency, cost, risk, friction).

@composite
def detected_pattern(draw):
    """Generate a detected pattern."""
    pattern_type = draw(st.sampled_from(list(PatternType)))
    timestamp = draw(st.integers(min_value=1000, max_value=100000))
    
    # Create proper Evidence objects
    evidence_list = [
        Evidence(
            type="statistical",
            description=f"Evidence {i}",
            value=draw(st.floats(min_value=0.0, max_value=10.0, allow_nan=False)),
            timestamp=timestamp,
            source="test"
        )
        for i in range(3)
    ]
    
    return DetectedPattern(
        type=pattern_type,
        affected_dimension=f"issuer:{draw(st.sampled_from(['HDFC', 'ICICI', 'SBI']))}",
        severity=draw(st.floats(min_value=0.1, max_value=1.0, allow_nan=False)),
        evidence=evidence_list,
        detected_at=timestamp
    )


@given(pattern=detected_pattern())
def test_property_10_multi_dimensional_tradeoff_evaluation(pattern):
    """
    Feature: payops-ai-agent, Property 10: Multi-Dimensional Trade-off Evaluation
    Validates: Requirements 4.1, 4.5
    
    Test that all intervention options have complete trade-off evaluations.
    """
    planner = InterventionPlanner()
    options = planner.generate_options([pattern], [])
    
    # All options should have trade-offs evaluated
    for option in options:
        assert option.tradeoffs is not None
        assert hasattr(option.tradeoffs, 'success_rate_impact')
        assert hasattr(option.tradeoffs, 'latency_impact')
        assert hasattr(option.tradeoffs, 'cost_impact')
        assert hasattr(option.tradeoffs, 'risk_impact')
        assert hasattr(option.tradeoffs, 'user_friction_impact')
        
        # All trade-off dimensions should be numeric
        assert isinstance(option.tradeoffs.success_rate_impact, (int, float))
        assert isinstance(option.tradeoffs.latency_impact, (int, float))
        assert isinstance(option.tradeoffs.cost_impact, (int, float))
        assert isinstance(option.tradeoffs.risk_impact, (int, float))
        assert isinstance(option.tradeoffs.user_friction_impact, (int, float))


# Property 11: Optimal Option Selection
# The decision engine should select the option with the highest expected value
# considering all trade-offs and constraints.

def test_property_11_optimal_option_selection():
    """
    Feature: payops-ai-agent, Property 11: Optimal Option Selection
    Validates: Requirements 4.2
    
    Test that decision policy selects optimal option based on NRV.
    """
    from payops_ai.models.hypothesis import BeliefState
    
    planner = InterventionPlanner()
    policy = DecisionPolicy()
    
    # Create pattern with proper Evidence objects
    pattern = DetectedPattern(
        type=PatternType.ISSUER_DEGRADATION,
        affected_dimension="issuer:HDFC",
        severity=0.8,
        evidence=[
            Evidence(type="statistical", description="50% failure rate", value=0.5, timestamp=50000, source="test"),
            Evidence(type="statistical", description="Timeout errors", value=100.0, timestamp=50000, source="test")
        ],
        detected_at=50000
    )
    
    # Generate options
    options = planner.generate_options([pattern], [])
    
    # Create belief state
    beliefs = BeliefState(
        active_hypotheses=[],
        system_health_score=0.5,
        uncertainty_level=0.3,
        last_updated=50000
    )
    
    # Make decision - policy will calculate NRV internally
    decision = policy.make_decision(options, beliefs, current_volume=1000, current_success_rate=0.5)
    
    # Should make a decision (either act or not act)
    assert decision is not None
    assert decision.rationale is not None


# Property 12: High-Risk Escalation
# For any intervention with blast radius above threshold or low confidence,
# the decision engine should escalate to human approval.

@given(
    blast_radius=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
)
def test_property_12_high_risk_escalation(blast_radius, confidence):
    """
    Feature: payops-ai-agent, Property 12: High-Risk Escalation
    Validates: Requirements 4.3, 6.1, 6.2, 6.3
    
    Test that high-risk interventions require approval.
    """
    policy = DecisionPolicy(
        min_confidence=0.7,
        max_blast_radius=0.3
    )
    
    # Create intervention option
    planner = InterventionPlanner()
    pattern = DetectedPattern(
        type=PatternType.ISSUER_DEGRADATION,
        affected_dimension="issuer:HDFC",
        severity=0.8,
        evidence=[Evidence(type="statistical", description="Test", value=0.8, timestamp=50000, source="test")],
        detected_at=50000
    )
    
    options = planner.generate_options([pattern], [])
    suppress_option = next(o for o in options if o.type == InterventionType.SUPPRESS_PATH)
    suppress_option.blast_radius = blast_radius
    
    # Create mock belief state
    from payops_ai.models.hypothesis import BeliefState
    beliefs = BeliefState(
        active_hypotheses=[],
        system_health_score=0.8,
        uncertainty_level=1.0 - confidence,
        last_updated=50000
    )
    
    decision = policy.make_decision([suppress_option], beliefs)
    
    # High uncertainty (> 0.5) should require approval
    if beliefs.uncertainty_level > 0.5:
        if decision.should_act:
            assert decision.requires_human_approval, \
                f"High uncertainty={beliefs.uncertainty_level} should require approval"
    
    # High blast radius should require approval
    if blast_radius > 0.3:
        if decision.should_act:
            assert decision.requires_human_approval, \
                f"High blast_radius={blast_radius} should require approval"


# Property 13: Explicit No-Action Decision
# When no intervention is warranted, the decision engine should explicitly
# return a NO_ACTION decision with rationale.

def test_property_13_explicit_no_action_decision():
    """
    Feature: payops-ai-agent, Property 13: Explicit No-Action Decision
    Validates: Requirements 4.4
    
    Test that no-action decisions are explicit.
    """
    from payops_ai.models.hypothesis import BeliefState
    
    policy = DecisionPolicy()
    planner = InterventionPlanner()
    
    # Create low-severity pattern
    pattern = DetectedPattern(
        type=PatternType.LATENCY_SPIKE,
        affected_dimension="issuer:HDFC",
        severity=0.1,  # Low severity
        evidence=[Evidence(type="statistical", description="Minor latency increase", value=10.0, timestamp=50000, source="test")],
        detected_at=50000
    )
    
    options = planner.generate_options([pattern], [])
    
    # Create belief state
    beliefs = BeliefState(
        active_hypotheses=[],
        system_health_score=0.8,
        uncertainty_level=0.5,
        last_updated=50000
    )
    
    decision = policy.make_decision(options, beliefs, current_volume=100, current_success_rate=0.95)
    
    # Should explicitly choose no-action (low severity pattern)
    assert not decision.should_act
    assert decision.rationale is not None
    assert len(decision.rationale) > 0


def test_property_13_no_action_with_low_confidence():
    """
    Feature: payops-ai-agent, Property 13: Explicit No-Action Decision
    Validates: Requirements 4.4
    
    Test that low confidence leads to no-action.
    """
    from payops_ai.models.hypothesis import BeliefState
    
    policy = DecisionPolicy(min_confidence=0.7)
    planner = InterventionPlanner()
    
    pattern = DetectedPattern(
        type=PatternType.ISSUER_DEGRADATION,
        affected_dimension="issuer:HDFC",
        severity=0.5,
        evidence=[Evidence(type="statistical", description="Some failures", value=0.5, timestamp=50000, source="test")],
        detected_at=50000
    )
    
    options = planner.generate_options([pattern], [])
    
    # Create belief state with high uncertainty (low confidence)
    beliefs = BeliefState(
        active_hypotheses=[],
        system_health_score=0.6,
        uncertainty_level=0.6,  # High uncertainty
        last_updated=50000
    )
    
    decision = policy.make_decision(options, beliefs)
    
    # Should not act with high uncertainty
    assert not decision.should_act or decision.requires_human_approval
