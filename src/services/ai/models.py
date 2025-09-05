"""AI/ML model definitions and configurations."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class ModelProvider(str, Enum):
    """Supported AI model providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"


class ModelType(str, Enum):
    """Types of AI models."""
    CHAT = "chat"
    EMBEDDING = "embedding"
    CLASSIFICATION = "classification"
    GENERATION = "generation"


class ModelCapability(str, Enum):
    """Model capabilities."""
    TEXT_GENERATION = "text_generation"
    EMBEDDINGS = "embeddings"
    INTENT_CLASSIFICATION = "intent_classification"
    ENTITY_EXTRACTION = "entity_extraction"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    EMOTION_DETECTION = "emotion_detection"
    LANGUAGE_DETECTION = "language_detection"
    CODE_GENERATION = "code_generation"
    SALESFORCE_ANALYSIS = "salesforce_analysis"


@dataclass
class ModelConfig:
    """Configuration for an AI model."""
    name: str
    provider: ModelProvider
    model_type: ModelType
    capabilities: List[ModelCapability]
    max_tokens: int
    cost_per_token: float = 0.0
    cost_per_1k_tokens: float = 0.0
    context_window: int = 4096
    temperature: float = 0.7
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    timeout: int = 30
    retry_attempts: int = 3
    fallback_models: List[str] = field(default_factory=list)
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class AIModel(BaseModel):
    """AI model configuration with validation."""
    name: str = Field(..., description="Model name/identifier")
    provider: ModelProvider = Field(..., description="Model provider")
    model_type: ModelType = Field(..., description="Type of model")
    capabilities: List[ModelCapability] = Field(..., description="Model capabilities")
    max_tokens: int = Field(..., gt=0, description="Maximum tokens per request")
    cost_per_token: float = Field(0.0, ge=0, description="Cost per token")
    cost_per_1k_tokens: float = Field(0.0, ge=0, description="Cost per 1K tokens")
    context_window: int = Field(4096, gt=0, description="Context window size")
    temperature: float = Field(0.7, ge=0, le=2, description="Temperature setting")
    top_p: float = Field(1.0, ge=0, le=1, description="Top-p setting")
    frequency_penalty: float = Field(0.0, ge=-2, le=2, description="Frequency penalty")
    presence_penalty: float = Field(0.0, ge=-2, le=2, description="Presence penalty")
    timeout: int = Field(30, gt=0, description="Request timeout in seconds")
    retry_attempts: int = Field(3, ge=0, description="Number of retry attempts")
    fallback_models: List[str] = Field(default_factory=list, description="Fallback model names")
    is_active: bool = Field(True, description="Whether model is active")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        use_enum_values = True


class ModelRegistry:
    """Registry for managing AI models and their configurations."""
    
    def __init__(self):
        self._models: Dict[str, AIModel] = {}
        self._capability_index: Dict[ModelCapability, List[str]] = {}
        self._provider_index: Dict[ModelProvider, List[str]] = {}
    
    def register_model(self, model: AIModel) -> None:
        """Register a model in the registry."""
        self._models[model.name] = model
        
        # Update capability index
        for capability in model.capabilities:
            if capability not in self._capability_index:
                self._capability_index[capability] = []
            if model.name not in self._capability_index[capability]:
                self._capability_index[capability].append(model.name)
        
        # Update provider index
        if model.provider not in self._provider_index:
            self._provider_index[model.provider] = []
        if model.name not in self._provider_index[model.provider]:
            self._provider_index[model.provider].append(model.name)
    
    def get_model(self, name: str) -> Optional[AIModel]:
        """Get a model by name."""
        return self._models.get(name)
    
    def get_models_by_capability(self, capability: ModelCapability) -> List[AIModel]:
        """Get all models that support a specific capability."""
        model_names = self._capability_index.get(capability, [])
        return [self._models[name] for name in model_names if self._models[name].is_active]
    
    def get_models_by_provider(self, provider: ModelProvider) -> List[AIModel]:
        """Get all models from a specific provider."""
        model_names = self._provider_index.get(provider, [])
        return [self._models[name] for name in model_names if self._models[name].is_active]
    
    def get_fallback_chain(self, primary_model: str) -> List[AIModel]:
        """Get the fallback chain for a model."""
        chain = []
        current_model = self.get_model(primary_model)
        
        while current_model:
            chain.append(current_model)
            if not current_model.fallback_models:
                break
            
            # Get first available fallback
            next_model_name = None
            for fallback_name in current_model.fallback_models:
                fallback_model = self.get_model(fallback_name)
                if fallback_model and fallback_model.is_active:
                    next_model_name = fallback_name
                    break
            
            if next_model_name:
                current_model = self.get_model(next_model_name)
            else:
                break
        
        return chain
    
    def list_models(self) -> List[AIModel]:
        """List all registered models."""
        return list(self._models.values())
    
    def list_active_models(self) -> List[AIModel]:
        """List all active models."""
        return [model for model in self._models.values() if model.is_active]


