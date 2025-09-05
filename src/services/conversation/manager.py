"""Main conversation manager integrating all conversation components."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from src.core.exceptions import ConversationError, ValidationError
from src.core.logging import get_logger
from src.services.conversation.state_machine import (
    ConversationStateMachine, ConversationStatus, StateTransitionError
)
from src.services.conversation.context import (
    ConversationContext, ContextManager
)
from src.services.conversation.message_processor import (
    MessageProcessor, ProcessingResult, ProcessingConfig
)
from src.services.conversation.emotion_handler import (
    EmotionResponseHandler, EmotionContext, ToneAdaptation
)
from src.services.conversation.intent_handler import (
    IntentHandler, IntentContext, IntentResult
)
from src.services.conversation.analytics import ConversationAnalytics
from src.services.ai.orchestrator import AIOrchestrator

logger = get_logger(__name__)


@dataclass
class ConversationResponse:
    """Response from conversation processing."""
    message_id: str
    content: str
    sender_type: str = "ai_agent"
    content_type: str = "text"
    metadata: Dict[str, Any] = None
    emotion_adaptation: Optional[ToneAdaptation] = None
    intent_result: Optional[IntentResult] = None
    processing_metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.processing_metrics is None:
            self.processing_metrics = {}


@dataclass
class ConversationConfig:
    """Configuration for conversation manager."""
    # Processing configuration
    enable_emotion_adaptation: bool = True
    enable_intent_handling: bool = True
    enable_analytics: bool = True
    enable_typing_indicators: bool = True
    
    # Performance configuration
    max_processing_time_ms: int = 30000  # 30 seconds
    enable_parallel_processing: bool = True
    cache_responses: bool = True
    
    # Quality configuration
    confidence_threshold: float = 0.7
    emotion_intensity_threshold: float = 0.6
    escalation_confidence_threshold: float = 0.5
    
    # Context configuration
    max_context_history: int = 50
    max_emotion_history: int = 20
    context_timeout_minutes: int = 30


class ConversationManager:
    """Central orchestrator for conversation management."""
    
    def __init__(self, ai_orchestrator: AIOrchestrator, config: Optional[ConversationConfig] = None):
        self.ai_orchestrator = ai_orchestrator
        self.config = config or ConversationConfig()
        self.state_machine = ConversationStateMachine()
        self.context_manager = ContextManager()
        self.message_processor = MessageProcessor(ai_orchestrator)
        self.emotion_handler = EmotionResponseHandler()
        self.intent_handler = IntentHandler()
        self.analytics = ConversationAnalytics()
        self.logger = get_logger(__name__)
        
        # Initialize processing configuration
        self._initialize_processing_config()
    
    def _initialize_processing_config(self) -> None:
        """Initialize message processing configuration."""
        processing_config = ProcessingConfig(
            enable_language_detection=True,
            enable_intent_classification=True,
            enable_sentiment_analysis=True,
            enable_emotion_detection=True,
            enable_entity_extraction=True,
            enable_translation=False,
            enable_knowledge_retrieval=True,
            enable_response_generation=True,
            confidence_threshold=self.config.confidence_threshold,
            max_processing_time_ms=self.config.max_processing_time_ms,
            fallback_on_error=True,
            parallel_processing=self.config.enable_parallel_processing
        )
        self.message_processor.config = processing_config
    
    async def create_conversation(self, organization_id: UUID, user_id: Optional[UUID] = None,
                                channel: str = "web_chat", metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a new conversation."""
        conversation_id = str(uuid4())
        
        try:
            # Initialize conversation tracking
            self.analytics.start_conversation_tracking(
                conversation_id=conversation_id,
                organization_id=str(organization_id),
                user_id=str(user_id) if user_id else "anonymous",
                channel=channel
            )
            
            # Initialize context
            context = self.context_manager.get_or_create_context(conversation_id, organization_id)
            context.initialize_for_conversation(conversation_id, user_id, organization_id, channel)
            
            # Record initial state in context
            context.record_state_change(
                new_state=ConversationStatus.INITIALIZED.value,
                reason="conversation_created"
            )
            
            self.logger.info(f"Created new conversation: {conversation_id} for org {organization_id} user {user_id} on {channel}")
            
            return conversation_id
            
        except Exception as e:
            self.logger.error(f"Failed to create conversation for org {organization_id} user {user_id}: {str(e)}")
            raise ConversationError(f"Failed to create conversation: {str(e)}") from e
    
    async def process_user_message(self, conversation_id: str, message_content: str,
                                 user_id: Optional[UUID] = None, metadata: Optional[Dict[str, Any]] = None) -> ConversationResponse:
        """Process a user message and generate response."""
        start_time = time.time()
        
        try:
            # Validate conversation exists
            context = self.context_manager.get_context(conversation_id)
            if not context:
                raise ConversationError(f"Conversation not found: {conversation_id}")
            
            # Validate state
            if not self.state_machine.can_receive_messages(
                ConversationStatus(context.session_context.current_state)
            ):
                raise ConversationError("Conversation is not in a state to receive messages")
            
            # Transition to processing state
            await self._transition_state(conversation_id, ConversationStatus.PROCESSING, "user_message_received")
            
            # Record message in analytics
            message_id = str(uuid4())
            self.analytics.record_message_processed(
                conversation_id=conversation_id,
                message_id=message_id,
                sender_type="user",
                content_length=len(message_content),
                processing_time_ms=0,  # Will be updated after processing
                metrics={
                    "content": message_content[:100]  # Truncate for logging
                }
            )
            
            # Process message through AI pipeline
            processing_result = await self.message_processor.process_message(
                message_content=message_content,
                context=context,
                conversation_id=conversation_id,
                user_id=user_id
            )
            
            # Apply emotion-aware response adaptation
            emotion_adaptation = None
            if self.config.enable_emotion_adaptation and processing_result.emotion:
                emotion_adaptation = self.emotion_handler.adapt_response_tone(
                    response_text=processing_result.content,
                    emotion=processing_result.emotion,
                    intensity=processing_result.emotion_intensity,
                    confidence=processing_result.emotion_confidence,
                    context=context
                )
                processing_result.content = emotion_adaptation.adapted_text
            
            # Handle intent-specific processing
            intent_result = None
            if self.config.enable_intent_handling and processing_result.intent:
                intent_context = IntentContext(
                    intent=processing_result.intent,
                    confidence=processing_result.intent_confidence,
                    parameters=processing_result.intent_parameters,
                    original_message=message_content,
                    conversation_id=UUID(conversation_id),
                    user_id=user_id,
                    organization_id=context.user_context.organization_id,
                    channel=context.session_context.channel,
                    context_data=context.get_context_summary(),
                    previous_intents=[record["intent"] for record in context.ai_context.intent_history[-5:]]
                )
                
                intent_result = await self.intent_handler.process_intent(
                    intent_context=intent_context,
                    conversation_context=context
                )
                
                # Update response if intent handler provided a better one
                if intent_result.success and intent_result.response_text:
                    processing_result.content = intent_result.response_text
            
            # Check for escalation needs
            requires_escalation = self._should_escalate(processing_result, emotion_adaptation, intent_result)
            
            # Transition to appropriate next state
            next_state = await self._determine_next_state(
                conversation_id, processing_result, emotion_adaptation, intent_result, requires_escalation
            )
            
            await self._transition_state(conversation_id, next_state, "processing_complete")
            
            # Create response
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            response = ConversationResponse(
                message_id=message_id,
                content=processing_result.content,
                sender_type="ai_agent",
                content_type="text",
                metadata={
                    "intent": processing_result.intent,
                    "intent_confidence": processing_result.intent_confidence,
                    "sentiment": processing_result.sentiment,
                    "sentiment_score": processing_result.sentiment_score,
                    "emotion": processing_result.emotion,
                    "emotion_intensity": processing_result.emotion_intensity,
                    "language": processing_result.language,
                    "model_used": processing_result.model_used,
                    "requires_escalation": requires_escalation
                },
                emotion_adaptation=emotion_adaptation,
                intent_result=intent_result,
                processing_metrics={
                    "processing_time_ms": processing_time_ms,
                    "confidence": processing_result.confidence,
                    "token_usage": processing_result.token_usage,
                    "cache_hit": processing_result.metadata.get("cache_hit", False)
                }
            )
            
            # Update analytics with final processing metrics
            self.analytics.record_message_processed(
                conversation_id=conversation_id,
                message_id=message_id,
                sender_type="ai_agent",
                content_length=len(response.content),
                processing_time_ms=processing_time_ms,
                metrics={
                    "intent": processing_result.intent,
                    "intent_confidence": processing_result.intent_confidence,
                    "sentiment": processing_result.sentiment,
                    "sentiment_score": processing_result.sentiment_score,
                    "sentiment_confidence": processing_result.sentiment_confidence,
                    "emotion": processing_result.emotion,
                    "emotion_intensity": processing_result.emotion_intensity,
                    "emotion_confidence": processing_result.emotion_confidence,
                    "model_used": processing_result.model_used,
                    "confidence": processing_result.confidence,
                    "cache_hit": processing_result.metadata.get("cache_hit", False),
                    "fallback_triggered": processing_result.metadata.get("fallback_triggered", False)
                }
            )
            
            self.logger.info(f"Processed user message successfully: {conversation_id} msg={message_id} time={processing_time_ms}ms intent={processing_result.intent} confidence={processing_result.confidence} state={next_state.value}")
            
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to process user message for conversation {conversation_id}: {str(e)} ({type(e).__name__})")
            
            # Attempt to transition to error state
            try:
                await self._transition_state(conversation_id, ConversationStatus.ESCALATED, "processing_error")
            except:
                pass
            
            raise ConversationError(f"Failed to process message: {str(e)}") from e
    
    async def escalate_conversation(self, conversation_id: str, reason: str,
                                  escalated_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Escalate conversation to human agent."""
        try:
            context = self.context_manager.get_context(conversation_id)
            if not context:
                raise ConversationError(f"Conversation not found: {conversation_id}")
            
            # Validate transition
            if not self.state_machine.can_transition(
                ConversationStatus(context.session_context.current_state),
                ConversationStatus.ESCALATED
            ):
                raise ConversationError("Cannot escalate from current state")
            
            # Record escalation in context
            context.business_context.escalation_triggered = True
            context.business_context.escalation_reason = reason
            context.business_context.escalation_level += 1
            
            # Record in analytics
            self.analytics.record_sla_breach(
                conversation_id=conversation_id,
                breach_type="escalation",
                breach_duration_seconds=0.0
            )
            
            # Transition state
            await self._transition_state(
                conversation_id,
                ConversationStatus.ESCALATED,
                reason,
                {
                    "escalation_reason": reason,
                    "escalated_by": "system",  # System is escalating based on user request
                    "escalated_to": escalated_to,
                    **(metadata or {})
                }
            )
            
            self.logger.info(f"Escalated conversation {conversation_id}: {reason} to {escalated_to}")
            
        except Exception as e:
            self.logger.error(f"Failed to escalate conversation {conversation_id}: {reason} - {str(e)}")
            raise ConversationError(f"Failed to escalate conversation: {str(e)}") from e
    
    async def close_conversation(self, conversation_id: str, resolution_type: str,
                               satisfaction_score: Optional[float] = None,
                               nps_score: Optional[int] = None,
                               resolution_summary: Optional[str] = None) -> None:
        """Close a conversation."""
        try:
            context = self.context_manager.get_context(conversation_id)
            if not context:
                raise ConversationError(f"Conversation not found: {conversation_id}")
            
            # Validate transition to resolved
            current_state = ConversationStatus(context.session_context.current_state)
            if not self.state_machine.can_transition(current_state, ConversationStatus.RESOLVED):
                raise ConversationError(f"Cannot transition from {current_state.value} to resolved")
            
            # Record resolution
            context.business_context.record_rule_application(
                rule_id="conversation_resolution",
                rule_name="Close Conversation",
                result=resolution_type
            )
            
            # Record in analytics
            self.analytics.record_resolution(
                conversation_id=conversation_id,
                resolved=True,
                resolution_type=resolution_type,
                satisfaction_score=satisfaction_score,
                nps_score=nps_score
            )
            
            # Transition state
            await self._transition_state(
                conversation_id,
                ConversationStatus.RESOLVED,
                "conversation_closed",
                {
                    "resolution_type": resolution_type,
                    "resolved_by": "system",  # System is resolving the conversation
                    "resolution_summary": resolution_summary
                }
            )
            
            # Finalize analytics
            final_metrics = self.analytics.finalize_conversation(conversation_id)
            
            # Clean up context
            self.context_manager.remove_context(conversation_id)
            
            self.logger.info(f"Closed conversation {conversation_id}: {resolution_type} satisfaction={satisfaction_score} duration={final_metrics.duration_seconds if final_metrics else 'unknown'}s")
            
        except Exception as e:
            self.logger.error(f"Failed to close conversation {conversation_id}: {str(e)}")
            raise ConversationError(f"Failed to close conversation: {str(e)}") from e
    
    async def get_conversation_status(self, conversation_id: str) -> Dict[str, Any]:
        """Get current conversation status."""
        context = self.context_manager.get_context(conversation_id)
        if not context:
            raise ConversationError(f"Conversation not found: {conversation_id}")
        
        current_metrics = self.analytics.get_active_conversation_metrics(conversation_id)
        
        return {
            "conversation_id": conversation_id,
            "status": context.session_context.current_state,
            "organization_id": str(context.user_context.organization_id) if context.user_context.organization_id else None,
            "user_id": str(context.user_context.user_id) if context.user_context.user_id else None,
            "channel": context.session_context.channel,
            "start_time": context.session_context.start_time.isoformat() if context.session_context.start_time else None,
            "last_activity_time": context.session_context.last_activity_time.isoformat() if context.session_context.last_activity_time else None,
            "message_count": context.session_context.message_count,
            "context_summary": context.get_context_summary(),
            "metrics": current_metrics,
            "can_receive_messages": self.state_machine.can_receive_messages(
                ConversationStatus(context.session_context.current_state)
            )
        }
    
    async def _transition_state(self, conversation_id: str, new_state: ConversationStatus,
                              reason: str = None, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Transition conversation to new state."""
        context = self.context_manager.get_context(conversation_id)
        if not context:
            raise ConversationError(f"Context not found for conversation: {conversation_id}")
        
        current_state = ConversationStatus(context.session_context.current_state)
        
        # Validate transition
        if not self.state_machine.validate_transition(current_state, new_state, metadata):
            raise StateTransitionError(current_state.value, new_state.value)
        
        # Record state change in context
        context.record_state_change(new_state.value, reason, metadata)
        
        # Record in analytics
        self.analytics.record_state_transition(
            conversation_id=conversation_id,
            from_state=current_state.value,
            to_state=new_state.value,
            reason=reason
        )
        
        self.logger.info(f"State transition completed: {conversation_id} from {current_state.value} to {new_state.value} reason={reason}")
    
    async def _determine_next_state(self, conversation_id: str, processing_result: ProcessingResult,
                                  emotion_adaptation: Optional[ToneAdaptation],
                                  intent_result: Optional[IntentResult],
                                  requires_escalation: bool) -> ConversationStatus:
        """Determine the next conversation state based on processing results."""
        context = self.context_manager.get_context(conversation_id)
        current_state = ConversationStatus(context.session_context.current_state)
        
        # Handle escalation
        if requires_escalation:
            return ConversationStatus.ESCALATED
        
        # Handle intent-specific state transitions
        if intent_result and intent_result.requires_escalation:
            return ConversationStatus.ESCALATED
        
        # Handle emotion-based transitions
        if emotion_adaptation and emotion_adaptation.escalation_recommended:
            return ConversationStatus.ESCALATED
        
        # Handle low confidence
        if processing_result.confidence < self.config.confidence_threshold:
            return ConversationStatus.WAITING_FOR_USER
        
        # Default transitions based on current state
        if current_state == ConversationStatus.PROCESSING:
            # Check if we need more information
            if not processing_result.intent or processing_result.intent_confidence < 0.8:
                return ConversationStatus.WAITING_FOR_USER
            
            # Check if response was generated successfully
            if processing_result.content and processing_result.confidence >= 0.7:
                return ConversationStatus.ACTIVE
            else:
                return ConversationStatus.WAITING_FOR_USER
        
        # Default to active state
        return ConversationStatus.ACTIVE
    
    def _should_escalate(self, processing_result: ProcessingResult,
                        emotion_adaptation: Optional[ToneAdaptation],
                        intent_result: Optional[IntentResult]) -> bool:
        """Determine if conversation should be escalated."""
        # Check processing result
        if processing_result.requires_escalation:
            return True
        
        # Check emotion adaptation
        if emotion_adaptation and emotion_adaptation.escalation_recommended:
            return True
        
        # Check intent result
        if intent_result and intent_result.requires_escalation:
            return True
        
        return False
    
    def get_conversation_summary(self, conversation_id: str) -> Dict[str, Any]:
        """Get comprehensive conversation summary."""
        context = self.context_manager.get_context(conversation_id)
        if not context:
            raise ConversationError(f"Conversation not found: {conversation_id}")
        
        return {
            "conversation_id": conversation_id,
            "status": context.session_context.current_state,
            "duration_seconds": context.session_context.get_session_duration(),
            "message_count": context.session_context.message_count,
            "user_context": context.user_context.__dict__,
            "session_context": context.session_context.__dict__,
            "ai_context": context.ai_context.__dict__,
            "business_context": context.business_context.__dict__,
            "analytics_summary": self.analytics.get_active_conversation_metrics(conversation_id)
        }
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system-wide conversation metrics."""
        return {
            "active_conversations": len(self.context_manager.contexts),
            "analytics_summary": self.analytics.get_metrics_summary(),
            "ai_performance": self.analytics.get_ai_performance_summary(),
            "config": {
                "enable_emotion_adaptation": self.config.enable_emotion_adaptation,
                "enable_intent_handling": self.config.enable_intent_handling,
                "confidence_threshold": self.config.confidence_threshold,
                "max_processing_time_ms": self.config.max_processing_time_ms
            }
        }
    
    async def cleanup_expired_conversations(self, max_age_hours: int = 24) -> int:
        """Clean up expired conversations."""
        return self.context_manager.cleanup_expired_contexts(max_age_hours)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on conversation system."""
        try:
            # Check AI orchestrator
            ai_health = await self.ai_orchestrator.health_check()
            
            # Check analytics
            analytics_metrics = self.analytics.get_metrics_summary()
            
            return {
                "status": "healthy",
                "ai_orchestrator": ai_health,
                "active_conversations": len(self.context_manager.contexts),
                "analytics": analytics_metrics,
                "timestamp": time.time()
            }
            
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }