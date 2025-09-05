"""Conversation state machine for managing conversation lifecycle."""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime

from src.core.exceptions import ConversationError
from src.core.logging import get_logger

logger = get_logger(__name__)


class ConversationStatus(str, Enum):
    """Conversation status enumeration matching database schema."""
    INITIALIZED = "initialized"
    ACTIVE = "active"
    WAITING_FOR_USER = "waiting_for_user"
    WAITING_FOR_AGENT = "waiting_for_agent"
    PROCESSING = "processing"
    ESCALATED = "escalated"
    TRANSFERRED = "transferred"
    RESOLVED = "resolved"
    ABANDONED = "abandoned"
    ARCHIVED = "archived"


@dataclass
class StateTransition:
    """Represents a state transition with validation rules."""
    from_state: ConversationStatus
    to_state: ConversationStatus
    requires_validation: bool = True
    timeout_seconds: Optional[int] = None
    metadata_required: List[str] = None
    
    def __post_init__(self):
        if self.metadata_required is None:
            self.metadata_required = []


class ConversationStateMachine:
    """Finite state machine for conversation lifecycle management."""
    
    # State transition rules - defines valid transitions between states
    TRANSITION_RULES: Dict[ConversationStatus, Set[ConversationStatus]] = {
        ConversationStatus.INITIALIZED: {
            ConversationStatus.ACTIVE,
            ConversationStatus.PROCESSING,
            ConversationStatus.ABANDONED
        },
        ConversationStatus.ACTIVE: {
            ConversationStatus.PROCESSING,
            ConversationStatus.WAITING_FOR_USER,
            ConversationStatus.WAITING_FOR_AGENT,
            ConversationStatus.ESCALATED,
            ConversationStatus.RESOLVED,
            ConversationStatus.ABANDONED
        },
        ConversationStatus.PROCESSING: {
            ConversationStatus.ACTIVE,
            ConversationStatus.WAITING_FOR_USER,
            ConversationStatus.WAITING_FOR_AGENT,
            ConversationStatus.ESCALATED,
            ConversationStatus.RESOLVED
        },
        ConversationStatus.WAITING_FOR_USER: {
            ConversationStatus.ACTIVE,
            ConversationStatus.PROCESSING,
            ConversationStatus.ESCALATED,
            ConversationStatus.ABANDONED
        },
        ConversationStatus.WAITING_FOR_AGENT: {
            ConversationStatus.ACTIVE,
            ConversationStatus.PROCESSING,
            ConversationStatus.ESCALATED,
            ConversationStatus.RESOLVED
        },
        ConversationStatus.ESCALATED: {
            ConversationStatus.TRANSFERRED,
            ConversationStatus.RESOLVED
        },
        ConversationStatus.TRANSFERRED: {
            ConversationStatus.ACTIVE,
            ConversationStatus.RESOLVED
        },
        ConversationStatus.RESOLVED: {
            ConversationStatus.ARCHIVED
        },
        ConversationStatus.ABANDONED: {
            ConversationStatus.ARCHIVED
        },
        ConversationStatus.ARCHIVED: set()  # Terminal state - no transitions allowed
    }
    
    # State-specific configuration
    STATE_CONFIG = {
        ConversationStatus.INITIALIZED: {
            "timeout_seconds": 300,  # 5 minutes to become active
            "auto_transition_to": ConversationStatus.ABANDONED,
            "description": "Conversation created but not yet started"
        },
        ConversationStatus.ACTIVE: {
            "timeout_seconds": 1800,  # 30 minutes of inactivity
            "auto_transition_to": ConversationStatus.ABANDONED,
            "description": "Active conversation with ongoing interaction"
        },
        ConversationStatus.PROCESSING: {
            "timeout_seconds": 60,  # 1 minute processing timeout
            "auto_transition_to": ConversationStatus.ESCALATED,
            "description": "AI is processing the current message"
        },
        ConversationStatus.WAITING_FOR_USER: {
            "timeout_seconds": 600,  # 10 minutes for user response
            "auto_transition_to": ConversationStatus.ABANDONED,
            "description": "Waiting for user input"
        },
        ConversationStatus.WAITING_FOR_AGENT: {
            "timeout_seconds": 1800,  # 30 minutes for agent response
            "auto_transition_to": ConversationStatus.ESCALATED,
            "description": "Waiting for human agent"
        },
        ConversationStatus.ESCALATED: {
            "timeout_seconds": None,  # No timeout - requires manual intervention
            "auto_transition_to": None,
            "description": "Conversation escalated to human agent"
        },
        ConversationStatus.TRANSFERRED: {
            "timeout_seconds": 300,  # 5 minutes to accept transfer
            "auto_transition_to": ConversationStatus.ESCALATED,
            "description": "Conversation transferred to another agent/queue"
        },
        ConversationStatus.RESOLVED: {
            "timeout_seconds": 86400,  # 24 hours before archiving
            "auto_transition_to": ConversationStatus.ARCHIVED,
            "description": "Conversation successfully resolved"
        },
        ConversationStatus.ABANDONED: {
            "timeout_seconds": 3600,  # 1 hour before archiving
            "auto_transition_to": ConversationStatus.ARCHIVED,
            "description": "Conversation abandoned due to inactivity"
        },
        ConversationStatus.ARCHIVED: {
            "timeout_seconds": None,  # Terminal state
            "auto_transition_to": None,
            "description": "Archived conversation - read-only"
        }
    }
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def can_transition(self, from_state: ConversationStatus, to_state: ConversationStatus) -> bool:
        """Check if a state transition is valid."""
        valid_transitions = self.TRANSITION_RULES.get(from_state, set())
        return to_state in valid_transitions
    
    def get_valid_transitions(self, current_state: ConversationStatus) -> List[ConversationStatus]:
        """Get list of valid transitions from current state."""
        return list(self.TRANSITION_RULES.get(current_state, []))
    
    def validate_transition(self, from_state: ConversationStatus, to_state: ConversationStatus, 
                          context: Optional[Dict[str, any]] = None) -> bool:
        """Validate a state transition with additional context."""
        if not self.can_transition(from_state, to_state):
            self.logger.warning(f"Invalid state transition attempted: {from_state.value} -> {to_state.value}")
            return False
        
        # Additional validation based on transition type
        if context:
            return self._validate_transition_context(from_state, to_state, context)
        
        return True
    
    def _validate_transition_context(self, from_state: ConversationStatus, to_state: ConversationStatus,
                                   context: Dict[str, any]) -> bool:
        """Validate transition based on additional context."""
        
        # Validate escalation transitions
        if to_state == ConversationStatus.ESCALATED:
            required_fields = ['escalation_reason', 'escalated_by']
            for field in required_fields:
                if field not in context or not context[field]:
                    self.logger.error(f"Missing required field for escalation: {field}")
                    return False
        
        # Validate resolution transitions
        if to_state == ConversationStatus.RESOLVED:
            required_fields = ['resolution_type', 'resolved_by']
            for field in required_fields:
                if field not in context or not context[field]:
                    self.logger.error(f"Missing required field for resolution: {field}")
                    return False
        
        # Validate transfer transitions
        if to_state == ConversationStatus.TRANSFERRED:
            required_fields = ['transfer_reason', 'transferred_to']
            for field in required_fields:
                if field not in context or not context[field]:
                    self.logger.error(
                        "Missing required field for transfer",
                        field=field,
                        context=context
                    )
                    return False
        
        return True
    
    def get_state_timeout(self, state: ConversationStatus) -> Optional[int]:
        """Get timeout configuration for a state."""
        config = self.STATE_CONFIG.get(state, {})
        return config.get("timeout_seconds")
    
    def get_auto_transition_state(self, state: ConversationStatus) -> Optional[ConversationStatus]:
        """Get the automatic transition state for timeout scenarios."""
        config = self.STATE_CONFIG.get(state, {})
        return config.get("auto_transition_to")
    
    def get_state_description(self, state: ConversationStatus) -> str:
        """Get human-readable description of a state."""
        config = self.STATE_CONFIG.get(state, {})
        return config.get("description", f"Conversation is {state.value}")
    
    def is_terminal_state(self, state: ConversationStatus) -> bool:
        """Check if a state is terminal (no further transitions allowed)."""
        return state == ConversationStatus.ARCHIVED
    
    def is_active_state(self, state: ConversationStatus) -> bool:
        """Check if conversation is in an active state (can receive messages)."""
        active_states = {
            ConversationStatus.INITIALIZED,
            ConversationStatus.ACTIVE,
            ConversationStatus.PROCESSING,
            ConversationStatus.WAITING_FOR_USER,
            ConversationStatus.WAITING_FOR_AGENT
        }
        return state in active_states
    
    def requires_processing(self, state: ConversationStatus) -> bool:
        """Check if state requires AI processing."""
        processing_states = {
            ConversationStatus.INITIALIZED,
            ConversationStatus.ACTIVE,
            ConversationStatus.PROCESSING
        }
        return state in processing_states
    
    def can_receive_messages(self, state: ConversationStatus) -> bool:
        """Check if conversation can receive new messages."""
        return self.is_active_state(state) and not self.is_terminal_state(state)
    
    def get_state_metrics(self, state: ConversationStatus) -> Dict[str, any]:
        """Get metrics configuration for a state."""
        config = self.STATE_CONFIG.get(state, {})
        return {
            "state": state.value,
            "is_active": self.is_active_state(state),
            "is_terminal": self.is_terminal_state(state),
            "requires_processing": self.requires_processing(state),
            "timeout_seconds": config.get("timeout_seconds"),
            "auto_transition_to": config.get("auto_transition_to"),
            "description": config.get("description")
        }
    
    def create_transition_event(self, from_state: ConversationStatus, to_state: ConversationStatus,
                              context: Optional[Dict[str, any]] = None) -> Dict[str, any]:
        """Create a standardized transition event for logging and analytics."""
        event = {
            "event_type": "state_transition",
            "from_state": from_state.value,
            "to_state": to_state.value,
            "transition_time": datetime.utcnow().isoformat(),
            "valid_transition": self.can_transition(from_state, to_state)
        }
        
        if context:
            event["context"] = context
        
        return event
    
    def validate_conversation_lifecycle(self, states_history: List[ConversationStatus]) -> bool:
        """Validate that a sequence of state transitions is valid."""
        if not states_history:
            return True
        
        # First state must be INITIALIZED
        if states_history[0] != ConversationStatus.INITIALIZED:
            self.logger.error(
                "Invalid initial state",
                expected=ConversationStatus.INITIALIZED.value,
                actual=states_history[0].value
            )
            return False
        
        # Validate each transition in sequence
        for i in range(len(states_history) - 1):
            from_state = states_history[i]
            to_state = states_history[i + 1]
            
            if not self.can_transition(from_state, to_state):
                self.logger.error(
                    "Invalid transition in history",
                    position=i,
                    from_state=from_state.value,
                    to_state=to_state.value
                )
                return False
        
        return True


class StateTransitionError(ConversationError):
    """Raised when an invalid state transition is attempted."""
    
    def __init__(self, from_state: str, to_state: str, message: str = None):
        if message is None:
            message = f"Invalid transition from '{from_state}' to '{to_state}'"
        super().__init__(message)
        self.from_state = from_state
        self.to_state = to_state


class InvalidStateError(ConversationError):
    """Raised when an invalid state is encountered."""
    
    def __init__(self, state: str, message: str = None):
        if message is None:
            message = f"Invalid conversation state: '{state}'"
        super().__init__(message)
        self.state = state