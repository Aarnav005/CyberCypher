"""Data validation for incoming signals."""

import logging
from typing import Optional, Dict, Any
from pydantic import ValidationError

from payops_ai.models.transaction import TransactionSignal
from payops_ai.models.system_metrics import SystemMetrics

logger = logging.getLogger(__name__)


class DataQualityIssue:
    """Represents a data quality issue."""
    
    def __init__(self, issue_type: str, description: str, raw_data: Optional[Dict[str, Any]] = None):
        self.issue_type = issue_type
        self.description = description
        self.raw_data = raw_data
        self.timestamp = None  # Will be set when logged


class DataValidator:
    """Validates and sanitizes incoming data.
    
    Handles invalid or missing fields gracefully and logs data quality issues.
    """
    
    def __init__(self):
        self.quality_issues: list[DataQualityIssue] = []
    
    def validate_transaction(self, data: Dict[str, Any]) -> Optional[TransactionSignal]:
        """Validate transaction signal data.
        
        Args:
            data: Raw transaction data dictionary
            
        Returns:
            TransactionSignal if valid, None if invalid
        """
        try:
            signal = TransactionSignal(**data)
            return signal
        except ValidationError as e:
            issue = DataQualityIssue(
                issue_type="validation_error",
                description=f"Transaction validation failed: {str(e)}",
                raw_data=data
            )
            self.quality_issues.append(issue)
            logger.warning(f"Invalid transaction data: {e}")
            return None
        except (TypeError, KeyError) as e:
            issue = DataQualityIssue(
                issue_type="parsing_error",
                description=f"Transaction parsing failed: {str(e)}",
                raw_data=data
            )
            self.quality_issues.append(issue)
            logger.error(f"Failed to parse transaction data: {e}")
            return None
    
    def validate_system_metrics(self, data: Dict[str, Any]) -> Optional[SystemMetrics]:
        """Validate system metrics data.
        
        Args:
            data: Raw system metrics dictionary
            
        Returns:
            SystemMetrics if valid, None if invalid
        """
        try:
            metrics = SystemMetrics(**data)
            return metrics
        except ValidationError as e:
            issue = DataQualityIssue(
                issue_type="validation_error",
                description=f"System metrics validation failed: {str(e)}",
                raw_data=data
            )
            self.quality_issues.append(issue)
            logger.warning(f"Invalid system metrics: {e}")
            return None
        except (TypeError, KeyError) as e:
            issue = DataQualityIssue(
                issue_type="parsing_error",
                description=f"System metrics parsing failed: {str(e)}",
                raw_data=data
            )
            self.quality_issues.append(issue)
            logger.error(f"Failed to parse system metrics: {e}")
            return None
    
    def get_quality_issues(self) -> list[DataQualityIssue]:
        """Get all logged data quality issues."""
        return self.quality_issues.copy()
    
    def clear_quality_issues(self) -> None:
        """Clear logged quality issues."""
        self.quality_issues.clear()
