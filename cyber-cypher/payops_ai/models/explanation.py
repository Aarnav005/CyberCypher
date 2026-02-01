"""Explanation data models."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class HypothesisExplanation(BaseModel):
    """Explanation of a hypothesis."""
    description: str = Field(..., description="Hypothesis description")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence level")
    supporting_evidence: List[str] = Field(
        default_factory=list,
        description="Supporting evidence"
    )
    why_not_alternatives: Optional[List[str]] = Field(
        None,
        description="Why alternatives were rejected"
    )

    class Config:
        """Pydantic configuration."""
        frozen = False


class Explanation(BaseModel):
    """Structured explanation for a decision or action."""
    situation_summary: str = Field(..., description="Summary of current situation")
    detected_patterns: List[str] = Field(
        default_factory=list,
        description="Patterns detected"
    )
    hypotheses: List[HypothesisExplanation] = Field(
        default_factory=list,
        description="Hypotheses considered"
    )
    decision_rationale: str = Field(..., description="Rationale for decision")
    action_taken: str = Field(..., description="Action taken or recommended")
    guardrails: List[str] = Field(default_factory=list, description="Guardrails applied")
    rollback_conditions: List[str] = Field(
        default_factory=list,
        description="Rollback conditions"
    )
    learning_plan: str = Field(..., description="Plan for learning from this decision")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence")
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context (e.g., RAG playbook, similar incidents)"
    )
    
    # Dual-output format fields
    executive_summary: str = Field(
        default="",
        description="2-sentence executive summary for human operators"
    )
    action_json: Dict[str, Any] = Field(
        default_factory=dict,
        description="Machine-readable action specification"
    )

    class Config:
        """Pydantic configuration."""
        frozen = False
    
    def format_dual_output(self) -> str:
        """Format explanation as dual-output (executive summary + action JSON).
        
        Returns:
            Formatted string with both outputs
        """
        import json
        
        output = "=== EXECUTIVE SUMMARY ===\n"
        output += self.executive_summary + "\n\n"
        output += "=== ACTION_JSON ===\n"
        output += json.dumps(self.action_json, indent=2)
        
        return output
