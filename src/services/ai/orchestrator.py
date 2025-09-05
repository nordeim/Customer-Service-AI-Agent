"""AI orchestrator for managing model routing, fallback chains, and cost tracking."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from src.core.exceptions import AIServiceError
from src.core.logging import get_logger
from src.services.ai.models import AIModel, ModelCapability, ModelRegistry

logger = get_logger(__name__)


@dataclass
class TokenUsage:
    """Token usage tracking for cost calculation."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    model_name: str = ""


@dataclass
class AIRequest:
    """AI service request with context and metadata."""
    capability: ModelCapability
    input_data: Union[str, Dict[str, Any]]
    model_preference: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    timeout: Optional[int] = None
    retry_attempts: Optional[int] = None
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AIResponse:
    """AI service response with results and metadata."""
    content: Any
    model_used: str
    token_usage: TokenUsage
    confidence: float = 0.0
    processing_time: float = 0.0
    fallback_used: bool = False
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AIServiceProvider:
    """Base interface for AI service providers."""
    
    async def generate_text(
        self,
        prompt: str,
        model: AIModel,
        **kwargs
    ) -> AIResponse:
        """Generate text using the specified model."""
        raise NotImplementedError
    
    async def generate_embeddings(
        self,
        text: str,
        model: AIModel,
        **kwargs
    ) -> AIResponse:
        """Generate embeddings for the given text."""
        raise NotImplementedError
    
    async def classify_intent(
        self,
        text: str,
        model: AIModel,
        **kwargs
    ) -> AIResponse:
        """Classify intent from the given text."""
        raise NotImplementedError
    
    async def extract_entities(
        self,
        text: str,
        model: AIModel,
        **kwargs
    ) -> AIResponse:
        """Extract entities from the given text."""
        raise NotImplementedError
    
    async def analyze_sentiment(
        self,
        text: str,
        model: AIModel,
        **kwargs
    ) -> AIResponse:
        """Analyze sentiment of the given text."""
        raise NotImplementedError
    
    async def detect_emotion(
        self,
        text: str,
        model: AIModel,
        **kwargs
    ) -> AIResponse:
        """Detect emotion in the given text."""
        raise NotImplementedError
    
    async def detect_language(
        self,
        text: str,
        model: AIModel,
        **kwargs
    ) -> AIResponse:
        """Detect language of the given text."""
        raise NotImplementedError