# Default model configurations
DEFAULT_MODELS = [
    AIModel(
        name="gpt-4-turbo",
        provider=ModelProvider.OPENAI,
        model_type=ModelType.CHAT,
        capabilities=[
            ModelCapability.TEXT_GENERATION,
            ModelCapability.INTENT_CLASSIFICATION,
            ModelCapability.ENTITY_EXTRACTION,
            ModelCapability.SENTIMENT_ANALYSIS,
            ModelCapability.EMOTION_DETECTION,
            ModelCapability.LANGUAGE_DETECTION,
            ModelCapability.CODE_GENERATION,
            ModelCapability.SALESFORCE_ANALYSIS,
        ],
        max_tokens=4096,
        cost_per_1k_tokens=0.03,
        context_window=128000,
        temperature=0.7,
        fallback_models=["gpt-4", "gpt-3.5-turbo"],
    ),
    AIModel(
        name="gpt-4",
        provider=ModelProvider.OPENAI,
        model_type=ModelType.CHAT,
        capabilities=[
            ModelCapability.TEXT_GENERATION,
            ModelCapability.INTENT_CLASSIFICATION,
            ModelCapability.ENTITY_EXTRACTION,
            ModelCapability.SENTIMENT_ANALYSIS,
            ModelCapability.EMOTION_DETECTION,
            ModelCapability.LANGUAGE_DETECTION,
            ModelCapability.CODE_GENERATION,
            ModelCapability.SALESFORCE_ANALYSIS,
        ],
        max_tokens=4096,
        cost_per_1k_tokens=0.06,
        context_window=8192,
        temperature=0.7,
        fallback_models=["gpt-3.5-turbo"],
    ),
    AIModel(
        name="gpt-3.5-turbo",
        provider=ModelProvider.OPENAI,
        model_type=ModelType.CHAT,
        capabilities=[
            ModelCapability.TEXT_GENERATION,
            ModelCapability.INTENT_CLASSIFICATION,
            ModelCapability.ENTITY_EXTRACTION,
            ModelCapability.SENTIMENT_ANALYSIS,
            ModelCapability.EMOTION_DETECTION,
            ModelCapability.LANGUAGE_DETECTION,
        ],
        max_tokens=4096,
        cost_per_1k_tokens=0.002,
        context_window=4096,
        temperature=0.7,
    ),
    AIModel(
        name="claude-3-sonnet",
        provider=ModelProvider.ANTHROPIC,
        model_type=ModelType.CHAT,
        capabilities=[
            ModelCapability.TEXT_GENERATION,
            ModelCapability.INTENT_CLASSIFICATION,
            ModelCapability.ENTITY_EXTRACTION,
            ModelCapability.SENTIMENT_ANALYSIS,
            ModelCapability.EMOTION_DETECTION,
            ModelCapability.LANGUAGE_DETECTION,
            ModelCapability.CODE_GENERATION,
            ModelCapability.SALESFORCE_ANALYSIS,
        ],
        max_tokens=4096,
        cost_per_1k_tokens=0.015,
        context_window=200000,
        temperature=0.7,
        fallback_models=["claude-3-haiku"],
    ),
    AIModel(
        name="claude-3-haiku",
        provider=ModelProvider.ANTHROPIC,
        model_type=ModelType.CHAT,
        capabilities=[
            ModelCapability.TEXT_GENERATION,
            ModelCapability.INTENT_CLASSIFICATION,
            ModelCapability.ENTITY_EXTRACTION,
            ModelCapability.SENTIMENT_ANALYSIS,
            ModelCapability.EMOTION_DETECTION,
            ModelCapability.LANGUAGE_DETECTION,
        ],
        max_tokens=4096,
        cost_per_1k_tokens=0.0025,
        context_window=200000,
        temperature=0.7,
    ),
    AIModel(
        name="text-embedding-3-large",
        provider=ModelProvider.OPENAI,
        model_type=ModelType.EMBEDDING,
        capabilities=[ModelCapability.EMBEDDINGS],
        max_tokens=8191,
        cost_per_1k_tokens=0.00013,
        context_window=8191,
    ),
    AIModel(
        name="text-embedding-3-small",
        provider=ModelProvider.OPENAI,
        model_type=ModelType.EMBEDDING,
        capabilities=[ModelCapability.EMBEDDINGS],
        max_tokens=8191,
        cost_per_1k_tokens=0.00002,
        context_window=8191,
        fallback_models=["text-embedding-ada-002"],
    ),
    AIModel(
        name="text-embedding-ada-002",
        provider=ModelProvider.OPENAI,
        model_type=ModelType.EMBEDDING,
        capabilities=[ModelCapability.EMBEDDINGS],
        max_tokens=8191,
        cost_per_1k_tokens=0.0001,
        context_window=8191,
    ),
]


def create_default_registry() -> ModelRegistry:
    """Create a model registry with default models."""
    registry = ModelRegistry()
    for model in DEFAULT_MODELS:
        registry.register_model(model)
    return registry
