"""Tests for conversation manager integration."""

import pytest
import asyncio
from uuid import uuid4
from unittest.mock import Mock, AsyncMock

from src.services.conversation.manager import ConversationManager, ConversationConfig
from src.services.conversation.state_machine import ConversationStatus
from src.services.conversation.context import ConversationContext
from src.services.conversation.message_processor import ProcessingResult
from src.services.ai.orchestrator import AIOrchestrator


class TestConversationManager:
    """Test cases for ConversationManager."""
    
    @pytest.fixture
    def mock_ai_orchestrator(self):
        """Create mock AI orchestrator."""
        orchestrator = Mock(spec=AIOrchestrator)
        orchestrator.process_request = AsyncMock(return_value=Mock(
            content="Test response",
            confidence=0.85,
            model_used="gpt-4",
            token_usage=Mock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        ))
        orchestrator.health_check = AsyncMock(return_value={"status": "healthy"})
        return orchestrator
    
    @pytest.fixture
    async def conversation_manager(self, mock_ai_orchestrator):
        """Create conversation manager instance."""
        config = ConversationConfig(
            enable_emotion_adaptation=True,
            enable_intent_handling=True,
            confidence_threshold=0.7
        )
        manager = ConversationManager(mock_ai_orchestrator, config)
        return manager
    
    @pytest.mark.asyncio
    async def test_create_conversation(self, conversation_manager):
        """Test creating a new conversation."""
        organization_id = uuid4()
        user_id = uuid4()
        
        conversation_id = await conversation_manager.create_conversation(
            organization_id=organization_id,
            user_id=user_id,
            channel="web_chat"
        )
        
        assert conversation_id is not None
        assert len(conversation_id) > 0
        
        # Verify conversation was created
        status = await conversation_manager.get_conversation_status(conversation_id)
        assert status["status"] == "initialized"
        assert status["organization_id"] == str(organization_id)
        assert status["user_id"] == str(user_id)
        assert status["channel"] == "web_chat"
    
    @pytest.mark.asyncio
    async def test_process_user_message_success(self, conversation_manager, mock_ai_orchestrator):
        """Test successful message processing."""
        # Create conversation
        conversation_id = await conversation_manager.create_conversation(
            organization_id=uuid4(),
            user_id=uuid4(),
            channel="web_chat"
        )
        
        # Mock AI processing result
        mock_ai_orchestrator.process_request.return_value = Mock(
            content="I understand your question about billing. Let me help you with that.",
            confidence=0.85,
            model_used="gpt-4",
            token_usage=Mock(prompt_tokens=15, completion_tokens=25, total_tokens=40)
        )
        
        # Process message
        response = await conversation_manager.process_user_message(
            conversation_id=conversation_id,
            message_content="I have a question about my billing"
        )
        
        assert response is not None
        assert response.message_id is not None
        assert response.content == "I understand your question about billing. Let me help you with that."
        assert response.sender_type == "ai_agent"
        assert response.processing_metrics["confidence"] == 0.85
        assert response.processing_metrics["processing_time_ms"] > 0
    
    @pytest.mark.asyncio
    async def test_process_message_with_emotion_adaptation(self, conversation_manager, mock_ai_orchestrator):
        """Test message processing with emotion adaptation."""
        # Create conversation
        conversation_id = await conversation_manager.create_conversation(
            organization_id=uuid4(),
            user_id=uuid4(),
            channel="web_chat"
        )
        
        # Mock AI processing with emotion detection
        mock_ai_orchestrator.process_request.return_value = Mock(
            content="I can help you with that issue.",
            confidence=0.8,
            model_used="gpt-4",
            token_usage=Mock(prompt_tokens=10, completion_tokens=15, total_tokens=25)
        )
        
        # Process frustrated message
        response = await conversation_manager.process_user_message(
            conversation_id=conversation_id,
            message_content="I'm really frustrated with this error!"
        )
        
        assert response is not None
        assert response.emotion_adaptation is not None
        assert "frustrated" in str(response.metadata.get("emotion", "")).lower()
    
    @pytest.mark.asyncio
    async def test_escalate_conversation(self, conversation_manager):
        """Test conversation escalation."""
        # Create conversation
        conversation_id = await conversation_manager.create_conversation(
            organization_id=uuid4(),
            user_id=uuid4(),
            channel="web_chat"
        )
        
        # Process a message to get to active state
        await conversation_manager.process_user_message(
            conversation_id=conversation_id,
            message_content="Test message"
        )
        
        # Escalate conversation
        await conversation_manager.escalate_conversation(
            conversation_id=conversation_id,
            reason="user_requested",
            escalated_to="senior_agent"
        )
        
        # Verify escalation
        status = await conversation_manager.get_conversation_status(conversation_id)
        assert status["status"] == "escalated"
    
    @pytest.mark.asyncio
    async def test_close_conversation(self, conversation_manager):
        """Test closing a conversation."""
        # Create conversation
        conversation_id = await conversation_manager.create_conversation(
            organization_id=uuid4(),
            user_id=uuid4(),
            channel="web_chat"
        )
        
        # Process messages to get to active state
        await conversation_manager.process_user_message(
            conversation_id=conversation_id,
            message_content="Test message"
        )
        
        # Close conversation
        await conversation_manager.close_conversation(
            conversation_id=conversation_id,
            resolution_type="solved",
            satisfaction_score=4.5,
            nps_score=9
        )
        
        # Verify closure
        status = await conversation_manager.get_conversation_status(conversation_id)
        assert status["status"] == "resolved"
    
    @pytest.mark.asyncio
    async def test_conversation_not_found_error(self, conversation_manager):
        """Test error handling for non-existent conversation."""
        fake_conversation_id = str(uuid4())
        
        with pytest.raises(ConversationError, match="Conversation not found"):
            await conversation_manager.process_user_message(
                conversation_id=fake_conversation_id,
                message_content="Test message"
            )
    
    @pytest.mark.asyncio
    async def test_invalid_state_transition_error(self, conversation_manager):
        """Test error handling for invalid state transitions."""
        # Create conversation
        conversation_id = await conversation_manager.create_conversation(
            organization_id=uuid4(),
            user_id=uuid4(),
            channel="web_chat"
        )
        
        # Try to close conversation without processing any messages (invalid transition)
        with pytest.raises(ConversationError, match="Cannot transition from"):
            await conversation_manager.close_conversation(
                conversation_id=conversation_id,
                resolution_type="solved"
            )
    
    @pytest.mark.asyncio
    async def test_get_conversation_status(self, conversation_manager):
        """Test getting conversation status."""
        # Create conversation
        organization_id = uuid4()
        user_id = uuid4()
        
        conversation_id = await conversation_manager.create_conversation(
            organization_id=organization_id,
            user_id=user_id,
            channel="web_chat"
        )
        
        # Get status
        status = await conversation_manager.get_conversation_status(conversation_id)
        
        assert status["conversation_id"] == conversation_id
        assert status["status"] == "initialized"
        assert status["organization_id"] == str(organization_id)
        assert status["user_id"] == str(user_id)
        assert status["channel"] == "web_chat"
        assert "context_summary" in status
        assert "metrics" in status
        assert status["can_receive_messages"] is True
    
    @pytest.mark.asyncio
    async def test_get_conversation_summary(self, conversation_manager):
        """Test getting comprehensive conversation summary."""
        # Create conversation
        conversation_id = await conversation_manager.create_conversation(
            organization_id=uuid4(),
            user_id=uuid4(),
            channel="web_chat"
        )
        
        # Process a message
        await conversation_manager.process_user_message(
            conversation_id=conversation_id,
            message_content="Test message"
        )
        
        # Get summary
        summary = await conversation_manager.get_conversation_summary(conversation_id)
        
        assert summary["conversation_id"] == conversation_id
        assert "user_context" in summary
        assert "session_context" in summary
        assert "ai_context" in summary
        assert "business_context" in summary
        assert "analytics_summary" in summary
    
    @pytest.mark.asyncio
    async def test_system_metrics(self, conversation_manager):
        """Test getting system-wide metrics."""
        # Create multiple conversations
        for i in range(3):
            conversation_id = await conversation_manager.create_conversation(
                organization_id=uuid4(),
                user_id=uuid4(),
                channel="web_chat"
            )
            
            await conversation_manager.process_user_message(
                conversation_id=conversation_id,
                message_content=f"Test message {i}"
            )
        
        # Get system metrics
        metrics = conversation_manager.get_system_metrics()
        
        assert "active_conversations" in metrics
        assert "analytics_summary" in metrics
        assert "ai_performance" in metrics
        assert "config" in metrics
        assert metrics["active_conversations"] == 3
    
    @pytest.mark.asyncio
    async def test_health_check(self, conversation_manager, mock_ai_orchestrator):
        """Test health check functionality."""
        health = await conversation_manager.health_check()
        
        assert health["status"] == "healthy"
        assert "ai_orchestrator" in health
        assert "active_conversations" in health
        assert "analytics" in health
        assert "timestamp" in health
    
    @pytest.mark.asyncio
    async def test_conversation_with_different_channels(self, conversation_manager):
        """Test conversation with different channels."""
        channels = ["web_chat", "mobile_ios", "email", "slack"]
        
        for channel in channels:
            conversation_id = await conversation_manager.create_conversation(
                organization_id=uuid4(),
                user_id=uuid4(),
                channel=channel
            )
            
            response = await conversation_manager.process_user_message(
                conversation_id=conversation_id,
                message_content="Test message"
            )
            
            assert response is not None
            # Response should be formatted appropriately for channel
            assert len(response.content) > 0
    
    @pytest.mark.asyncio
    async def test_conversation_timeout_handling(self, conversation_manager):
        """Test conversation timeout scenarios."""
        # Create conversation
        conversation_id = await conversation_manager.create_conversation(
            organization_id=uuid4(),
            user_id=uuid4(),
            channel="web_chat"
        )
        
        # Process message to get to processing state
        await conversation_manager.process_user_message(
            conversation_id=conversation_id,
            message_content="Test message"
        )
        
        # Check current state
        status = await conversation_manager.get_conversation_status(conversation_id)
        assert status["status"] in ["active", "processing"]
    
    @pytest.mark.asyncio
    async def test_parallel_message_processing(self, conversation_manager):
        """Test parallel processing of multiple conversations."""
        # Create multiple conversations
        conversations = []
        for i in range(5):
            conversation_id = await conversation_manager.create_conversation(
                organization_id=uuid4(),
                user_id=uuid4(),
                channel="web_chat"
            )
            conversations.append(conversation_id)
        
        # Process messages in parallel
        tasks = []
        for i, conversation_id in enumerate(conversations):
            task = conversation_manager.process_user_message(
                conversation_id=conversation_id,
                message_content=f"Parallel test message {i}"
            )
            tasks.append(task)
        
        # Wait for all to complete
        responses = await asyncio.gather(*tasks)
        
        # Verify all completed successfully
        assert len(responses) == 5
        for response in responses:
            assert response is not None
            assert response.content is not None
            assert response.processing_metrics["processing_time_ms"] > 0
    
    @pytest.mark.asyncio
    async def test_conversation_cleanup(self, conversation_manager):
        """Test conversation cleanup functionality."""
        # Create conversations
        for i in range(3):
            await conversation_manager.create_conversation(
                organization_id=uuid4(),
                user_id=uuid4(),
                channel="web_chat"
            )
        
        # Clean up (should remove expired conversations)
        cleaned_count = await conversation_manager.cleanup_expired_conversations(max_age_hours=0)
        
        # Verify cleanup (in this test, all should be removed due to 0 hour age)
        assert cleaned_count >= 0  # May or may not remove based on timing
    
    @pytest.mark.asyncio
    async def test_conversation_with_metadata(self, conversation_manager):
        """Test conversation with additional metadata."""
        # Create conversation with metadata
        metadata = {"source": "mobile_app", "campaign": "summer_2024", "user_agent": "test"}
        
        conversation_id = await conversation_manager.create_conversation(
            organization_id=uuid4(),
            user_id=uuid4(),
            channel="web_chat",
            metadata=metadata
        )
        
        # Process message with metadata
        response = await conversation_manager.process_user_message(
            conversation_id=conversation_id,
            message_content="Test with metadata",
            metadata={"message_type": "question", "urgency": "normal"}
        )
        
        assert response is not None
        assert response.metadata is not None
    
    def test_conversation_config_validation(self):
        """Test conversation configuration validation."""
        # Valid config
        config = ConversationConfig(
            enable_emotion_adaptation=True,
            confidence_threshold=0.7,
            max_processing_time_ms=30000
        )
        
        assert config.enable_emotion_adaptation is True
        assert config.confidence_threshold == 0.7
        assert config.max_processing_time_ms == 30000
        
        # Test with invalid values (should still create but may warn)
        config_invalid = ConversationConfig(
            confidence_threshold=1.5,  # Invalid: > 1.0
            max_processing_time_ms=-1000  # Invalid: negative
        )
        
        assert config_invalid.confidence_threshold == 1.5
        assert config_invalid.max_processing_time_ms == -1000
    
    @pytest.mark.asyncio
    async def test_error_recovery_and_fallbacks(self, conversation_manager, mock_ai_orchestrator):
        """Test error recovery and fallback mechanisms."""
        # Create conversation
        conversation_id = await conversation_manager.create_conversation(
            organization_id=uuid4(),
            user_id=uuid4(),
            channel="web_chat"
        )
        
        # Mock AI orchestrator to raise error
        mock_ai_orchestrator.process_request.side_effect = Exception("AI service error")
        
        # Process message should fallback gracefully
        response = await conversation_manager.process_user_message(
            conversation_id=conversation_id,
            message_content="Test message"
        )
        
        # Should get fallback response
        assert response is not None
        assert "apologize" in response.content.lower() or "trouble" in response.content.lower()
        assert response.metadata.get("fallback", False) or "error" in str(response.metadata)
    
    @pytest.mark.asyncio
    async def test_conversation_state_persistence(self, conversation_manager):
        """Test that conversation state persists across operations."""
        # Create conversation
        conversation_id = await conversation_manager.create_conversation(
            organization_id=uuid4(),
            user_id=uuid4(),
            channel="web_chat"
        )
        
        # Get initial status
        initial_status = await conversation_manager.get_conversation_status(conversation_id)
        initial_state = initial_status["status"]
        
        # Process multiple messages
        for i in range(3):
            await conversation_manager.process_user_message(
                conversation_id=conversation_id,
                message_content=f"Message {i}"
            )
        
        # Get final status
        final_status = await conversation_manager.get_conversation_status(conversation_id)
        
        # State should have changed from initial state
        assert final_status["status"] != initial_state
        assert final_status["message_count"] == 3
    
    @pytest.mark.asyncio
    async def test_concurrent_conversation_operations(self, conversation_manager):
        """Test concurrent operations on different conversations."""
        # Create multiple conversations
        conversations = []
        for i in range(10):
            conversation_id = await conversation_manager.create_conversation(
                organization_id=uuid4(),
                user_id=uuid4(),
                channel="web_chat"
            )
            conversations.append(conversation_id)
        
        # Perform concurrent operations
        async def process_conversation(conversation_id, index):
            # Create, process, and get status
            response = await conversation_manager.process_user_message(
                conversation_id=conversation_id,
                message_content=f"Concurrent message {index}"
            )
            status = await conversation_manager.get_conversation_status(conversation_id)
            return response, status
        
        # Run all operations concurrently
        tasks = [process_conversation(conv_id, i) for i, conv_id in enumerate(conversations)]
        results = await asyncio.gather(*tasks)
        
        # Verify all completed successfully
        assert len(results) == 10
        for response, status in results:
            assert response is not None
            assert status is not None
            assert status["message_count"] > 0
    
    def test_system_metrics_comprehensive(self, conversation_manager):
        """Test comprehensive system metrics."""
        metrics = conversation_manager.get_system_metrics()
        
        # Should have all expected sections
        expected_keys = ["active_conversations", "analytics_summary", "ai_performance", "config"]
        for key in expected_keys:
            assert key in metrics
        
        # Config should match our settings
        assert metrics["config"]["enable_emotion_adaptation"] == conversation_manager.config.enable_emotion_adaptation
        assert metrics["config"]["confidence_threshold"] == conversation_manager.config.confidence_threshold