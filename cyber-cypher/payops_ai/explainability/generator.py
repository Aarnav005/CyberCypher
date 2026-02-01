"""Explanation generation."""

import logging
from typing import List

from payops_ai.models.pattern import DetectedPattern
from payops_ai.models.hypothesis import Hypothesis
from payops_ai.models.intervention import InterventionDecision
from payops_ai.models.explanation import Explanation, HypothesisExplanation

logger = logging.getLogger(__name__)


class ExplanationGenerator:
    """Generates human-readable explanations."""
    
    def __init__(self):
        """Initialize explanation generator."""
        pass
    
    def explain_decision(
        self,
        patterns: List[DetectedPattern],
        hypotheses: List[Hypothesis],
        decision: InterventionDecision,
        nrv_details: dict = None,
        z_score: float = None,
        pre_mortem: dict = None
    ) -> Explanation:
        """Generate explanation for a decision with dual-output format.
        
        Args:
            patterns: Detected patterns
            hypotheses: Generated hypotheses
            decision: Intervention decision
            nrv_details: NRV calculation details
            z_score: Statistical Z-score
            pre_mortem: Pre-mortem analysis
            
        Returns:
            Explanation with executive summary and action JSON
        """
        # Situation summary
        if patterns:
            situation = f"Detected {len(patterns)} pattern(s): " + ", ".join(
                p.type.value for p in patterns
            )
        else:
            situation = "No significant patterns detected. System operating normally."
        
        # Pattern descriptions
        pattern_descriptions = [
            f"{p.type.value} in {p.affected_dimension} (severity: {p.severity:.2f})"
            for p in patterns
        ]
        
        # Hypothesis explanations
        hypothesis_explanations = [
            HypothesisExplanation(
                description=h.description,
                confidence=h.confidence,
                supporting_evidence=[e.description for e in h.supporting_evidence],
                why_not_alternatives=None
            )
            for h in hypotheses
        ]
        
        # Decision rationale
        rationale = decision.rationale
        
        # Action taken
        if decision.should_act and decision.selected_option:
            action = f"{decision.selected_option.type.value} on {decision.selected_option.target}"
            if decision.requires_human_approval:
                action += " (requires human approval)"
        else:
            action = "No action taken - continue observation"
        
        # Guardrails
        guardrails = []
        if decision.selected_option:
            if decision.selected_option.reversible:
                guardrails.append("Intervention is reversible")
            guardrails.append(f"Blast radius: {decision.selected_option.blast_radius:.2f}")
        
        # Rollback conditions
        rollback_conditions = []
        if decision.selected_option:
            duration = decision.selected_option.parameters.get("duration_ms")
            if duration:
                rollback_conditions.append(f"Auto-expires after {duration/1000:.0f} seconds")
        
        # Learning plan
        learning_plan = "Monitor outcome and adjust confidence levels based on results"
        
        # Overall confidence
        if hypotheses:
            confidence = sum(h.confidence for h in hypotheses) / len(hypotheses)
        else:
            confidence = 1.0
        
        # === DUAL-OUTPUT FORMAT ===
        
        # EXECUTIVE SUMMARY (2 sentences for humans)
        if decision.should_act and decision.selected_option:
            nrv_str = f"NRV=${nrv_details['nrv']:.2f}" if nrv_details else "positive value"
            z_str = f"Z={z_score:.2f}" if z_score else "significant deviation"
            executive_summary = (
                f"Detected {patterns[0].type.value if patterns else 'anomaly'} with {z_str}. "
                f"Recommending {decision.selected_option.type.value} on {decision.selected_option.target} ({nrv_str})."
            )
        else:
            executive_summary = (
                f"System operating normally with no significant anomalies. "
                f"No intervention required at this time."
            )
        
        # ACTION_JSON (machine-readable)
        action_json = {
            "should_act": decision.should_act,
            "action_type": decision.selected_option.type.value if decision.selected_option else "no_action",
            "target": decision.selected_option.target if decision.selected_option else None,
            "parameters": decision.selected_option.parameters if decision.selected_option else {},
            "confidence": confidence,
            "nrv": nrv_details["nrv"] if nrv_details else 0.0,
            "z_score": z_score if z_score else 0.0,
            "blast_radius": decision.selected_option.blast_radius if decision.selected_option else 0.0,
            "requires_approval": decision.requires_human_approval,
            "risk_score": pre_mortem["risk_score"] if pre_mortem else 0.0,
            "risk_acknowledged": False
        }
        
        return Explanation(
            situation_summary=situation,
            detected_patterns=pattern_descriptions,
            hypotheses=hypothesis_explanations,
            decision_rationale=rationale,
            action_taken=action,
            guardrails=guardrails,
            rollback_conditions=rollback_conditions,
            learning_plan=learning_plan,
            confidence=confidence,
            executive_summary=executive_summary,
            action_json=action_json
        )
