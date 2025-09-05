"""Base LLM service interface and common functionality."""

from __future__ import annotations

import asyncio
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from src.core.exceptions import AIServiceError
from src.core.logging import get_logger
from src.services.ai.models import AIModel, ModelCapability
from src.services.ai.orchestrator import AIResponse, TokenUsage

logger = get_logger(__name__)


class MessageRole(str):
    """Message roles for chat-based models."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class ChatMessage:
    """A chat message with role and content."""
    role: str
    content: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class GenerationConfig:
    """Configuration for text generation."""
    temperature: float = 0.7
    max_tokens: int = 1000
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop_sequences: List[str] = None
    stream: bool = False
    
    def __post_init__(self):
        if self.stop_sequences is None:
            self.stop_sequences = []


class BaseLLMService(ABC):
    """Base class for LLM service implementations."""
    
    def __init__(self, api_key: str, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url
        self._session = None
    
    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        model: AIModel,
        config: Optional[GenerationConfig] = None,
        **kwargs
    ) -> AIResponse:
        """Generate text from a prompt."""
        pass
    
    @abstractmethod
    async def generate_chat(
        self,
        messages: List[ChatMessage],
        model: AIModel,
        config: Optional[GenerationConfig] = None,
        **kwargs
    ) -> AIResponse:
        """Generate text from chat messages."""
        pass
    
    @abstractmethod
    async def generate_embeddings(
        self,
        text: str,
        model: AIModel,
        **kwargs
    ) -> AIResponse:
        """Generate embeddings for text."""
        pass
    
    async def classify_intent(
        self,
        text: str,
        model: AIModel,
        intents: List[str],
        **kwargs
    ) -> AIResponse:
        """Classify intent from text using structured prompting."""
        prompt = self._build_intent_classification_prompt(text, intents)
        response = await self.generate_text(prompt, model, **kwargs)
        
        # Parse structured response
        try:
            intent_data = json.loads(response.content)
            response.content = intent_data
            response.confidence = intent_data.get("confidence", 0.0)
        except (json.JSONDecodeError, KeyError):
            logger.warning("Failed to parse intent classification response")
            response.confidence = 0.0
        
        return response
    
    async def extract_entities(
        self,
        text: str,
        model: AIModel,
        entity_types: List[str],
        **kwargs
    ) -> AIResponse:
        """Extract entities from text using structured prompting."""
        prompt = self._build_entity_extraction_prompt(text, entity_types)
        response = await self.generate_text(prompt, model, **kwargs)
        
        # Parse structured response
        try:
            entity_data = json.loads(response.content)
            response.content = entity_data
            response.confidence = entity_data.get("confidence", 0.0)
        except (json.JSONDecodeError, KeyError):
            logger.warning("Failed to parse entity extraction response")
            response.confidence = 0.0
        
        return response
    
    async def analyze_sentiment(
        self,
        text: str,
        model: AIModel,
        **kwargs
    ) -> AIResponse:
        """Analyze sentiment of text using structured prompting."""
        prompt = self._build_sentiment_analysis_prompt(text)
        response = await self.generate_text(prompt, model, **kwargs)
        
        # Parse structured response
        try:
            sentiment_data = json.loads(response.content)
            response.content = sentiment_data
            response.confidence = sentiment_data.get("confidence", 0.0)
        except (json.JSONDecodeError, KeyError):
            logger.warning("Failed to parse sentiment analysis response")
            response.confidence = 0.0
        
        return response
    
    async def detect_emotion(
        self,
        text: str,
        model: AIModel,
        **kwargs
    ) -> AIResponse:
        """Detect emotion in text using structured prompting."""
        prompt = self._build_emotion_detection_prompt(text)
        response = await self.generate_text(prompt, model, **kwargs)
        
        # Parse structured response
        try:
            emotion_data = json.loads(response.content)
            response.content = emotion_data
            response.confidence = emotion_data.get("confidence", 0.0)
        except (json.JSONDecodeError, KeyError):
            logger.warning("Failed to parse emotion detection response")
            response.confidence = 0.0
        
        return response
    
    async def detect_language(
        self,
        text: str,
        model: AIModel,
        **kwargs
    ) -> AIResponse:
        """Detect language of text using structured prompting."""
        prompt = self._build_language_detection_prompt(text)
        response = await self.generate_text(prompt, model, **kwargs)
        
        # Parse structured response
        try:
            language_data = json.loads(response.content)
            response.content = language_data
            response.confidence = language_data.get("confidence", 0.0)
        except (json.JSONDecodeError, KeyError):
            logger.warning("Failed to parse language detection response")
            response.confidence = 0.0
        
        return response
    
    def _build_intent_classification_prompt(self, text: str, intents: List[str]) -> str:
        """Build prompt for intent classification."""
        intents_str = ", ".join(intents)
        return f"""Analyze the following text and classify its intent. Return a JSON response with the intent and confidence score.

