"""Fallback mechanisms and error handling for AI services."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from src.core.exceptions import AIServiceError
from src.core.logging import get_logger
from src.services.ai.models import AIModel, ModelCapability

logger = get_logger(__name__)


class FallbackStrategy(str, Enum):
    """Fallback strategies for AI service failures."""
    SEQUENTIAL = "sequential"  # Try models one by one
    PARALLEL = "parallel"      # Try multiple models simultaneously
    HYBRID = "hybrid"          # Try primary sequentially, then parallel fallbacks


class ErrorType(str, Enum):
    """Types of errors that can trigger fallbacks."""
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    QUOTA_EXCEEDED = "quota_exceeded"
    MODEL_UNAVAILABLE = "model_unavailable"
    LOW_CONFIDENCE = "low_confidence"
    INVALID_RESPONSE = "invalid_response"
    NETWORK_ERROR = "network_error"
    AUTHENTICATION_ERROR = "authentication_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class FallbackConfig:
    """Configuration for fallback behavior."""
    strategy: FallbackStrategy = FallbackStrategy.SEQUENTIAL
    max_attempts: int = 3
    timeout_per_attempt: int = 30
    confidence_threshold: float = 0.7
    parallel_timeout: int = 60
    retry_delay: float = 1.0
    exponential_backoff: bool = True
    max_backoff_delay: float = 30.0
    enable_circuit_breaker: bool = True
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 300


@dataclass
class FallbackAttempt:
    """Record of a fallback attempt."""
    model_name: str
    attempt_number: int
    start_time: float
    end_time: Optional[float] = None
    success: bool = False
    error_type: Optional[ErrorType] = None
    error_message: Optional[str] = None
    confidence: float = 0.0
    response_time: float = 0.0


@dataclass
class FallbackResult:
    """Result of fallback execution."""
    success: bool
    final_model: Optional[str] = None
    attempts: List[FallbackAttempt] = None
    total_time: float = 0.0
    error: Optional[str] = None
    response: Optional[Any] = None
    
    def __post_init__(self):
        if self.attempts is None:
            self.attempts = []


class CircuitBreaker:
    """Circuit breaker pattern for AI service protection."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 300,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    def can_execute(self) -> bool:
        """Check if the circuit breaker allows execution."""
        if self.state == "closed":
            return True
        elif self.state == "open":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "half-open"
                return True
            return False
        else:  # half-open
            return True
    
    def record_success(self) -> None:
        """Record a successful execution."""
        self.failure_count = 0
        self.state = "closed"
    
    def record_failure(self) -> None:
        """Record a failed execution."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")


class FallbackManager:
    """Manages fallback strategies and error handling for AI services."""
    
    def __init__(self, config: FallbackConfig):
        self.config = config
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.fallback_stats: Dict[str, Dict[str, Any]] = {}
    
    def get_circuit_breaker(self, model_name: str) -> CircuitBreaker:
        """Get or create a circuit breaker for a model."""
        if model_name not in self.circuit_breakers:
            self.circuit_breakers[model_name] = CircuitBreaker(
                failure_threshold=self.config.circuit_breaker_threshold,
                timeout=self.config.circuit_breaker_timeout
            )
        return self.circuit_breakers[model_name]
    
    async def execute_with_fallback(
        self,
        primary_model: AIModel,
        fallback_models: List[AIModel],
        capability: ModelCapability,
        request_func: callable,
        *args,
        **kwargs
    ) -> FallbackResult:
        """Execute a request with fallback support."""
        start_time = time.time()
        attempts = []
        all_models = [primary_model] + fallback_models
        
        if self.config.strategy == FallbackStrategy.SEQUENTIAL:
            return await self._execute_sequential(
                all_models, capability, request_func, attempts, start_time, *args, **kwargs
            )
        elif self.config.strategy == FallbackStrategy.PARALLEL:
            return await self._execute_parallel(
                all_models, capability, request_func, attempts, start_time, *args, **kwargs
            )
        else:  # HYBRID
            return await self._execute_hybrid(
                primary_model, fallback_models, capability, request_func, attempts, start_time, *args, **kwargs
            )
    
    async def _execute_sequential(
        self,
        models: List[AIModel],
        capability: ModelCapability,
        request_func: callable,
        attempts: List[FallbackAttempt],
        start_time: float,
        *args,
        **kwargs
    ) -> FallbackResult:
        """Execute models sequentially until one succeeds."""
        for i, model in enumerate(models):
            attempt = FallbackAttempt(
                model_name=model.name,
                attempt_number=i + 1,
                start_time=time.time()
            )
            
            # Check circuit breaker
            circuit_breaker = self.get_circuit_breaker(model.name)
            if not circuit_breaker.can_execute():
                attempt.error_type = ErrorType.MODEL_UNAVAILABLE
                attempt.error_message = "Circuit breaker is open"
                attempt.end_time = time.time()
                attempts.append(attempt)
                continue
            
            try:
                # Execute request with timeout
                response = await asyncio.wait_for(
                    request_func(model, *args, **kwargs),
                    timeout=self.config.timeout_per_attempt
                )
                
                attempt.end_time = time.time()
                attempt.response_time = attempt.end_time - attempt.start_time
                
                # Check confidence if applicable
                if hasattr(response, 'confidence'):
                    attempt.confidence = response.confidence
                    if response.confidence < self.config.confidence_threshold:
                        attempt.error_type = ErrorType.LOW_CONFIDENCE
                        attempt.error_message = f"Low confidence: {response.confidence:.2f}"
                        circuit_breaker.record_failure()
                        attempts.append(attempt)
                        continue
                
                # Success
                attempt.success = True
                circuit_breaker.record_success()
                attempts.append(attempt)
                
                self._update_stats(model.name, True, attempt.response_time)
                
                return FallbackResult(
                    success=True,
                    final_model=model.name,
                    attempts=attempts,
                    total_time=time.time() - start_time,
                    response=response
                )
                
            except asyncio.TimeoutError:
                attempt.error_type = ErrorType.TIMEOUT
                attempt.error_message = "Request timeout"
                circuit_breaker.record_failure()
            except Exception as e:
                attempt.error_type = self._classify_error(e)
                attempt.error_message = str(e)
                circuit_breaker.record_failure()
            
            attempt.end_time = time.time()
            attempt.response_time = attempt.end_time - attempt.start_time
            attempts.append(attempt)
            
            self._update_stats(model.name, False, attempt.response_time)
            
            # Apply retry delay with exponential backoff
            if i < len(models) - 1:  # Don't delay after last attempt
                delay = self._calculate_delay(i)
                if delay > 0:
                    await asyncio.sleep(delay)
        
        # All attempts failed
        return FallbackResult(
            success=False,
            attempts=attempts,
            total_time=time.time() - start_time,
            error="All fallback attempts failed"
        )
    
    async def _execute_parallel(
        self,
        models: List[AIModel],
        capability: ModelCapability,
        request_func: callable,
        attempts: List[FallbackAttempt],
        start_time: float,
        *args,
        **kwargs
    ) -> FallbackResult:
        """Execute models in parallel and return the best result."""
        tasks = []
        
        for model in models:
            # Check circuit breaker
            circuit_breaker = self.get_circuit_breaker(model.name)
            if not circuit_breaker.can_execute():
                continue
            
            task = asyncio.create_task(
                self._execute_single_model(model, request_func, *args, **kwargs)
            )
            tasks.append((model, task))
        
        if not tasks:
            return FallbackResult(
                success=False,
                attempts=attempts,
                total_time=time.time() - start_time,
                error="No models available (all circuit breakers open)"
            )
        
        # Wait for first successful result or all to complete
        try:
            done, pending = await asyncio.wait(
                [task for _, task in tasks],
                timeout=self.config.parallel_timeout,
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel pending tasks
            for task in pending:
                task.cancel()
            
            # Check results
            best_attempt = None
            best_confidence = 0.0
            
            for model, task in tasks:
                if task in done:
                    try:
                        result = await task
                        if result.success and result.confidence > best_confidence:
                            best_attempt = result
                            best_confidence = result.confidence
                    except Exception:
                        pass
            
            if best_attempt and best_confidence >= self.config.confidence_threshold:
                attempts.append(best_attempt)
                return FallbackResult(
                    success=True,
                    final_model=best_attempt.model_name,
                    attempts=attempts,
                    total_time=time.time() - start_time,
                    response=best_attempt.response
                )
            
        except asyncio.TimeoutError:
            pass
        
        return FallbackResult(
            success=False,
            attempts=attempts,
            total_time=time.time() - start_time,
            error="Parallel execution timeout or no successful results"
        )
    
    async def _execute_hybrid(
        self,
        primary_model: AIModel,
        fallback_models: List[AIModel],
        capability: ModelCapability,
        request_func: callable,
        attempts: List[FallbackAttempt],
        start_time: float,
        *args,
        **kwargs
    ) -> FallbackResult:
        """Execute primary model sequentially, then fallbacks in parallel."""
        # Try primary model first
        primary_result = await self._execute_sequential(
            [primary_model], capability, request_func, attempts, start_time, *args, **kwargs
        )
        
        if primary_result.success:
            return primary_result
        
        # If primary failed, try fallbacks in parallel
        if fallback_models:
            fallback_result = await self._execute_parallel(
                fallback_models, capability, request_func, attempts, start_time, *args, **kwargs
            )
            return fallback_result
        
        return primary_result
    
    async def _execute_single_model(
        self,
        model: AIModel,
        request_func: callable,
        *args,
        **kwargs
    ) -> FallbackAttempt:
        """Execute a single model and return attempt result."""
        attempt = FallbackAttempt(
            model_name=model.name,
            attempt_number=1,
            start_time=time.time()
        )
        
        try:
            response = await asyncio.wait_for(
                request_func(model, *args, **kwargs),
                timeout=self.config.timeout_per_attempt
            )
            
            attempt.end_time = time.time()
            attempt.response_time = attempt.end_time - attempt.start_time
            attempt.success = True
            
            if hasattr(response, 'confidence'):
                attempt.confidence = response.confidence
            
            attempt.response = response
            
        except Exception as e:
            attempt.end_time = time.time()
            attempt.response_time = attempt.end_time - attempt.start_time
            attempt.error_type = self._classify_error(e)
            attempt.error_message = str(e)
        
        return attempt
    
    def _classify_error(self, error: Exception) -> ErrorType:
        """Classify an error type for fallback decisions."""
        error_str = str(error).lower()
        
        if "timeout" in error_str:
            return ErrorType.TIMEOUT
        elif "rate limit" in error_str or "too many requests" in error_str:
            return ErrorType.RATE_LIMIT
        elif "quota" in error_str or "limit exceeded" in error_str:
            return ErrorType.QUOTA_EXCEEDED
        elif "unauthorized" in error_str or "authentication" in error_str:
            return ErrorType.AUTHENTICATION_ERROR
        elif "network" in error_str or "connection" in error_str:
            return ErrorType.NETWORK_ERROR
        else:
            return ErrorType.UNKNOWN_ERROR
    
    def _calculate_delay(self, attempt_number: int) -> float:
        """Calculate retry delay with exponential backoff."""
        if not self.config.exponential_backoff:
            return self.config.retry_delay
        
        delay = self.config.retry_delay * (2 ** attempt_number)
        return min(delay, self.config.max_backoff_delay)
    
    def _update_stats(self, model_name: str, success: bool, response_time: float) -> None:
        """Update fallback statistics."""
        if model_name not in self.fallback_stats:
            self.fallback_stats[model_name] = {
                "total_attempts": 0,
                "successful_attempts": 0,
                "failed_attempts": 0,
                "avg_response_time": 0.0,
                "success_rate": 0.0,
            }
        
        stats = self.fallback_stats[model_name]
        stats["total_attempts"] += 1
        
        if success:
            stats["successful_attempts"] += 1
        else:
            stats["failed_attempts"] += 1
        
        # Update averages
        stats["avg_response_time"] = (
            (stats["avg_response_time"] * (stats["total_attempts"] - 1) + response_time) 
            / stats["total_attempts"]
        )
        stats["success_rate"] = stats["successful_attempts"] / stats["total_attempts"]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get fallback statistics."""
        return {
            "circuit_breakers": {
                name: {
                    "state": cb.state,
                    "failure_count": cb.failure_count,
                    "last_failure_time": cb.last_failure_time,
                }
                for name, cb in self.circuit_breakers.items()
            },
            "model_stats": self.fallback_stats.copy(),
        }
    
    def reset_stats(self) -> None:
        """Reset fallback statistics."""
        self.fallback_stats.clear()
        for cb in self.circuit_breakers.values():
            cb.failure_count = 0
            cb.state = "closed"
        logger.info("Fallback manager statistics reset")
