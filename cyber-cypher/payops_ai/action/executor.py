"""Action execution with guardrails."""

import logging
import uuid
import time
from typing import Optional, Dict, Any

from payops_ai.models.intervention import InterventionOption
from payops_ai.models.execution import ExecutionResult, RollbackCondition, GuardrailConfig
from payops_ai.action.pre_mortem import PreMortemAnalyzer

logger = logging.getLogger(__name__)


class ActionExecutor:
    """Executes interventions with safety guardrails and pre-mortem analysis."""
    
    def __init__(self, guardrails: Optional[GuardrailConfig] = None, simulation_mode: bool = True):
        """Initialize action executor.
        
        Args:
            guardrails: Guardrail configuration
            simulation_mode: If True, log actions without executing
        """
        self.guardrails = guardrails or GuardrailConfig(
            max_retry_adjustment=5,
            max_suppression_duration_ms=600000,  # 10 minutes
            protected_merchants=[],
            protected_methods=[],
            require_approval_threshold=0.3
        )
        self.simulation_mode = simulation_mode
        self.active_interventions = {}
        self.pre_mortem_analyzer = PreMortemAnalyzer()
    
    def execute(
        self,
        option: InterventionOption,
        current_state: Optional[Dict[str, Any]] = None
    ) -> tuple[ExecutionResult, Dict[str, Any]]:
        """Execute an intervention with pre-mortem analysis.
        
        Args:
            option: Intervention option to execute
            current_state: Current system state for pre-mortem analysis
            
        Returns:
            Tuple of (ExecutionResult, pre_mortem_analysis)
        """
        intervention_id = str(uuid.uuid4())
        timestamp = int(time.time() * 1000)
        
        # Perform pre-mortem analysis
        current_state = current_state or {}
        pre_mortem = self.pre_mortem_analyzer.analyze(option, current_state)
        
        logger.info(f"Pre-Mortem: Risk Score={pre_mortem['risk_score']:.2f}, Acceptable={pre_mortem['risk_acceptable']}")
        
        # Check if risk requires acknowledgment
        if pre_mortem["requires_acknowledgment"]:
            logger.warning("High-risk intervention requires explicit acknowledgment")
            risk_ack = self.pre_mortem_analyzer.create_risk_acknowledgment(option, pre_mortem)
            pre_mortem["risk_acknowledgment"] = risk_ack
        
        # Validate guardrails
        if not self._validate_guardrails(option):
            return ExecutionResult(
                success=False,
                intervention_id=intervention_id,
                executed_at=timestamp,
                expires_at=None,
                rollback_conditions=[],
                actual_parameters={},
                error="Guardrail violation"
            ), pre_mortem
        
        # Calculate expiration
        duration_ms = option.parameters.get("duration_ms")
        expires_at = timestamp + duration_ms if duration_ms else None
        
        # Create rollback conditions
        rollback_conditions = [
            RollbackCondition(
                type="time_based",
                threshold=None,
                metric=None,
                description=f"Expires at {expires_at}" if expires_at else "Manual rollback only"
            )
        ]
        
        if self.simulation_mode:
            logger.info(f"[SIMULATION] Would execute {option.type.value} on {option.target}")
        else:
            logger.info(f"Executing {option.type.value} on {option.target}")
            # In production, this would call actual payment system APIs
        
        result = ExecutionResult(
            success=True,
            intervention_id=intervention_id,
            executed_at=timestamp,
            expires_at=expires_at,
            rollback_conditions=rollback_conditions,
            actual_parameters=option.parameters,
            error=None
        )
        
        self.active_interventions[intervention_id] = result
        return result, pre_mortem
    
    def _validate_guardrails(self, option: InterventionOption) -> bool:
        """Validate intervention against guardrails."""
        # Check blast radius
        if option.blast_radius > self.guardrails.require_approval_threshold:
            logger.warning(f"Blast radius {option.blast_radius} exceeds threshold")
            return False
        
        # Check duration for suppressions
        duration_ms = option.parameters.get("duration_ms", 0)
        if duration_ms > self.guardrails.max_suppression_duration_ms:
            logger.warning(f"Duration {duration_ms}ms exceeds maximum")
            return False
        
        return True
    
    def rollback(self, intervention_id: str) -> bool:
        """Rollback an intervention.
        
        Args:
            intervention_id: ID of intervention to rollback
            
        Returns:
            True if successful
        """
        if intervention_id not in self.active_interventions:
            logger.warning(f"Intervention {intervention_id} not found")
            return False
        
        if self.simulation_mode:
            logger.info(f"[SIMULATION] Would rollback {intervention_id}")
        else:
            logger.info(f"Rolling back {intervention_id}")
        
        del self.active_interventions[intervention_id]
        return True
    
    def get_active_interventions(self) -> list:
        """Get all active interventions."""
        return list(self.active_interventions.values())
