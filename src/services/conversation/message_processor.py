"""Message processing pipeline with AI service integration."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from src.core.exceptions import ConversationError, AIServiceError
from src.core.logging import get_logger
from src.services.ai.orchestrator import AIOrchestrator, AIRequest, AIResponse
from src.services.ai.models import ModelCapability
from src.services.conversation.context import ConversationContext

logger = get_logger(__name__)


@dataclass
class ProcessingResult:
    """Result of message processing pipeline."""
    content: str
    intent: Optional[str] = None
    intent_confidence: float = 0.0
    intent_parameters: Dict[str, Any] = field(default_factory=dict)
    sentiment: Optional[str] = None
    sentiment_score: float = 0.0
    sentiment_confidence: float = 0.0
    emotion: Optional[str] = None
    emotion_intensity: float = 0.0
    emotion_confidence: float = 0.0
    entities: List[Dict[str, Any]] = field(default_factory=list)
    language: str = "en"
    translation: Optional[str] = None
    model_used: str = ""
    processing_time_ms: int = 0
    token_usage: Dict[str, int] = field(default_factory=dict)
    confidence: float = 0.0
    requires_escalation: bool = False
    escalation_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessingConfig:
    """Configuration for message processing pipeline."""
    enable_language_detection: bool = True
    enable_intent_classification: bool = True
    enable_sentiment_analysis: bool = True
    enable_emotion_detection: bool = True
    enable_entity_extraction: bool = True
    enable_translation: bool = False
    enable_knowledge_retrieval: bool = True
    enable_response_generation: bool = True
    confidence_threshold: float = 0.7
    max_processing_time_ms: int = 30000  # 30 seconds
    fallback_on_error: bool = True
    parallel_processing: bool = True


class MessageProcessor:
    """Orchestrates message processing through AI services."""
    
    def __init__(self, ai_orchestrator: AIOrchestrator, config: Optional[ProcessingConfig] = None):
        self.ai_orchestrator = ai_orchestrator
        self.config = config or ProcessingConfig()
        self.logger = get_logger(__name__)
    
    async def process_message(self, message_content: str, context: ConversationContext,
                            conversation_id: str, user_id: Optional[UUID] = None) -> ProcessingResult:
        """Process a message through the AI pipeline."""
        start_time = time.time()
        
        self.logger.info(f"Starting message processing for conversation {conversation_id}: {len(message_content)} chars"
        )
        
        try:
            # Initialize result
            result = ProcessingResult(content=message_content)
            
            # Process based on configuration
            if self.config.parallel_processing:
                result = await self._process_parallel(message_content, context, result)
            else:
                result = await self._process_sequential(message_content, context, result)
            
            # Calculate confidence score
            result.confidence = self._calculate_confidence(result)
            
            # Determine if escalation is needed
            result.requires_escalation = self._should_escalate(result, context)
            
            # Calculate processing time
            result.processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Record in context
            context.record_message_processed(
                message_content, "user",
                sentiment_result={
                    "sentiment": result.sentiment,
                    "score": result.sentiment_score,
                    "confidence": result.sentiment_confidence
                } if result.sentiment else None,
                emotion_result={
                    "emotion": result.emotion,
                    "intensity": result.emotion_intensity,
                    "confidence": result.emotion_confidence
                } if result.emotion else None,
                intent_result={
                    "intent": result.intent,
                    "confidence": result.intent_confidence,
                    "parameters": result.intent_parameters
                } if result.intent else None
            )
            
            self.logger.info(
                "Message processing completed",
                conversation_id=conversation_id,
                processing_time_ms=result.processing_time_ms,
                confidence=result.confidence,
                intent=result.intent,
                sentiment=result.sentiment,
                emotion=result.emotion
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Message processing failed for conversation {conversation_id}: {str(e)} ({type(e).__name__})")
            
            if self.config.fallback_on_error:
                return await self._create_fallback_result(message_content, context, str(e))
            else:
                raise ConversationError(f"Message processing failed: {str(e)}") from e
    
    async def _process_parallel(self, message_content: str, context: ConversationContext,
                              result: ProcessingResult) -> ProcessingResult:
        """Process message components in parallel for better performance."""
        
        # Create tasks for parallel processing
        tasks = []
        
        if self.config.enable_language_detection:
            tasks.append(self._detect_language(message_content, context))
        
        if self.config.enable_intent_classification:
            tasks.append(self._classify_intent(message_content, context))
        
        if self.config.enable_sentiment_analysis:
            tasks.append(self._analyze_sentiment(message_content, context))
        
        if self.config.enable_emotion_detection:
            tasks.append(self._detect_emotion(message_content, context))
        
        if self.config.enable_entity_extraction:
            tasks.append(self._extract_entities(message_content, context))
        
        # Execute tasks in parallel
        if tasks:
            task_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, task_result in enumerate(task_results):
                if isinstance(task_result, Exception):
                    self.logger.warning(f"Parallel processing task {i} failed: {str(task_result)}")
                    continue
                
                # Update result based on task type
                if i == 0 and self.config.enable_language_detection and isinstance(task_result, dict):
                    result.language = task_result.get("language", "en")
                    result.translation = task_result.get("translation")
                elif i == 1 and self.config.enable_intent_classification and isinstance(task_result, dict):
                    result.intent = task_result.get("intent")
                    result.intent_confidence = task_result.get("confidence", 0.0)
                    result.intent_parameters = task_result.get("parameters", {})
                elif i == 2 and self.config.enable_sentiment_analysis and isinstance(task_result, dict):
                    result.sentiment = task_result.get("sentiment")
                    result.sentiment_score = task_result.get("score", 0.0)
                    result.sentiment_confidence = task_result.get("confidence", 0.0)
                elif i == 3 and self.config.enable_emotion_detection and isinstance(task_result, dict):
                    result.emotion = task_result.get("emotion")
                    result.emotion_intensity = task_result.get("intensity", 0.0)
                    result.emotion_confidence = task_result.get("confidence", 0.0)
                elif i == 4 and self.config.enable_entity_extraction and isinstance(task_result, list):
                    result.entities = task_result
        
        # Knowledge retrieval and response generation (can be done after analysis)
        if self.config.enable_knowledge_retrieval and result.intent:
            knowledge_result = await self._retrieve_knowledge(result.intent, result.intent_parameters, context)
            result.metadata.update({"knowledge_used": knowledge_result})
        
        if self.config.enable_response_generation:
            response_result = await self._generate_response(message_content, result, context)
            result.content = response_result.get("content", message_content)
            result.model_used = response_result.get("model_used", "")
            result.token_usage.update(response_result.get("token_usage", {}))
        
        return result
    
    async def _process_sequential(self, message_content: str, context: ConversationContext,
                                result: ProcessingResult) -> ProcessingResult:
        """Process message components sequentially (fallback mode)."""
        
        # Language detection
        if self.config.enable_language_detection:
            try:
                lang_result = await self._detect_language(message_content, context)
                result.language = lang_result.get("language", "en")
                result.translation = lang_result.get("translation")
            except Exception as e:
                self.logger.warning(f"Language detection failed: {str(e)}")
        
        # Intent classification
        if self.config.enable_intent_classification:
            try:
                intent_result = await self._classify_intent(message_content, context)
                result.intent = intent_result.get("intent")
                result.intent_confidence = intent_result.get("confidence", 0.0)
                result.intent_parameters = intent_result.get("parameters", {})
            except Exception as e:
                self.logger.warning(f"Intent classification failed: {str(e)}")
        
        # Sentiment analysis
        if self.config.enable_sentiment_analysis:
            try:
                sentiment_result = await self._analyze_sentiment(message_content, context)
                result.sentiment = sentiment_result.get("sentiment")
                result.sentiment_score = sentiment_result.get("score", 0.0)
                result.sentiment_confidence = sentiment_result.get("confidence", 0.0)
            except Exception as e:
                self.logger.warning(f"Sentiment analysis failed: {str(e)}")
        
        # Emotion detection
        if self.config.enable_emotion_detection:
            try:
                emotion_result = await self._detect_emotion(message_content, context)
                result.emotion = emotion_result.get("emotion")
                result.emotion_intensity = emotion_result.get("intensity", 0.0)
                result.emotion_confidence = emotion_result.get("confidence", 0.0)
            except Exception as e:
                self.logger.warning(f"Emotion detection failed: {str(e)}")
        
        # Entity extraction
        if self.config.enable_entity_extraction:
            try:
                entities = await self._extract_entities(message_content, context)
                result.entities = entities
            except Exception as e:
                self.logger.warning(f"Entity extraction failed: {str(e)}")
        
        # Knowledge retrieval
        if self.config.enable_knowledge_retrieval and result.intent:
            try:
                knowledge_result = await self._retrieve_knowledge(result.intent, result.intent_parameters, context)
                result.metadata.update({"knowledge_used": knowledge_result})
            except Exception as e:
                self.logger.warning(f"Knowledge retrieval failed: {str(e)}")
        
        # Response generation
        if self.config.enable_response_generation:
            try:
                response_result = await self._generate_response(message_content, result, context)
                result.content = response_result.get("content", message_content)
                result.model_used = response_result.get("model_used", "")
                result.token_usage.update(response_result.get("token_usage", {}))
            except Exception as e:
                self.logger.warning(f"Response generation failed: {str(e)}")
        
        return result
    
    async def _detect_language(self, message_content: str, context: ConversationContext) -> Dict[str, Any]:
        """Detect language of the message."""
        request = AIRequest(
            capability=ModelCapability.LANGUAGE_DETECTION,
            input_data=message_content,
            context=context.get_context_summary(),
            timeout=5
        )
        
        response = await self.ai_orchestrator.process_request(request)
        
        return {
            "language": response.content.get("language", "en"),
            "confidence": response.confidence,
            "translation": response.content.get("translation") if response.content.get("language") != "en" else None
        }
    
    async def _classify_intent(self, message_content: str, context: ConversationContext) -> Dict[str, Any]:
        """Classify message intent."""
        request = AIRequest(
            capability=ModelCapability.INTENT_CLASSIFICATION,
            input_data=message_content,
            context=context.get_context_summary(),
            timeout=10
        )
        
        response = await self.ai_orchestrator.process_request(request)
        
        return {
            "intent": response.content.get("intent"),
            "confidence": response.confidence,
            "parameters": response.content.get("parameters", {})
        }
    
    async def _analyze_sentiment(self, message_content: str, context: ConversationContext) -> Dict[str, Any]:
        """Analyze message sentiment."""
        request = AIRequest(
            capability=ModelCapability.SENTIMENT_ANALYSIS,
            input_data=message_content,
            context=context.get_context_summary(),
            timeout=5
        )
        
        response = await self.ai_orchestrator.process_request(request)
        
        return {
            "sentiment": response.content.get("sentiment"),
            "score": response.content.get("score", 0.0),
            "confidence": response.confidence
        }
    
    async def _detect_emotion(self, message_content: str, context: ConversationContext) -> Dict[str, Any]:
        """Detect emotion in message."""
        request = AIRequest(
            capability=ModelCapability.EMOTION_DETECTION,
            input_data=message_content,
            context=context.get_context_summary(),
            timeout=5
        )
        
        response = await self.ai_orchestrator.process_request(request)
        
        return {
            "emotion": response.content.get("emotion"),
            "intensity": response.content.get("intensity", 0.0),
            "confidence": response.confidence
        }
    
    async def _extract_entities(self, message_content: str, context: ConversationContext) -> List[Dict[str, Any]]:
        """Extract entities from message."""
        request = AIRequest(
            capability=ModelCapability.NER,
            input_data=message_content,
            context=context.get_context_summary(),
            timeout=5
        )
        
        response = await self.ai_orchestrator.process_request(request)
        
        return response.content.get("entities", [])
    
    async def _retrieve_knowledge(self, intent: str, parameters: Dict[str, Any],
                                context: ConversationContext) -> List[Dict[str, Any]]:
        """Retrieve relevant knowledge for intent."""
        if not intent:
            return []
        
        # Build knowledge retrieval query
        query_data = {
            "intent": intent,
            "parameters": parameters,
            "context": context.get_context_summary()
        }
        
        request = AIRequest(
            capability=ModelCapability.KNOWLEDGE_RETRIEVAL,
            input_data=query_data,
            context=context.get_context_summary(),
            timeout=10
        )
        
        response = await self.ai_orchestrator.process_request(request)
        
        return response.content.get("knowledge_entries", [])
    
    async def _generate_response(self, message_content: str, processing_result: ProcessingResult,
                               context: ConversationContext) -> Dict[str, Any]:
        """Generate response based on processing results."""
        
        # Build response generation context
        response_context = {
            "original_message": message_content,
            "intent": processing_result.intent,
            "intent_confidence": processing_result.intent_confidence,
            "intent_parameters": processing_result.intent_parameters,
            "sentiment": processing_result.sentiment,
            "sentiment_score": processing_result.sentiment_score,
            "emotion": processing_result.emotion,
            "emotion_intensity": processing_result.emotion_intensity,
            "entities": processing_result.entities,
            "conversation_context": context.get_context_summary(),
            "knowledge_used": processing_result.metadata.get("knowledge_used", [])
        }
        
        request = AIRequest(
            capability=ModelCapability.CHAT_COMPLETION,
            input_data=response_context,
            context=context.get_context_summary(),
            timeout=15
        )
        
        response = await self.ai_orchestrator.process_request(request)
        
        return {
            "content": response.content,
            "model_used": response.model_used,
            "token_usage": {
                "prompt_tokens": response.token_usage.prompt_tokens,
                "completion_tokens": response.token_usage.completion_tokens,
                "total_tokens": response.token_usage.total_tokens
            }
        }
    
    def _calculate_confidence(self, result: ProcessingResult) -> float:
        """Calculate overall confidence score based on component confidences."""
        confidences = []
        
        if result.intent_confidence > 0:
            confidences.append(result.intent_confidence)
        
        if result.sentiment_confidence > 0:
            confidences.append(result.sentiment_confidence)
        
        if result.emotion_confidence > 0:
            confidences.append(result.emotion_confidence)
        
        if not confidences:
            return 0.0
        
        # Weighted average (intent gets higher weight)
        weights = []
        values = []
        
        if result.intent_confidence > 0:
            weights.append(0.5)
            values.append(result.intent_confidence)
        
        if result.sentiment_confidence > 0:
            weights.append(0.3)
            values.append(result.sentiment_confidence)
        
        if result.emotion_confidence > 0:
            weights.append(0.2)
            values.append(result.emotion_confidence)
        
        weighted_sum = sum(w * v for w, v in zip(weights, values))
        weight_sum = sum(weights)
        
        return weighted_sum / weight_sum if weight_sum > 0 else 0.0
    
    def _should_escalate(self, result: ProcessingResult, context: ConversationContext) -> bool:
        """Determine if conversation should be escalated based on processing results."""
        
        # Check confidence threshold
        if result.confidence < context.ai_context.confidence_threshold:
            result.escalation_reason = "low_confidence"
            return True
        
        # Check negative sentiment
        if result.sentiment in ["very_negative", "negative"] and result.sentiment_confidence > 0.8:
            result.escalation_reason = "sentiment_negative"
            return True
        
        # Check strong negative emotion
        if result.emotion in ["angry", "frustrated"] and result.emotion_intensity > 0.8:
            result.escalation_reason = f"emotion_{result.emotion}"
            return True
        
        # Check for specific escalation intents
        if result.intent == "escalation_request":
            result.escalation_reason = "user_requested"
            return True
        
        # Check for complex issues based on entity patterns
        if self._is_complex_issue(result.entities):
            result.escalation_reason = "complex_issue"
            return True
        
        return False
    
    def _is_complex_issue(self, entities: List[Dict[str, Any]]) -> bool:
        """Determine if entities indicate a complex issue requiring escalation."""
        # Simple heuristic: multiple technical entities or billing-related entities
        technical_entities = ["technical_term", "error_code", "api_name", "database"]
        billing_entities = ["payment_method", "invoice", "subscription", "billing_issue"]
        
        technical_count = sum(1 for entity in entities if entity.get("type") in technical_entities)
        billing_count = sum(1 for entity in entities if entity.get("type") in billing_entities)
        
        return technical_count >= 3 or billing_count >= 2
    
    async def _create_fallback_result(self, message_content: str, context: ConversationContext,
                                    error_message: str) -> ProcessingResult:
        """Create a fallback result when processing fails."""
        self.logger.warning(f"Creating fallback result due to processing error: {error_message}")
        
        return ProcessingResult(
            content="I apologize, but I'm having trouble processing your message. Could you please rephrase or provide more details?",
            sentiment="neutral",
            sentiment_score=0.0,
            sentiment_confidence=1.0,
            emotion="neutral",
            emotion_intensity=0.0,
            emotion_confidence=1.0,
            confidence=0.5,
            requires_escalation=False,
            metadata={
                "fallback": True,
                "error": error_message,
                "original_message": message_content
            }
        )