Available intents: {intents_str}

Text: "{text}"

Return JSON in this format:
{{
    "intent": "most_likely_intent",
    "confidence": 0.95,
    "reasoning": "brief explanation"
}}"""
    
    def _build_entity_extraction_prompt(self, text: str, entity_types: List[str]) -> str:
        """Build prompt for entity extraction."""
        entity_types_str = ", ".join(entity_types)
        return f"""Extract entities from the following text. Return a JSON response with the entities and confidence score.

Entity types to extract: {entity_types_str}

Text: "{text}"

Return JSON in this format:
{{
    "entities": [
        {{
            "text": "entity_text",
            "type": "entity_type",
            "start": 0,
            "end": 10,
            "confidence": 0.95
        }}
    ],
    "confidence": 0.90
}}"""
    
    def _build_sentiment_analysis_prompt(self, text: str) -> str:
        """Build prompt for sentiment analysis."""
        return f"""Analyze the sentiment of the following text. Return a JSON response with sentiment and confidence score.

Text: "{text}"

Return JSON in this format:
{{
    "sentiment": "positive|negative|neutral",
    "score": 0.85,
    "confidence": 0.90,
    "reasoning": "brief explanation"
}}"""
    
    def _build_emotion_detection_prompt(self, text: str) -> str:
        """Build prompt for emotion detection."""
        return f"""Detect the primary emotion in the following text. Return a JSON response with emotion and confidence score.

Text: "{text}"

Return JSON in this format:
{{
    "emotion": "joy|sadness|anger|fear|surprise|disgust|neutral",
    "intensity": 0.75,
    "confidence": 0.85,
    "reasoning": "brief explanation"
}}"""
    
    def _build_language_detection_prompt(self, text: str) -> str:
        """Build prompt for language detection."""
        return f"""Detect the language of the following text. Return a JSON response with language code and confidence score.

Text: "{text}"

Return JSON in this format:
{{
    "language": "en|es|fr|de|it|pt|ru|zh|ja|ko|ar|hi",
    "confidence": 0.95,
    "reasoning": "brief explanation"
}}"""
    
    def _calculate_token_cost(
        self,
        model: AIModel,
        prompt_tokens: int,
        completion_tokens: int
    ) -> float:
        """Calculate cost based on token usage."""
        if model.cost_per_1k_tokens > 0:
            total_tokens = prompt_tokens + completion_tokens
            return (total_tokens / 1000) * model.cost_per_1k_tokens
        elif model.cost_per_token > 0:
            return (prompt_tokens + completion_tokens) * model.cost_per_token
        else:
            return 0.0
    
    def _create_token_usage(
        self,
        model: AIModel,
        prompt_tokens: int,
        completion_tokens: int
    ) -> TokenUsage:
        """Create token usage object with cost calculation."""
        total_tokens = prompt_tokens + completion_tokens
        cost = self._calculate_token_cost(model, prompt_tokens, completion_tokens)
        
        return TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost=cost,
            model_name=model.name
        )
    
    def _create_ai_response(
        self,
        content: Any,
        model: AIModel,
        token_usage: TokenUsage,
        confidence: float = 0.0,
        processing_time: float = 0.0,
        error: Optional[str] = None
    ) -> AIResponse:
        """Create standardized AI response."""
        return AIResponse(
            content=content,
            model_used=model.name,
            token_usage=token_usage,
            confidence=confidence,
            processing_time=processing_time,
            error=error
        )
    
    async def _make_request(
        self,
        url: str,
        headers: Dict[str, str],
        data: Dict[str, Any],
        timeout: int = 30
    ) -> Dict[str, Any]:
        """Make HTTP request with error handling."""
        import aiohttp
        
        if not self._session:
            self._session = aiohttp.ClientSession()
        
        try:
            async with self._session.post(
                url,
                headers=headers,
                json=data,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise AIServiceError(f"API request failed: {response.status} - {error_text}")
        except asyncio.TimeoutError:
            raise AIServiceError("Request timeout")
        except aiohttp.ClientError as e:
            raise AIServiceError(f"Network error: {str(e)}")
    
    async def close(self) -> None:
        """Close the service and cleanup resources."""
        if self._session:
            await self._session.close()
            self._session = None
    
    def __del__(self):
        """Ensure session is closed on destruction."""
        if self._session and not self._session.closed:
            # Note: This is not ideal for async cleanup, but provides safety
            logger.warning("LLM service destroyed without proper cleanup")
