"""Append-only audit log for compliance and debugging."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class AuditLog:
    """Append-only audit log for all agent decisions and actions."""
    
    def __init__(self, log_dir: str = ".payops_logs"):
        """Initialize audit log.
        
        Args:
            log_dir: Directory for log files
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.current_log_file = self._get_current_log_file()
    
    def _get_current_log_file(self) -> Path:
        """Get current log file (one per day)."""
        date_str = datetime.now().strftime("%Y%m%d")
        return self.log_dir / f"audit_{date_str}.jsonl"
    
    def log_decision(
        self,
        decision_id: str,
        timestamp: int,
        patterns: List[str],
        hypotheses: List[str],
        options: List[str],
        selected_option: str,
        rationale: str,
        confidence: float,
        nrv: float,
        requires_approval: bool
    ) -> bool:
        """Log a decision event.
        
        Args:
            decision_id: Unique decision identifier
            timestamp: Decision timestamp
            patterns: Detected patterns
            hypotheses: Generated hypotheses
            options: Available options
            selected_option: Selected option
            rationale: Decision rationale
            confidence: Confidence score
            nrv: Net recovery value
            requires_approval: Whether approval required
            
        Returns:
            True if successful
        """
        event = {
            "event_type": "decision",
            "decision_id": decision_id,
            "timestamp": timestamp,
            "datetime": datetime.fromtimestamp(timestamp / 1000).isoformat(),
            "patterns": patterns,
            "hypotheses": hypotheses,
            "options": options,
            "selected_option": selected_option,
            "rationale": rationale,
            "confidence": confidence,
            "nrv": nrv,
            "requires_approval": requires_approval
        }
        return self._append_event(event)
    
    def log_action(
        self,
        action_id: str,
        timestamp: int,
        action_type: str,
        target: str,
        parameters: Dict[str, Any],
        success: bool,
        error: str = None,
        pre_mortem_risk: float = None
    ) -> bool:
        """Log an action event.
        
        Args:
            action_id: Unique action identifier
            timestamp: Action timestamp
            action_type: Type of action
            target: Action target
            parameters: Action parameters
            success: Whether action succeeded
            error: Error message if failed
            pre_mortem_risk: Pre-mortem risk score
            
        Returns:
            True if successful
        """
        event = {
            "event_type": "action",
            "action_id": action_id,
            "timestamp": timestamp,
            "datetime": datetime.fromtimestamp(timestamp / 1000).isoformat(),
            "action_type": action_type,
            "target": target,
            "parameters": parameters,
            "success": success,
            "error": error,
            "pre_mortem_risk": pre_mortem_risk
        }
        return self._append_event(event)
    
    def log_learning(
        self,
        learning_id: str,
        timestamp: int,
        intervention_id: str,
        expected_outcome: Dict[str, float],
        actual_outcome: Dict[str, float],
        accuracy: float,
        success: bool,
        learnings: List[str]
    ) -> bool:
        """Log a learning event.
        
        Args:
            learning_id: Unique learning identifier
            timestamp: Learning timestamp
            intervention_id: Related intervention ID
            expected_outcome: Expected outcome metrics
            actual_outcome: Actual outcome metrics
            accuracy: Accuracy score
            success: Whether intervention succeeded
            learnings: Key learnings
            
        Returns:
            True if successful
        """
        event = {
            "event_type": "learning",
            "learning_id": learning_id,
            "timestamp": timestamp,
            "datetime": datetime.fromtimestamp(timestamp / 1000).isoformat(),
            "intervention_id": intervention_id,
            "expected_outcome": expected_outcome,
            "actual_outcome": actual_outcome,
            "accuracy": accuracy,
            "success": success,
            "learnings": learnings
        }
        return self._append_event(event)
    
    def log_rollback(
        self,
        rollback_id: str,
        timestamp: int,
        intervention_id: str,
        reason: str,
        automatic: bool
    ) -> bool:
        """Log a rollback event.
        
        Args:
            rollback_id: Unique rollback identifier
            timestamp: Rollback timestamp
            intervention_id: Intervention being rolled back
            reason: Rollback reason
            automatic: Whether rollback was automatic
            
        Returns:
            True if successful
        """
        event = {
            "event_type": "rollback",
            "rollback_id": rollback_id,
            "timestamp": timestamp,
            "datetime": datetime.fromtimestamp(timestamp / 1000).isoformat(),
            "intervention_id": intervention_id,
            "reason": reason,
            "automatic": automatic
        }
        return self._append_event(event)
    
    def _append_event(self, event: Dict[str, Any]) -> bool:
        """Append event to log file.
        
        Args:
            event: Event dictionary
            
        Returns:
            True if successful
        """
        try:
            # Check if we need a new log file (new day)
            current_file = self._get_current_log_file()
            if current_file != self.current_log_file:
                self.current_log_file = current_file
            
            # Append event as JSON line
            with open(self.current_log_file, 'a') as f:
                f.write(json.dumps(event) + '\n')
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to append audit event: {e}")
            return False
    
    def query_events(
        self,
        event_type: str = None,
        start_time: int = None,
        end_time: int = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query audit log events.
        
        Args:
            event_type: Filter by event type
            start_time: Start timestamp (ms)
            end_time: End timestamp (ms)
            limit: Maximum events to return
            
        Returns:
            List of matching events
        """
        events = []
        
        try:
            # Read all log files in date range
            log_files = sorted(self.log_dir.glob("audit_*.jsonl"))
            
            for log_file in log_files:
                with open(log_file, 'r') as f:
                    for line in f:
                        if len(events) >= limit:
                            break
                        
                        event = json.loads(line.strip())
                        
                        # Apply filters
                        if event_type and event.get("event_type") != event_type:
                            continue
                        
                        if start_time and event.get("timestamp", 0) < start_time:
                            continue
                        
                        if end_time and event.get("timestamp", float('inf')) > end_time:
                            continue
                        
                        events.append(event)
                
                if len(events) >= limit:
                    break
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to query audit log: {e}")
            return []
