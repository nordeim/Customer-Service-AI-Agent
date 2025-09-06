"""
Base integration classes and utilities.

Provides foundational functionality for all integrations including:
- OAuth 2.0 flow management
- Rate limiting implementation
- Retry logic with exponential backoff
- Circuit breaker pattern
- Health monitoring
- Bi-directional sync foundation
"""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar, Union
from urllib.parse import urlencode, urlparse
import httpx
import jwt
from redis import Redis

from src.core.config import get_settings
from src.core.logging import get_logger
from src.core.exceptions import ExternalServiceError, RateLimitError
from . import (
    BaseIntegration,
    IntegrationException,
    IntegrationHealth,
    IntegrationStatus,
    IntegrationType,
)

logger = get_logger(__name__)
T = TypeVar("T")


class SyncDirection(Enum):
    """Data synchronization directions."""
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    BIDIRECTIONAL = "bidirectional"


class ConflictResolutionStrategy(Enum):
    """Conflict resolution strategies for sync operations."""
    LAST_WRITE_WINS = "last_write_wins"
    MERGE = "merge"
    MANUAL = "manual"
    SOURCE_WINS = "source_wins"
    TARGET_WINS = "target_wins"


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class OAuth2Config:
    """OAuth 2.0 configuration."""
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        authorization_url: str,
        token_url: str,
        redirect_uri: str,
        scope: Optional[str] = None,
        audience: Optional[str] = None,
        **kwargs: Any
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.authorization_url = authorization_url
        self.token_url = token_url
        self.redirect_uri = redirect_uri
        self.scope = scope
        self.audience = audience
        self.additional_params = kwargs


class RateLimiter:
    """Token bucket rate limiter using Redis."""
    
    def __init__(self, redis_client: Redis, key_prefix: str, max_requests: int, window_seconds: int):
        self.redis = redis_client
        self.key_prefix = key_prefix
        self.max_requests = max_requests
        self.window_seconds = window_seconds
    
    async def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed under rate limit."""
        key = f"{self.key_prefix}:{identifier}"
        current = await self.redis.incr(key)
        
        if current == 1:
            await self.redis.expire(key, self.window_seconds)
        
        return current <= self.max_requests
    
    async def get_retry_after(self, identifier: str) -> int:
        """Get retry after time in seconds."""
        key = f"{self.key_prefix}:{identifier}"
        ttl = await self.redis.ttl(key)
        return max(ttl, 0)


class RetryHandler:
    """Exponential backoff retry handler."""
    
    def __init__(
        self,
        max_attempts: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
    
    async def execute_with_retry(
        self,
        func: Callable[[], T],
        should_retry: Optional[Callable[[Exception], bool]] = None
    ) -> T:
        """Execute function with exponential backoff retry."""
        for attempt in range(1, self.max_attempts + 1):
            try:
                return await func()
            except Exception as e:
                if should_retry and not should_retry(e):
                    raise
                
                if attempt == self.max_attempts:
                    logger.error(f"Max retry attempts ({self.max_attempts}) reached")
                    raise
                
                delay = min(
                    self.base_delay * (self.exponential_base ** (attempt - 1)),
                    self.max_delay
                )
                
                logger.warning(f"Attempt {attempt} failed: {e}. Retrying in {delay}s")
                await asyncio.sleep(delay)


class CircuitBreaker:
    """Circuit breaker pattern implementation."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitBreakerState.CLOSED
    
    async def call(self, func: Callable[[], T]) -> T:
        """Call function with circuit breaker protection."""
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
            else:
                raise IntegrationException(
                    "Circuit breaker is OPEN",
                    IntegrationType.UNKNOWN
                )
        
        try:
            result = await func()
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset."""
        return (
            self.last_failure_time and
            time.time() - self.last_failure_time >= self.recovery_timeout
        )
    
    def _on_success(self) -> None:
        """Handle successful call."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count = 0
    
    def _on_failure(self) -> None:
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
        elif self.state == CircuitBreakerState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitBreakerState.OPEN


