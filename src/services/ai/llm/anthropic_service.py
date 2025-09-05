"""Anthropic LLM service implementation."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from src.core.exceptions import AIServiceError
from src.core.logging import get_logger
from src.services.ai.models import AIModel, ModelProvider
from src.services.ai.llm.base import BaseLLMService, ChatMessage, GenerationConfig, AIResponse, TokenUsage

logger = get_logger(__name__)


class AnthropicService(BaseLLMService):
    """Anthropic LLM service implementation."""
    
    def __init__(self, api_key: str, base_url: Optional[str] = None):
        super().__init__(api_key, base_url)
        self.base_url = base_url or "https://api.anthropic.com/v1"
        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
    
    async def generate_text(
        self,
        prompt: str,
        model: AIModel,
        config: Optional[GenerationConfig] = None,
        **kwargs
    ) -> AIResponse:
        """Generate text using Anthropic's completion API."""
        if model.provider != ModelProvider.ANTHROPIC:
            raise AIServiceError(f"Model {model.name} is not an Anthropic model")
        
        config = config or GenerationConfig()
        start_time = time.time()
        
        # Anthropic uses messages format even for single prompts
        messages = [ChatMessage(role="user", content=prompt)]
        
        return await self.generate_chat(messages, model, config, **kwargs)
    
    async def generate_chat(
        self,
        messages: List[ChatMessage],
        model: AIModel,
        config: Optional[GenerationConfig] = None,
        **kwargs
    ) -> AIResponse:
        """Generate text using Anthropic's messages API."""
        if model.provider != ModelProvider.ANTHROPIC:
            raise AIServiceError(f"Model {model.name} is not an Anthropic model")
        
        config = config or GenerationConfig()
        start_time = time.time()
        
        # Convert messages to Anthropic format
        anthropic_messages = []
        system_message = None
        
        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                anthropic_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        # Prepare request data
        data = {
            "model": model.name,
            "max_tokens": min(config.max_tokens, model.max_tokens),
            "temperature": config.temperature,
            "top_p": config.top_p,
            "stop_sequences": config.stop_sequences if config.stop_sequences else None,
            "stream": config.stream,
            "messages": anthropic_messages,
        }
        
        # Add system message if present
        if system_message:
            data["system"] = system_message
        
        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}
        
        try:
            response_data = await self._make_request(
                f"{self.base_url}/messages",
                self.headers,
                data,
                timeout=model.timeout
            )
            
            # Extract response
            content_list = response_data.get("content", [])
            if not content_list:
                raise AIServiceError("No content returned from Anthropic")
            
            # Anthropic returns content as a list of blocks
            content = ""
            for block in content_list:
                if block.get("type") == "text":
                    content += block.get("text", "")
            
            content = content.strip()
            
            # Extract token usage
            usage_data = response_data.get("usage", {})
            token_usage = self._create_token_usage(
                model,
                usage_data.get("input_tokens", 0),
                usage_data.get("output_tokens", 0)
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
            logger.error(f"Anthropic chat generation failed: {str(e)}")
            raise AIServiceError(f"Anthropic chat generation failed: {str(e)}")
    
    async def generate_embeddings(
        self,
        text: str,
        model: AIModel,
        **kwargs
    ) -> AIResponse:
        """Generate embeddings using Anthropic's embeddings API."""
        if model.provider != ModelProvider.ANTHROPIC:
            raise AIServiceError(f"Model {model.name} is not an Anthropic model")
        
        if ModelCapability.EMBEDDINGS not in model.capabilities:
            raise AIServiceError(f"Model {model.name} does not support embeddings")
        
        start_time = time.time()
        
        # Prepare request data
        data = {
            "model": model.name,
            "input": text,
        }
        
        try:
            response_data = await self._make_request(
                f"{self.base_url}/embeddings",
                self.headers,
                data,
                timeout=model.timeout
            )
            
            # Extract embeddings
            embeddings = response_data.get("embedding", [])
            if not embeddings:
                raise AIServiceError("No embeddings data returned from Anthropic")
            
            # Extract token usage
            usage_data = response_data.get("usage", {})
            token_usage = self._create_token_usage(
                model,
                usage_data.get("input_tokens", 0),
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
            logger.error(f"Anthropic embeddings generation failed: {str(e)}")
            raise AIServiceError(f"Anthropic embeddings generation failed: {str(e)}")
    
    def _estimate_confidence(self, response_data: Dict[str, Any], content: str) -> float:
        """Estimate confidence based on response characteristics."""
        # Anthropic doesn't provide confidence scores, so we estimate based on:
        # 1. Response length and structure
        # 2. Presence of uncertainty indicators
        # 3. Response quality indicators
        
        confidence = 0.85  # Base confidence (Anthropic models are generally high quality)
        
        # Adjust based on content length
        if len(content) < 10:
            confidence -= 0.2  # Very short responses might be uncertain
        elif len(content) > 2000:
            confidence -= 0.05  # Very long responses might be less focused
        
        # Check for uncertainty indicators
        uncertainty_words = [
            "i think", "maybe", "perhaps", "possibly", "might", "could be",
            "not sure", "unclear", "uncertain", "i'm not certain", "i believe"
        ]
        
        content_lower = content.lower()
        uncertainty_count = sum(1 for word in uncertainty_words if word in content_lower)
        
        if uncertainty_count > 0:
            confidence -= min(0.2, uncertainty_count * 0.05)
        
        # Check for structured response (JSON, lists, etc.)
        if content.startswith("{") or content.startswith("[") or ":" in content:
            confidence += 0.05  # Structured responses are often more confident
        
        # Check for quality indicators
        quality_indicators = [
            "here's", "let me", "i'll", "based on", "according to",
            "the answer is", "the solution is", "to summarize"
        ]
        
        quality_count = sum(1 for phrase in quality_indicators if phrase in content_lower)
        if quality_count > 0:
            confidence += min(0.1, quality_count * 0.02)
        
        return max(0.0, min(1.0, confidence))