class AIOrchestrator:
    """Orchestrates AI services with model routing, fallback chains, and cost tracking."""
    
    def __init__(
        self,
        model_registry: ModelRegistry,
        providers: Dict[str, AIServiceProvider],
        default_confidence_threshold: float = 0.7
    ):
        self.model_registry = model_registry
        self.providers = providers
        self.default_confidence_threshold = default_confidence_threshold
        self.cost_tracker: Dict[str, float] = {}
        self.usage_stats: Dict[str, Dict[str, Any]] = {}
    
    async def process_request(
        self,
        request: AIRequest,
        confidence_threshold: Optional[float] = None
    ) -> AIResponse:
        """Process an AI request with fallback chain support."""
        threshold = confidence_threshold or self.default_confidence_threshold
        start_time = time.time()
        
        # Get available models for the capability
        available_models = self.model_registry.get_models_by_capability(request.capability)
        if not available_models:
            raise AIServiceError(f"No models available for capability: {request.capability}")
        
        # Determine model chain
        if request.model_preference:
            primary_model = self.model_registry.get_model(request.model_preference)
            if not primary_model or request.capability not in primary_model.capabilities:
                logger.warning(f"Preferred model {request.model_preference} not available, using fallback")
                primary_model = available_models[0]
        else:
            primary_model = available_models[0]
        
        model_chain = self.model_registry.get_fallback_chain(primary_model.name)
        
        # Try each model in the chain
        last_error = None
        for i, model in enumerate(model_chain):
            try:
                logger.info(f"Attempting request with model: {model.name}")
                
                # Get provider for this model
                provider = self.providers.get(model.provider.value)
                if not provider:
                    logger.error(f"No provider available for {model.provider}")
                    continue
                
                # Prepare model parameters
                model_params = self._prepare_model_params(model, request)
                
                # Execute the request
                response = await self._execute_capability(
                    provider, request, model, model_params
                )
                
                # Check confidence threshold
                if response.confidence >= threshold:
                    response.processing_time = time.time() - start_time
                    response.fallback_used = i > 0
                    
                    # Track usage and cost
                    self._track_usage(response, model)
                    
                    logger.info(
                        f"Request completed successfully with {model.name} "
                        f"(confidence: {response.confidence:.2f}, "
                        f"cost: ${response.token_usage.cost:.4f})"
                    )
                    
                    return response
                else:
                    logger.warning(
                        f"Model {model.name} returned low confidence: {response.confidence:.2f} "
                        f"(threshold: {threshold})"
                    )
                    
            except Exception as e:
                last_error = e
                logger.error(f"Model {model.name} failed: {str(e)}")
                continue
        
        # All models failed or returned low confidence
        error_msg = f"All models failed for capability {request.capability}"
        if last_error:
            error_msg += f": {str(last_error)}"
        
        raise AIServiceError(error_msg)
    
    async def _execute_capability(
        self,
        provider: AIServiceProvider,
        request: AIRequest,
        model: AIModel,
        model_params: Dict[str, Any]
    ) -> AIResponse:
        """Execute the specific capability request."""
        input_text = request.input_data if isinstance(request.input_data, str) else str(request.input_data)
        
        if request.capability == ModelCapability.TEXT_GENERATION:
            return await provider.generate_text(input_text, model, **model_params)
        elif request.capability == ModelCapability.EMBEDDINGS:
            return await provider.generate_embeddings(input_text, model, **model_params)
        elif request.capability == ModelCapability.INTENT_CLASSIFICATION:
            return await provider.classify_intent(input_text, model, **model_params)
        elif request.capability == ModelCapability.ENTITY_EXTRACTION:
            return await provider.extract_entities(input_text, model, **model_params)
        elif request.capability == ModelCapability.SENTIMENT_ANALYSIS:
            return await provider.analyze_sentiment(input_text, model, **model_params)
        elif request.capability == ModelCapability.EMOTION_DETECTION:
            return await provider.detect_emotion(input_text, model, **model_params)
        elif request.capability == ModelCapability.LANGUAGE_DETECTION:
            return await provider.detect_language(input_text, model, **model_params)
        else:
            raise AIServiceError(f"Unsupported capability: {request.capability}")
    
    def _prepare_model_params(
        self,
        model: AIModel,
        request: AIRequest
    ) -> Dict[str, Any]:
        """Prepare model parameters from request and model config."""
        params = {
            "temperature": request.temperature or model.temperature,
            "max_tokens": request.max_tokens or model.max_tokens,
            "timeout": request.timeout or model.timeout,
            "retry_attempts": request.retry_attempts or model.retry_attempts,
        }
        
        # Add model-specific parameters
        if model.model_type.value == "chat":
            params.update({
                "top_p": model.top_p,
                "frequency_penalty": model.frequency_penalty,
                "presence_penalty": model.presence_penalty,
            })
        
        return params
    
    def _track_usage(self, response: AIResponse, model: AIModel) -> None:
        """Track usage statistics and costs."""
        # Track total cost
        if model.provider.value not in self.cost_tracker:
            self.cost_tracker[model.provider.value] = 0.0
        self.cost_tracker[model.provider.value] += response.token_usage.cost
        
        # Track usage stats
        if model.name not in self.usage_stats:
            self.usage_stats[model.name] = {
                "requests": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "avg_confidence": 0.0,
                "avg_processing_time": 0.0,
            }
        
        stats = self.usage_stats[model.name]
        stats["requests"] += 1
        stats["total_tokens"] += response.token_usage.total_tokens
        stats["total_cost"] += response.token_usage.cost
        
        # Update averages
        stats["avg_confidence"] = (
            (stats["avg_confidence"] * (stats["requests"] - 1) + response.confidence) 
            / stats["requests"]
        )
        stats["avg_processing_time"] = (
            (stats["avg_processing_time"] * (stats["requests"] - 1) + response.processing_time) 
            / stats["requests"]
        )
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get cost summary across all providers."""
        total_cost = sum(self.cost_tracker.values())
        return {
            "total_cost": total_cost,
            "by_provider": self.cost_tracker.copy(),
            "by_model": {name: stats["total_cost"] for name, stats in self.usage_stats.items()},
        }
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get detailed usage statistics."""
        return {
            "by_model": self.usage_stats.copy(),
            "total_requests": sum(stats["requests"] for stats in self.usage_stats.values()),
            "total_tokens": sum(stats["total_tokens"] for stats in self.usage_stats.values()),
        }
    
    def reset_stats(self) -> None:
        """Reset usage statistics and cost tracking."""
        self.cost_tracker.clear()
        self.usage_stats.clear()
        logger.info("AI orchestrator statistics reset")


class AIOrchestratorFactory:
    """Factory for creating AI orchestrators with default configurations."""
    
    @staticmethod
    def create_default_orchestrator(
        providers: Dict[str, AIServiceProvider],
        confidence_threshold: float = 0.7
    ) -> AIOrchestrator:
        """Create a default AI orchestrator with standard model registry."""
        from src.services.ai.models import create_default_registry
        
        registry = create_default_registry()
        return AIOrchestrator(registry, providers, confidence_threshold)
