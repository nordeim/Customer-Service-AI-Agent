"""OpenAI LLM service implementation."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from src.core.exceptions import AIServiceError
from src.core.logging import get_logger
from src.services.ai.models import AIModel, ModelProvider
from src.services.ai.llm.base import BaseLLMService, ChatMessage, GenerationConfig, AIResponse, TokenUsage

logger = get_logger(__name__)


class OpenAIService(BaseLLMService):
    """OpenAI LLM service implementation."""
    
    def __init__(self, api_key: str, base_url: Optional[str] = None):
        super().__init__(api_key, base_url)
        self.base_url = base_url or "https://api.openai.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
    
    async def generate_text(
        self,
        prompt: str,
        model: AIModel,
        config: Optional[GenerationConfig] = None,
        **kwargs
    ) -> AIResponse:
        """Generate text using OpenAI's completion API."""
        if model.provider != ModelProvider.OPENAI:
            raise AIServiceError(f"Model {model.name} is not an OpenAI model")
        
        config = config or GenerationConfig()
        start_time = time.time()
        
        # Prepare request data
        data = {
            "model": model.name,
            "prompt": prompt,
            "max_tokens": min(config.max_tokens, model.max_tokens),
            "temperature": config.temperature,
            "top_p": config.top_p,
            "frequency_penalty": config.frequency_penalty,
            "presence_penalty": config.presence_penalty,
            "stop": config.stop_sequences if config.stop_sequences else None,
            "stream": config.stream,
        }
        
        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}
        
        try:
            response_data = await self._make_request(
                f"{self.base_url}/completions",
                self.headers,
                data,
                timeout=model.timeout
            )
            
            # Extract response
            choices = response_data.get("choices", [])
            if not choices:
                raise AIServiceError("No response choices returned from OpenAI")
            
            content = choices[0].get("text", "").strip()
            
            # Extract token usage
            usage_data = response_data.get("usage", {})
            token_usage = self._create_token_usage(
                model,
                usage_data.get("prompt_tokens", 0),
                usage_data.get("completion_tokens", 0)
            )
            
            # Calculate confidence (OpenAI doesn't provide this directly)
            confidence = self._estimate_confidence(response_data, content)
            
            processing_time = time.time() - start_time
            
            return self._create_ai_response(
                content=content,
                model=model,
                token_usage=token_usage,
                confidence=confidence,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"OpenAI text generation failed: {str(e)}")
            raise AIServiceError(f"OpenAI text generation failed: {str(e)}")
    
    async def generate_chat(
        self,
        messages: List[ChatMessage],
        model: AIModel,
        config: Optional[GenerationConfig] = None,
        **kwargs
    ) -> AIResponse:
        """Generate text using OpenAI's chat completion API."""
        if model.provider != ModelProvider.OPENAI:
            raise AIServiceError(f"Model {model.name} is not an OpenAI model")
        
        config = config or GenerationConfig()
        start_time = time.time()
        
        # Convert messages to OpenAI format
        openai_messages = []
        for msg in messages:
            openai_messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Prepare request data
        data = {
            "model": model.name,
            "messages": openai_messages,
            "max_tokens": min(config.max_tokens, model.max_tokens),
            "temperature": config.temperature,
            "top_p": config.top_p,
            "frequency_penalty": config.frequency_penalty,
            "presence_penalty": config.presence_penalty,
            "stop": config.stop_sequences if config.stop_sequences else None,
            "stream": config.stream,
        }
        
        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}
        
        try:
            response_data = await self._make_request(
                f"{self.base_url}/chat/completions",
                self.headers,
                data,
                timeout=model.timeout
            )
            
            # Extract response
            choices = response_data.get("choices", [])
            if not choices:
                raise AIServiceError("No response choices returned from OpenAI")
            
            message = choices[0].get("message", {})
            content = message.get("content", "").strip()
            
            # Extract token usage
            usage_data = response_data.get("usage", {})
            token_usage = self._create_token_usage(
                model,
                usage_data.get("prompt_tokens", 0),
                usage_data.get("completion_tokens", 0)
            )
            
            # Calculate confidence
            confidence = self._estimate_confidence(response_data, content)
            
            processing_time = time.time() - start_time
            
            return self._create_ai_response(
                content=content,
                model=model,
                token_usage=token_usage,
                confidence=confidence,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"OpenAI chat generation failed: {str(e)}")
            raise AIServiceError(f"OpenAI chat generation failed: {str(e)}")
    
    async def generate_embeddings(
        self,
        text: str,
        model: AIModel,
        **kwargs
    ) -> AIResponse:
        """Generate embeddings using OpenAI's embeddings API."""
        if model.provider != ModelProvider.OPENAI:
            raise AIServiceError(f"Model {model.name} is not an OpenAI model")
        
        if ModelCapability.EMBEDDINGS not in model.capabilities:
            raise AIServiceError(f"Model {model.name} does not support embeddings")
        
        start_time = time.time()
        
        # Prepare request data
        data = {
            "model": model.name,
            "input": text,
            "encoding_format": "float",
        }
        
        try:
            response_data = await self._make_request(
                f"{self.base_url}/embeddings",
                self.headers,
                data,
                timeout=model.timeout
            )
            
            # Extract embeddings
            data_list = response_data.get("data", [])
            if not data_list:
                raise AIServiceError("No embeddings data returned from OpenAI")
            
            embeddings = data_list[0].get("embedding", [])
            
            # Extract token usage
            usage_data = response_data.get("usage", {})
            token_usage = self._create_token_usage(
                model,
                usage_data.get("prompt_tokens", 0),
                0  # No completion tokens for embeddings
            )
            
            processing_time = time.time() - start_time
            
            return self._create_ai_response(
                content=embeddings,
                model=model,
                token_usage=token_usage,
                confidence=1.0,  # Embeddings are deterministic
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"OpenAI embeddings generation failed: {str(e)}")
            raise AIServiceError(f"OpenAI embeddings generation failed: {str(e)}")
    
    def _estimate_confidence(self, response_data: Dict[str, Any], content: str) -> float:
        """Estimate confidence based on response characteristics."""
        # OpenAI doesn't provide confidence scores, so we estimate based on:
        # 1. Response length (longer responses might be less confident)
        # 2. Presence of uncertainty indicators
        # 3. Response structure
        
        confidence = 0.8  # Base confidence
        
        # Adjust based on content length
        if len(content) < 10:
            confidence -= 0.2  # Very short responses might be uncertain
        elif len(content) > 1000:
            confidence -= 0.1  # Very long responses might be rambling
        
        # Check for uncertainty indicators
        uncertainty_words = [
            "i think", "maybe", "perhaps", "possibly", "might", "could be",
            "not sure", "unclear", "uncertain", "i'm not certain"
        ]
        
        content_lower = content.lower()
        uncertainty_count = sum(1 for word in uncertainty_words if word in content_lower)
        
        if uncertainty_count > 0:
            confidence -= min(0.3, uncertainty_count * 0.1)
        
        # Check for structured response (JSON, lists, etc.)
        if content.startswith("{") or content.startswith("[") or ":" in content:
            confidence += 0.1  # Structured responses are often more confident
        
        return max(0.0, min(1.0, confidence))
