"""Tests for conversation state machine."""

import pytest
from datetime import datetime
from uuid import UUID, uuid4

from src.services.conversation.state_machine import (
    ConversationStateMachine, ConversationStatus, StateTransitionError, InvalidStateError
)


class TestConversationStateMachine:
    """Test cases for ConversationStateMachine."""
    
    @pytest.fixture
    def state_machine(self):
        """Create state machine instance."""
        return ConversationStateMachine()
    
    def test_state_enum_values(self):
        """Test that all state enum values are correctly defined."""
        expected_states = [
            "initialized", "active", "waiting_for_user", "waiting_for_agent",
            "processing", "escalated", "transferred", "resolved", "abandoned", "archived"
        ]
        
        for state_name in expected_states:
            assert hasattr(ConversationStatus, state_name.upper())
            assert ConversationStatus(state_name).value == state_name
    
    def test_valid_transitions_from_initialized(self, state_machine):
        """Test valid transitions from INITIALIZED state."""
        current_state = ConversationStatus.INITIALIZED
        
        # Valid transitions
        assert state_machine.can_transition(current_state, ConversationStatus.ACTIVE)
        assert state_machine.can_transition(current_state, ConversationStatus.ABANDONED)
        
        # Invalid transitions
        assert not state_machine.can_transition(current_state, ConversationStatus.PROCESSING)
        assert not state_machine.can_transition(current_state, ConversationStatus.ESCALATED)
        assert not state_machine.can_transition(current_state, ConversationStatus.RESOLVED)
    
    def test_valid_transitions_from_active(self, state_machine):
        """Test valid transitions from ACTIVE state."""
        current_state = ConversationStatus.ACTIVE
        
        # Valid transitions
        assert state_machine.can_transition(current_state, ConversationStatus.PROCESSING)
        assert state_machine.can_transition(current_state, ConversationStatus.WAITING_FOR_USER)
        assert state_machine.can_transition(current_state, ConversationStatus.WAITING_FOR_AGENT)
        assert state_machine.can_transition(current_state, ConversationStatus.ESCALATED)
        assert state_machine.can_transition(current_state, ConversationStatus.RESOLVED)
        assert state_machine.can_transition(current_state, ConversationStatus.ABANDONED)
        
        # Invalid transitions
        assert not state_machine.can_transition(current_state, ConversationStatus.INITIALIZED)
        assert not state_machine.can_transition(current_state, ConversationStatus.TRANSFERRED)
    
    def test_valid_transitions_from_processing(self, state_machine):
        """Test valid transitions from PROCESSING state."""
        current_state = ConversationStatus.PROCESSING
        
        # Valid transitions
        assert state_machine.can_transition(current_state, ConversationStatus.ACTIVE)
        assert state_machine.can_transition(current_state, ConversationStatus.WAITING_FOR_USER)
        assert state_machine.can_transition(current_state, ConversationStatus.WAITING_FOR_AGENT)
        assert state_machine.can_transition(current_state, ConversationStatus.ESCALATED)
        assert state_machine.can_transition(current_state, ConversationStatus.RESOLVED)
        
        # Invalid transitions
        assert not state_machine.can_transition(current_state, ConversationStatus.INITIALIZED)
        assert not state_machine.can_transition(current_state, ConversationStatus.ABANDONED)
    
    def test_state_timeout_configuration(self, state_machine):
        """Test state timeout configurations."""
        # Test initialized timeout
        timeout = state_machine.get_state_timeout(ConversationStatus.INITIALIZED)
        assert timeout == 300  # 5 minutes
        
        # Test active timeout
        timeout = state_machine.get_state_timeout(ConversationStatus.ACTIVE)
        assert timeout == 1800  # 30 minutes
        
        # Test processing timeout
        timeout = state_machine.get_state_timeout(ConversationStatus.PROCESSING)
        assert timeout == 60  # 1 minute
        
        # Test escalated timeout (should be None)
        timeout = state_machine.get_state_timeout(ConversationStatus.ESCALATED)
        assert timeout is None
    
    def test_auto_transition_states(self, state_machine):
        """Test auto-transition states for timeouts."""
        # Test initialized -> abandoned
        auto_state = state_machine.get_auto_transition_state(ConversationStatus.INITIALIZED)
        assert auto_state == ConversationStatus.ABANDONED
        
        # Test active -> abandoned
        auto_state = state_machine.get_auto_transition_state(ConversationStatus.ACTIVE)
        assert auto_state == ConversationStatus.ABANDONED
        
        # Test processing -> escalated
        auto_state = state_machine.get_auto_transition_state(ConversationStatus.PROCESSING)
        assert auto_state == ConversationStatus.ESCALATED
        
        # Test escalated (should be None)
        auto_state = state_machine.get_auto_transition_state(ConversationStatus.ESCALATED)
        assert auto_state is None
    
    def test_state_descriptions(self, state_machine):
        """Test state descriptions."""
        description = state_machine.get_state_description(ConversationStatus.ACTIVE)
        assert "Active conversation" in description
        
        description = state_machine.get_state_description(ConversationStatus.ESCALATED)
        assert "escalated to human agent" in description
    
    def test_active_state_detection(self, state_machine):
        """Test active state detection."""
        # Active states
        assert state_machine.is_active_state(ConversationStatus.ACTIVE)
        assert state_machine.is_active_state(ConversationStatus.PROCESSING)
        assert state_machine.is_active_state(ConversationStatus.WAITING_FOR_USER)
        assert state_machine.is_active_state(ConversationStatus.WAITING_FOR_AGENT)
        
        # Non-active states
        assert not state_machine.is_active_state(ConversationStatus.INITIALIZED)
        assert not state_machine.is_active_state(ConversationStatus.ESCALATED)
        assert not state_machine.is_active_state(ConversationStatus.RESOLVED)
        assert not state_machine.is_active_state(ConversationStatus.ARCHIVED)
    
    def test_terminal_state_detection(self, state_machine):
        """Test terminal state detection."""
        assert state_machine.is_terminal_state(ConversationStatus.ARCHIVED)
        assert not state_machine.is_terminal_state(ConversationStatus.RESOLVED)
        assert not state_machine.is_terminal_state(ConversationStatus.ACTIVE)
    
    def test_processing_requirement_detection(self, state_machine):
        """Test processing requirement detection."""
        # States that require processing
        assert state_machine.requires_processing(ConversationStatus.INITIALIZED)
        assert state_machine.requires_processing(ConversationStatus.ACTIVE)
        assert state_machine.requires_processing(ConversationStatus.PROCESSING)
        
        # States that don't require processing
        assert not state_machine.requires_processing(ConversationStatus.ESCALATED)
        assert not state_machine.requires_processing(ConversationStatus.RESOLVED)
        assert not state_machine.requires_processing(ConversationStatus.ARCHIVED)
    
    def test_message_reception_capability(self, state_machine):
        """Test message reception capability detection."""
        # States that can receive messages
        assert state_machine.can_receive_messages(ConversationStatus.ACTIVE)
        assert state_machine.can_receive_messages(ConversationStatus.PROCESSING)
        assert state_machine.can_receive_messages(ConversationStatus.WAITING_FOR_USER)
        
        # States that cannot receive messages
        assert not state_machine.can_receive_messages(ConversationStatus.INITIALIZED)
        assert not state_machine.can_receive_messages(ConversationStatus.ESCALATED)
        assert not state_machine.can_receive_messages(ConversationStatus.RESOLVED)
        assert not state_machine.can_receive_messages(ConversationStatus.ARCHIVED)
    
    def test_valid_transitions_list(self, state_machine):
        """Test getting list of valid transitions."""
        current_state = ConversationStatus.ACTIVE
        valid_transitions = state_machine.get_valid_transitions(current_state)
        
        expected_transitions = [
            ConversationStatus.PROCESSING,
            ConversationStatus.WAITING_FOR_USER,
            ConversationStatus.WAITING_FOR_AGENT,
            ConversationStatus.ESCALATED,
            ConversationStatus.RESOLVED,
            ConversationStatus.ABANDONED
        ]
        
        assert len(valid_transitions) == len(expected_transitions)
        for transition in expected_transitions:
            assert transition in valid_transitions
    
    def test_state_metrics_generation(self, state_machine):
        """Test state metrics generation."""
        metrics = state_machine.get_state_metrics(ConversationStatus.ACTIVE)
        
        assert metrics["state"] == "active"
        assert metrics["is_active"] is True
        assert metrics["is_terminal"] is False
        assert metrics["requires_processing"] is True
        assert metrics["timeout_seconds"] == 1800
        assert metrics["auto_transition_to"] == "abandoned"
        assert "Active conversation" in metrics["description"]
    
    def test_transition_event_creation(self, state_machine):
        """Test transition event creation."""
        from_state = ConversationStatus.ACTIVE
        to_state = ConversationStatus.PROCESSING
        context = {"reason": "user_message", "message_id": "test-123"}
        
        event = state_machine.create_transition_event(from_state, to_state, context)
        
        assert event["event_type"] == "state_transition"
        assert event["from_state"] == "active"
        assert event["to_state"] == "processing"
        assert event["valid_transition"] is True
        assert event["context"] == context
        assert "transition_time" in event
    
    def test_conversation_lifecycle_validation(self, state_machine):
        """Test conversation lifecycle validation."""
        # Valid lifecycle
        valid_lifecycle = [
            ConversationStatus.INITIALIZED,
            ConversationStatus.ACTIVE,
            ConversationStatus.PROCESSING,
            ConversationStatus.RESOLVED,
            ConversationStatus.ARCHIVED
        ]
        
        assert state_machine.validate_conversation_lifecycle(valid_lifecycle) is True
        
        # Invalid lifecycle (wrong initial state)
        invalid_lifecycle = [
            ConversationStatus.ACTIVE,  # Should start with INITIALIZED
            ConversationStatus.PROCESSING,
            ConversationStatus.RESOLVED
        ]
        
        assert state_machine.validate_conversation_lifecycle(invalid_lifecycle) is False
        
        # Invalid lifecycle (invalid transition)
        invalid_transition_lifecycle = [
            ConversationStatus.INITIALIZED,
            ConversationStatus.RESOLVED,  # Invalid direct transition
            ConversationStatus.ARCHIVED
        ]
        
        assert state_machine.validate_conversation_lifecycle(invalid_transition_lifecycle) is False
    
    def test_escalation_validation(self, state_machine):
        """Test escalation-specific validation."""
        # Valid escalation transition
        assert state_machine.validate_transition(
            ConversationStatus.ACTIVE,
            ConversationStatus.ESCALATED,
            {"escalation_reason": "user_requested", "escalated_by": "system"}
        ) is True
        
        # Invalid escalation (missing required context)
        assert state_machine.validate_transition(
            ConversationStatus.ACTIVE,
            ConversationStatus.ESCALATED,
            {"escalation_reason": "user_requested"}  # Missing escalated_by
        ) is False
    
    def test_resolution_validation(self, state_machine):
        """Test resolution-specific validation."""
        # Valid resolution transition
        assert state_machine.validate_transition(
            ConversationStatus.ACTIVE,
            ConversationStatus.RESOLVED,
            {"resolution_type": "solved", "resolved_by": "ai_agent"}
        ) is True
        
        # Invalid resolution (missing required context)
        assert state_machine.validate_transition(
            ConversationStatus.ACTIVE,
            ConversationStatus.RESOLVED,
            {"resolution_type": "solved"}  # Missing resolved_by
        ) is False
    
    def test_error_exceptions(self, state_machine):
        """Test custom exception creation."""
        # State transition error
        error = StateTransitionError("active", "invalid")
        assert "Invalid transition from 'active' to 'invalid'" in str(error)
        assert error.from_state == "active"
        assert error.to_state == "invalid"
        
        # Invalid state error
        error = InvalidStateError("invalid_state")
        assert "Invalid conversation state: 'invalid_state'" in str(error)
        assert error.state == "invalid_state"
    
    def test_complex_state_transition_scenarios(self, state_machine):
        """Test complex state transition scenarios."""
        # Multiple escalations
        assert state_machine.can_transition(ConversationStatus.ESCALATED, ConversationStatus.TRANSFERRED)
        assert state_machine.can_transition(ConversationStatus.TRANSFERRED, ConversationStatus.RESOLVED)
        
        # Abandonment scenarios
        assert state_machine.can_transition(ConversationStatus.INITIALIZED, ConversationStatus.ABANDONED)
        assert state_machine.can_transition(ConversationStatus.ACTIVE, ConversationStatus.ABANDONED)
        assert state_machine.can_transition(ConversationStatus.WAITING_FOR_USER, ConversationStatus.ABANDONED)
        
        # Cannot abandon from certain states
        assert not state_machine.can_transition(ConversationStatus.ESCALATED, ConversationStatus.ABANDONED)
        assert not state_machine.can_transition(ConversationStatus.RESOLVED, ConversationStatus.ABANDONED)
        assert not state_machine.can_transition(ConversationStatus.ARCHIVED, ConversationStatus.ABANDONED)
    
    def test_edge_cases_and_boundary_conditions(self, state_machine):
        """Test edge cases and boundary conditions."""
        # Test with None values
        assert not state_machine.can_transition(None, ConversationStatus.ACTIVE)
        assert not state_machine.can_transition(ConversationStatus.ACTIVE, None)
        
        # Test invalid state strings
        with pytest.raises(ValueError):
            ConversationStatus("invalid_state")
        
        # Test empty context
        assert state_machine.validate_transition(ConversationStatus.ACTIVE, ConversationStatus.PROCESSING, {}) is True
        
        # Test None context
        assert state_machine.validate_transition(ConversationStatus.ACTIVE, ConversationStatus.PROCESSING, None) is True
    
    def test_performance_of_state_operations(self, state_machine):
        """Test performance of state operations."""
        import time
        
        # Test rapid state checks
        start_time = time.time()
        for _ in range(1000):
            state_machine.can_transition(ConversationStatus.ACTIVE, ConversationStatus.PROCESSING)
        elapsed_time = time.time() - start_time
        
        # Should be very fast (< 0.1 seconds for 1000 operations)
        assert elapsed_time < 0.1
        
        # Test rapid transition validation
        start_time = time.time()
        for _ in range(1000):
            state_machine.validate_transition(ConversationStatus.ACTIVE, ConversationStatus.PROCESSING, {})
        elapsed_time = time.time() - start_time
        
        # Should be very fast (< 0.1 seconds for 1000 operations)
        assert elapsed_time < 0.1
    
    def test_state_machine_singleton_behavior(self):
        """Test that state machine behaves consistently across instances."""
        machine1 = ConversationStateMachine()
        machine2 = ConversationStateMachine()
        
        # Should have identical behavior
        for state in ConversationStatus:
            transitions1 = machine1.get_valid_transitions(state)
            transitions2 = machine2.get_valid_transitions(state)
            assert transitions1 == transitions2
            
            for to_state in ConversationStatus:
                can_transition1 = machine1.can_transition(state, to_state)
                can_transition2 = machine2.can_transition(state, to_state)
                assert can_transition1 == can_transition2
    
    def test_comprehensive_state_coverage(self, state_machine):
        """Test that all states have proper configuration."""
        for state in ConversationStatus:
            # Should have timeout configuration (except terminal states)
            if state != ConversationStatus.ARCHIVED:
                timeout = state_machine.get_state_timeout(state)
                assert timeout is not None or state in [ConversationStatus.ESCALATED, ConversationStatus.RESOLVED]
            
            # Should have description
            description = state_machine.get_state_description(state)
            assert description and len(description) > 0
            
            # Should have metrics
            metrics = state_machine.get_state_metrics(state)
            assert metrics["state"] == state.value
            assert isinstance(metrics["is_active"], bool)
            assert isinstance(metrics["is_terminal"], bool)
            assert isinstance(metrics["requires_processing"], bool)
            
            # Should have valid transitions
            transitions = state_machine.get_valid_transitions(state)
            assert isinstance(transitions, list)
            for transition in transitions:
                assert isinstance(transition, ConversationStatus)
                assert state_machine.can_transition(state, transition) is True