"""State management for persistence and recovery."""

import json
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from payops_ai.models.state import AgentState

logger = logging.getLogger(__name__)


class StateManager:
    """Manages agent state persistence and recovery."""
    
    def __init__(self, state_dir: str = ".payops_state"):
        """Initialize state manager.
        
        Args:
            state_dir: Directory for state files
        """
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(exist_ok=True)
        self.current_state_file = self.state_dir / "current_state.json"
        self.backup_dir = self.state_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)
    
    def save_state(self, state: AgentState) -> bool:
        """Save agent state to disk.
        
        Args:
            state: Agent state to save
            
        Returns:
            True if successful
        """
        try:
            # Create backup of current state if it exists
            if self.current_state_file.exists():
                # FIX #5: Use nanoseconds to avoid collision
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")  # Include microseconds
                backup_file = self.backup_dir / f"state_{timestamp}.json"
                
                # Read current state and save as backup
                current_content = self.current_state_file.read_text()
                backup_file.write_text(current_content)
                
                # Keep only last 10 backups
                backups = sorted(self.backup_dir.glob("state_*.json"))
                if len(backups) > 10:
                    for old_backup in backups[:-10]:
                        old_backup.unlink()
            
            # Save new state
            state_json = state.model_dump_json(indent=2)
            self.current_state_file.write_text(state_json)
            
            logger.info(f"State saved successfully at {state.last_updated}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
            return False
    
    def load_state(self) -> Optional[AgentState]:
        """Load agent state from disk.
        
        Returns:
            AgentState if found, None otherwise
        """
        try:
            if not self.current_state_file.exists():
                logger.warning("No saved state found")
                return None
            
            state_json = self.current_state_file.read_text()
            state = AgentState.model_validate_json(state_json)
            
            logger.info(f"State loaded successfully from {state.last_updated}")
            return state
            
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            return None
    
    def recover_from_backup(self, backup_index: int = 0) -> Optional[AgentState]:
        """Recover state from backup.
        
        Args:
            backup_index: Index of backup (0 = most recent)
            
        Returns:
            AgentState if found, None otherwise
        """
        try:
            backups = sorted(self.backup_dir.glob("state_*.json"), reverse=True)
            
            if backup_index >= len(backups):
                logger.error(f"Backup index {backup_index} out of range")
                return None
            
            backup_file = backups[backup_index]
            state_json = backup_file.read_text()
            state = AgentState.model_validate_json(state_json)
            
            logger.info(f"State recovered from backup: {backup_file.name}")
            return state
            
        except Exception as e:
            logger.error(f"Failed to recover from backup: {e}")
            return None
    
    def clear_state(self) -> bool:
        """Clear current state (for testing).
        
        Returns:
            True if successful
        """
        try:
            if self.current_state_file.exists():
                self.current_state_file.unlink()
            logger.info("State cleared")
            return True
        except Exception as e:
            logger.error(f"Failed to clear state: {e}")
            return False