class OAuth2Client:
    """OAuth 2.0 client for integrations."""
    
    def __init__(
        self,
        config: OAuth2Config,
        http_client: Optional[httpx.AsyncClient] = None
    ):
        self.config = config
        self.http_client = http_client or httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
        )
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        self._token_lock = asyncio.Lock()
    
    async def get_authorization_url(self, state: str, additional_params: Optional[Dict[str, Any]] = None) -> str:
        """Get OAuth 2.0 authorization URL."""
        params = {
            "client_id": self.config.client_id,
            "response_type": "code",
            "redirect_uri": self.config.redirect_uri,
            "state": state
        }
        
        if self.config.scope:
            params["scope"] = self.config.scope
        
        if self.config.audience:
            params["audience"] = self.config.audience
        
        if additional_params:
            params.update(additional_params)
        
        return f"{self.config.authorization_url}?{urlencode(params)}"
    
    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "redirect_uri": self.config.redirect_uri
        }
        
        response = await self.http_client.post(self.config.token_url, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        await self._update_tokens(token_data)
        
        return token_data
    
    async def refresh_access_token(self) -> Dict[str, Any]:
        """Refresh access token using refresh token."""
        if not self.refresh_token:
            raise AuthError("No refresh token available", IntegrationType.UNKNOWN)
        
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret
        }
        
        response = await self.http_client.post(self.config.token_url, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        await self._update_tokens(token_data)
        
        return token_data
    
    async def get_valid_access_token(self) -> str:
        """Get valid access token, refreshing if necessary."""
        async with self._token_lock:
            if self._is_token_expired():
                await self.refresh_access_token()
            
            if not self.access_token:
                raise AuthError("No valid access token available", IntegrationType.UNKNOWN)
            
            return self.access_token
    
    def _is_token_expired(self) -> bool:
        """Check if access token is expired."""
        if not self.token_expires_at:
            return True
        
        # Consider token expired if it expires in less than 5 minutes
        return datetime.utcnow() >= (self.token_expires_at - timedelta(minutes=5))
    
    async def _update_tokens(self, token_data: Dict[str, Any]) -> None:
        """Update tokens from token response."""
        self.access_token = token_data.get("access_token")
        self.refresh_token = token_data.get("refresh_token")
        
        if "expires_in" in token_data:
            expires_in = int(token_data["expires_in"])
            self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    
    async def close(self) -> None:
        """Close HTTP client."""
        await self.http_client.aclose()


class SyncEngine:
    """Bi-directional synchronization engine."""
    
    def __init__(
        self,
        redis_client: Redis,
        conflict_resolution: ConflictResolutionStrategy = ConflictResolutionStrategy.LAST_WRITE_WINS
    ):
        self.redis = redis_client
        self.conflict_resolution = conflict_resolution
    
    async def sync_bidirectional(
        self,
        local_data: Dict[str, Any],
        remote_data: Dict[str, Any],
        sync_key: str
    ) -> Dict[str, Any]:
        """Perform bi-directional synchronization."""
        # Get last sync timestamps
        local_sync_ts = local_data.get("last_synced_at")
        remote_sync_ts = remote_data.get("last_synced_at")
        
        # Detect conflicts
        if self._has_conflict(local_data, remote_data, local_sync_ts, remote_sync_ts):
            resolved_data = await self._resolve_conflict(local_data, remote_data)
            return resolved_data
        
        # No conflict, merge data
        return self._merge_data(local_data, remote_data)
    
    def _has_conflict(
        self,
        local_data: Dict[str, Any],
        remote_data: Dict[str, Any],
        local_ts: Optional[str],
        remote_ts: Optional[str]
    ) -> bool:
        """Detect if there's a conflict between local and remote data."""
        if not local_ts or not remote_ts:
            return False
        
        # Simple conflict detection: both modified since last sync
        return (
            local_data.get("updated_at") > local_ts and
            remote_data.get("updated_at") > remote_ts
        )
    
    async def _resolve_conflict(
        self,
        local_data: Dict[str, Any],
        remote_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve conflict based on configured strategy."""
        if self.conflict_resolution == ConflictResolutionStrategy.LAST_WRITE_WINS:
            local_time = local_data.get("updated_at", "")
            remote_time = remote_data.get("updated_at", "")
            
            if local_time >= remote_time:
                return local_data
            else:
                return remote_data
        
        elif self.conflict_resolution == ConflictResolutionStrategy.MERGE:
            return self._merge_data(local_data, remote_data)
        
        else:
            # Manual resolution required
            raise SyncError(
                "Manual conflict resolution required",
                IntegrationType.UNKNOWN,
                {"local_data": local_data, "remote_data": remote_data}
            )
    
    def _merge_data(self, local_data: Dict[str, Any], remote_data: Dict[str, Any]) -> Dict[str, Any]:
        """Merge local and remote data."""
        merged = local_data.copy()
        merged.update(remote_data)
        merged["last_synced_at"] = datetime.utcnow().isoformat()
        return merged


class BaseIntegrationImpl(BaseIntegration):
    """Base implementation of integration with common functionality."""
    
    def __init__(
        self,
        integration_type: IntegrationType,
        config: Dict[str, Any],
        redis_client: Optional[Redis] = None
    ):
        super().__init__(integration_type, config)
        
        self.settings = get_settings()
        self.redis = redis_client
        
        # Initialize components
        self.rate_limiter = self._create_rate_limiter()
        self.retry_handler = self._create_retry_handler()
        self.circuit_breaker = self._create_circuit_breaker()
        self.sync_engine = self._create_sync_engine()
        
        # OAuth client (if configured)
        self.oauth_client: Optional[OAuth2Client] = None
        if "oauth" in config:
            self.oauth_client = OAuth2Client(OAuth2Config(**config["oauth"]))
    
    def _create_rate_limiter(self) -> Optional[RateLimiter]:
        """Create rate limiter from config."""
        rate_limit_config = self.config.get("rate_limit", {})
        if not rate_limit_config or not self.redis:
            return None
        
        return RateLimiter(
            redis_client=self.redis,
            key_prefix=f"rate_limit:{self.integration_type.value}",
            max_requests=rate_limit_config.get("max_requests", 100),
            window_seconds=rate_limit_config.get("window_seconds", 3600)
        )
    
    def _create_retry_handler(self) -> RetryHandler:
        """Create retry handler from config."""
        retry_config = self.config.get("retry", {})
        return RetryHandler(**retry_config)
    
    def _create_circuit_breaker(self) -> CircuitBreaker:
        """Create circuit breaker from config."""
        cb_config = self.config.get("circuit_breaker", {})
        return CircuitBreaker(**cb_config)
    
    def _create_sync_engine(self) -> Optional[SyncEngine]:
        """Create sync engine from config."""
        sync_config = self.config.get("sync", {})
        if not sync_config or not self.redis:
            return None
        
        conflict_strategy = ConflictResolutionStrategy(
            sync_config.get("conflict_resolution", "last_write_wins")
        )
        
        return SyncEngine(self.redis, conflict_strategy)
    
    async def execute_with_protection(self, func: Callable[[], T]) -> T:
        """Execute function with rate limiting, retry, and circuit breaker protection."""
        # Rate limiting check
        if self.rate_limiter:
            identifier = self.config.get("rate_limit_identifier", "default")
            if not await self.rate_limiter.is_allowed(identifier):
                retry_after = await self.rate_limiter.get_retry_after(identifier)
                raise RateLimitError(
                    f"Rate limit exceeded. Retry after {retry_after}s",
                    self.integration_type,
                    {"retry_after": retry_after}
                )
        
        # Execute with circuit breaker and retry
        async def protected_call() -> T:
            return await self.circuit_breaker.call(
                lambda: self.retry_handler.execute_with_retry(func)
            )
        
        return await protected_call()
    
    async def close(self) -> None:
        """Close integration and cleanup resources."""
        await super().close()
        
        if self.oauth_client:
            await self.oauth_client.close()
        
        self.logger.info(f"Closed {self.integration_type.value} integration")


# Export key components
__all__ = [
    "SyncDirection",
    "ConflictResolutionStrategy",
    "CircuitBreakerState",
    "OAuth2Config",
    "RateLimiter",
    "RetryHandler",
    "CircuitBreaker",
    "OAuth2Client",
    "SyncEngine",
    "BaseIntegrationImpl",
]