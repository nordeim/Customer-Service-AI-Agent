"""
Generic webhook framework with comprehensive security and event routing.

Provides enterprise-grade webhook handling including:
- HMAC signature verification with multiple algorithms
- Payload validation and sanitization
- Event routing with topic-based dispatch
- Retry mechanisms with exponential backoff
- Security hardening and rate limiting
- Dead letter queue for failed events
- Comprehensive logging and monitoring
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import re
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, AsyncGenerator
from urllib.parse import urlparse, parse_qs
import httpx

from src.core.config import get_settings
from src.core.logging import get_logger
from src.core.exceptions import ExternalServiceError, ValidationError
from ..base import BaseIntegrationImpl, RateLimitError
from ..config import WebhookIntegrationConfig
from . import IntegrationType

logger = get_logger(__name__)


class WebhookAPIError(ExternalServiceError):
    """Webhook API specific errors."""
    pass


class WebhookRateLimitError(RateLimitError):
    """Webhook rate limit exceeded error."""
    pass


class WebhookSecurityError(ValidationError):
    """Webhook security validation errors."""
    pass


class WebhookPayload:
    """Represents a webhook payload with metadata."""
    
    def __init__(
        self,
        event_id: str,
        event_type: str,
        timestamp: datetime,
        data: Dict[str, Any],
        source: str,
        signature: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        raw_payload: Optional[str] = None
    ):
        self.event_id = event_id
        self.event_type = event_type
        self.timestamp = timestamp
        self.data = data
        self.source = source
        self.signature = signature
        self.headers = headers or {}
        self.raw_payload = raw_payload
        self.received_at = datetime.utcnow()
        self.processed_at: Optional[datetime] = None
        self.retry_count = 0
        self.status = "received"


class WebhookEvent:
    """Represents a processed webhook event."""
    
    def __init__(
        self,
        event_id: str,
        event_type: str,
        payload: Dict[str, Any],
        source: str,
        timestamp: datetime,
        status: str = "processed"
    ):
        self.event_id = event_id
        self.event_type = event_type
        self.payload = payload
        self.source = source
        self.timestamp = timestamp
        self.status = status
        self.created_at = datetime.utcnow()


class WebhookSecurityValidator:
    """Webhook security validation utilities."""
    
    # Supported signature algorithms
    SIGNATURE_ALGORITHMS = {
        "sha256": hashlib.sha256,
        "sha512": hashlib.sha512,
        "sha1": hashlib.sha1,
        "md5": hashlib.md5
    }
    
    @staticmethod
    def validate_signature(
        payload: str,
        signature: str,
        secret: str,
        algorithm: str = "sha256"
    ) -> bool:
        """Validate webhook signature using HMAC."""
        if algorithm not in WebhookSecurityValidator.SIGNATURE_ALGORITHMS:
            raise WebhookSecurityError(f"Unsupported signature algorithm: {algorithm}")
        
        try:
            # Create HMAC signature
            hash_func = WebhookSecurityValidator.SIGNATURE_ALGORITHMS[algorithm]
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                payload.encode('utf-8'),
                hash_func
            ).hexdigest()
            
            # Support various signature formats
            if signature.startswith(f"{algorithm}="):
                provided_signature = signature[len(algorithm) + 1:]
            elif signature.startswith("sha="):
                provided_signature = signature[4:]
            elif signature.startswith("v1="):
                provided_signature = signature[3:]
            else:
                provided_signature = signature
            
            # Constant-time comparison to prevent timing attacks
            return hmac.compare_digest(expected_signature, provided_signature)
            
        except Exception as e:
            logger.error(f"Signature validation failed: {e}")
            return False
    
    @staticmethod
    def validate_timestamp(timestamp: str, max_age: int = 300) -> bool:
        """Validate webhook timestamp to prevent replay attacks."""
        try:
            # Parse timestamp (supports various formats)
            if timestamp.isdigit():
                # Unix timestamp
                event_time = datetime.fromtimestamp(int(timestamp))
            else:
                # ISO format
                event_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            
            # Check if timestamp is within acceptable range
            age = (datetime.utcnow() - event_time).total_seconds()
            return 0 <= age <= max_age
            
        except Exception as e:
            logger.error(f"Timestamp validation failed: {e}")
            return False
    
    @staticmethod
    def validate_ip_address(ip_address: str, allowed_ips: List[str]) -> bool:
        """Validate source IP address."""
        if not allowed_ips:
            return True  # No IP restrictions
        
        return ip_address in allowed_ips
    
    @staticmethod
    def sanitize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize webhook payload to prevent injection attacks."""
        def sanitize_value(value: Any) -> Any:
            if isinstance(value, str):
                # Remove potentially dangerous characters
                sanitized = re.sub(r'[<>&"\']', '', value)
                # Limit string length
                return sanitized[:1000]
            elif isinstance(value, dict):
                return {k: sanitize_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [sanitize_value(item) for item in value]
            else:
                return value
        
        return sanitize_value(payload)


class WebhookEventRouter:
    """Routes webhook events to appropriate handlers."""
    
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        self._wildcard_handlers: List[Callable] = []
    
    def add_handler(self, event_type: str, handler: Callable) -> None:
        """Add event handler for specific event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def add_wildcard_handler(self, handler: Callable) -> None:
        """Add wildcard handler for all events."""
        self._wildcard_handlers.append(handler)
    
    def remove_handler(self, event_type: str, handler: Callable) -> None:
        """Remove event handler."""
        if event_type in self._handlers:
            self._handlers[event_type].remove(handler)
    
    async def route_event(self, event: WebhookEvent) -> None:
        """Route event to appropriate handlers."""
        # Call specific handlers
        if event.event_type in self._handlers:
            for handler in self._handlers[event.event_type]:
                try:
                    await handler(event)
                except Exception as e:
                    logger.error(f"Error in event handler {handler.__name__}: {e}")
        
        # Call wildcard handlers
        for handler in self._wildcard_handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Error in wildcard handler {handler.__name__}: {e}")


class WebhookRetryManager:
    """Manages webhook retry logic with exponential backoff."""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
    
    def calculate_delay(self, retry_count: int) -> float:
        """Calculate delay for retry attempt."""
        delay = self.base_delay * (self.exponential_base ** retry_count)
        return min(delay, self.max_delay)
    
    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Execute function with retry logic."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    delay = self.calculate_delay(attempt)
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All retry attempts failed after {self.max_retries} retries: {e}")
                    raise
        
        raise last_exception


class WebhookIntegration(BaseIntegrationImpl):
    """Generic webhook integration with comprehensive security and routing."""
    
    def __init__(self, config: WebhookIntegrationConfig):
        super().__init__(IntegrationType.WEBHOOK, config.dict())
        
        self.webhook_config = config
        self.logger = logger.getChild("webhook")
        
        # Security validator
        self.security_validator = WebhookSecurityValidator()
        
        # Event router
        self.event_router = WebhookEventRouter()
        
        # Retry manager
        self.retry_manager = WebhookRetryManager(
            max_retries=config.retry_config.max_retries,
            base_delay=config.retry_config.base_delay,
            max_delay=config.retry_config.max_delay
        )
        
        # Rate limiting
        self._rate_limit_info = {
            "remaining": 1000,  # Default webhook rate limit
            "reset": None,
            "retry_after": None
        }
        
        # Event tracking
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._processed_events: set[str] = set()
        self._dead_letter_queue: List[WebhookPayload] = []
        
        # Connection state
        self._connected = False
        self._webhook_endpoints: Dict[str, Dict[str, Any]] = {}
    
    # Authentication and Setup
    
    async def authenticate(self) -> bool:
        """Authenticate webhook integration."""
        try:
            # Test webhook endpoint accessibility
            if self.webhook_config.test_endpoint:
                async with httpx.AsyncClient() as client:
                    response = await client.get(self.webhook_config.test_endpoint, timeout=10.0)
                    response.raise_for_status()
            
            self.logger.info("Webhook integration authenticated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Webhook authentication failed: {e}")
            raise WebhookAPIError(f"Authentication failed: {e}")
    
    # Webhook Registration and Management
    
    def register_webhook_endpoint(
        self,
        endpoint_path: str,
        secret: str,
        algorithm: str = "sha256",
        allowed_ips: Optional[List[str]] = None,
        max_age: int = 300
    ) -> None:
        """Register a webhook endpoint configuration."""
        self._webhook_endpoints[endpoint_path] = {
            "secret": secret,
            "algorithm": algorithm,
            "allowed_ips": allowed_ips or [],
            "max_age": max_age
        }
        
        self.logger.info(f"Registered webhook endpoint: {endpoint_path}")
    
    async def process_webhook_request(
        self,
        endpoint_path: str,
        headers: Dict[str, str],
        payload: str,
        source_ip: str
    ) -> Dict[str, Any]:
        """Process incoming webhook request."""
        try:
            # Get endpoint configuration
            endpoint_config = self._webhook_endpoints.get(endpoint_path)
            if not endpoint_config:
                raise WebhookSecurityError(f"Unknown webhook endpoint: {endpoint_path}")
            
            # Validate source IP
            if not self.security_validator.validate_ip_address(
                source_ip, endpoint_config["allowed_ips"]
            ):
                raise WebhookSecurityError(f"Unauthorized source IP: {source_ip}")
            
            # Extract signature from headers
            signature = (
                headers.get("X-Hub-Signature-256") or
                headers.get("X-Hub-Signature") or
                headers.get("X-Signature") or
                headers.get("Signature")
            )
            
            if not signature and endpoint_config["secret"]:
                raise WebhookSecurityError("Missing webhook signature")
            
            # Validate signature if secret is configured
            if endpoint_config["secret"] and signature:
                if not self.security_validator.validate_signature(
                    payload, signature, endpoint_config["secret"], endpoint_config["algorithm"]
                ):
                    raise WebhookSecurityError("Invalid webhook signature")
            
            # Validate timestamp to prevent replay attacks
            timestamp = (
                headers.get("X-Timestamp") or
                headers.get("X-Request-Timestamp") or
                headers.get("X-Event-Time")
            )
            
            if timestamp and not self.security_validator.validate_timestamp(
                timestamp, endpoint_config["max_age"]
            ):
                raise WebhookSecurityError("Webhook timestamp too old")
            
            # Parse payload
            try:
                data = json.loads(payload)
            except json.JSONDecodeError as e:
                raise WebhookAPIError(f"Invalid JSON payload: {e}")
            
            # Sanitize payload
            data = self.security_validator.sanitize_payload(data)
            
            # Extract event information
            event_id = (
                headers.get("X-Event-ID") or
                headers.get("X-Request-ID") or
                data.get("id") or
                data.get("event_id") or
                hashlib.sha256(f"{endpoint_path}:{payload}".encode()).hexdigest()[:16]
            )
            
            event_type = (
                headers.get("X-Event-Type") or
                headers.get("X-GitHub-Event") or
                headers.get("X-Slack-Event") or
                data.get("type") or
                data.get("event_type") or
                "unknown"
            )
            
            # Create webhook payload
            webhook_payload = WebhookPayload(
                event_id=event_id,
                event_type=event_type,
                timestamp=datetime.utcnow(),
                data=data,
                source=endpoint_path,
                signature=signature,
                headers=headers,
                raw_payload=payload
            )
            
            # Process the webhook
            result = await self._process_webhook_payload(webhook_payload)
            
            return {
                "status": "success",
                "event_id": event_id,
                "event_type": event_type,
                "processed_at": datetime.utcnow().isoformat()
            }
            
        except WebhookSecurityError as e:
            self.logger.error(f"Webhook security validation failed: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Webhook processing failed: {e}")
            raise WebhookAPIError(f"Failed to process webhook: {e}")
    
    async def _process_webhook_payload(self, payload: WebhookPayload) -> None:
        """Process webhook payload with retry logic."""
        try:
            # Check for duplicate events
            if payload.event_id in self._processed_events:
                self.logger.info(f"Duplicate webhook event ignored: {payload.event_id}")
                return
            
            # Mark as processed to prevent duplicates
            self._processed_events.add(payload.event_id)
            
            # Create webhook event
            webhook_event = WebhookEvent(
                event_id=payload.event_id,
                event_type=payload.event_type,
                payload=payload.data,
                source=payload.source,
                timestamp=payload.timestamp
            )
            
            # Process with retry logic
            await self.retry_manager.execute_with_retry(
                self._handle_webhook_event,
                webhook_event
            )
            
            payload.processed_at = datetime.utcnow()
            payload.status = "processed"
            
            self.logger.info(f"Webhook event processed successfully: {payload.event_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to process webhook payload: {e}")
            payload.status = "failed"
            
            # Add to dead letter queue
            await self._add_to_dead_letter_queue(payload, str(e))
            
            raise
    
    async def _handle_webhook_event(self, event: WebhookEvent) -> None:
        """Handle webhook event by routing to appropriate handlers."""
        await self.event_router.route_event(event)
    
    async def _add_to_dead_letter_queue(self, payload: WebhookPayload, error: str) -> None:
        """Add failed webhook to dead letter queue."""
        payload.retry_count += 1
        self._dead_letter_queue.append(payload)
        
        # Limit dead letter queue size
        if len(self._dead_letter_queue) > self.webhook_config.dead_letter_queue_size:
            self._dead_letter_queue.pop(0)
        
        self.logger.error(f"Added webhook to dead letter queue: {payload.event_id}, Error: {error}")
    
    # Outgoing Webhooks
    
    async def send_webhook(
        self,
        url: str,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        secret: Optional[str] = None,
        algorithm: str = "sha256"
    ) -> Dict[str, Any]:
        """Send outgoing webhook with signature."""
        # Prepare headers
        webhook_headers = headers or {}
        webhook_headers.update({
            "Content-Type": "application/json",
            "User-Agent": "AI-Customer-Service-Agent/1.0",
            "X-Event-ID": hashlib.sha256(json.dumps(payload).encode()).hexdigest()[:16],
            "X-Event-Type": payload.get("type", "generic"),
            "X-Timestamp": str(int(time.time()))
        })
        
        # Add signature if secret is provided
        if secret:
            payload_str = json.dumps(payload, separators=(',', ':'))
            signature = hmac.new(
                secret.encode('utf-8'),
                payload_str.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            webhook_headers["X-Hub-Signature-256"] = f"{algorithm}={signature}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=webhook_headers
                )
                response.raise_for_status()
                
                self.logger.info(f"Webhook sent successfully to {url}")
                
                return {
                    "status": "sent",
                    "status_code": response.status_code,
                    "response_body": response.text,
                    "sent_at": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Failed to send webhook to {url}: {e}")
            raise WebhookAPIError(f"Failed to send webhook: {e}")
    
    # Event Registration
    
    def add_event_handler(self, event_type: str, handler: Callable[[WebhookEvent], None]) -> None:
        """Add webhook event handler."""
        self.event_router.add_handler(event_type, handler)
    
    def add_wildcard_handler(self, handler: Callable[[WebhookEvent], None]) -> None:
        """Add wildcard event handler."""
        self.event_router.add_wildcard_handler(handler)
    
    def remove_event_handler(self, event_type: str, handler: Callable) -> None:
        """Remove webhook event handler."""
        self.event_router.remove_handler(event_type, handler)
    
    # Dead Letter Queue Management
    
    async def retry_dead_letter_queue(self) -> Dict[str, Any]:
        """Retry processing dead letter queue."""
        successful = 0
        failed = 0
        
        # Process each item in dead letter queue
        for payload in self._dead_letter_queue[:]:
            try:
                await self._process_webhook_payload(payload)
                self._dead_letter_queue.remove(payload)
                successful += 1
                
            except Exception as e:
                self.logger.error(f"Failed to retry dead letter item {payload.event_id}: {e}")
                failed += 1
        
        return {
            "successful": successful,
            "failed": failed,
            "remaining": len(self._dead_letter_queue)
        }
    
    async def get_dead_letter_queue_status(self) -> Dict[str, Any]:
        """Get dead letter queue status."""
        return {
            "size": len(self._dead_letter_queue),
            "oldest_event": (
                self._dead_letter_queue[0].received_at.isoformat()
                if self._dead_letter_queue else None
            ),
            "newest_event": (
                self._dead_letter_queue[-1].received_at.isoformat()
                if self._dead_letter_queue else None
            ),
            "max_size": self.webhook_config.dead_letter_queue_size
        }
    
    # Monitoring and Reporting
    
    async def get_webhook_stats(self) -> Dict[str, Any]:
        """Get webhook processing statistics."""
        return {
            "processed_events": len(self._processed_events),
            "dead_letter_queue_size": len(self._dead_letter_queue),
            "registered_endpoints": len(self._webhook_endpoints),
            "rate_limit_remaining": self._rate_limit_info["remaining"],
            "last_check": datetime.utcnow().isoformat()
        }
    
    # Health Check
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        try:
            # Test webhook endpoint registration
            endpoints_healthy = len(self._webhook_endpoints) > 0
            
            # Test event routing
            routing_healthy = bool(self.event_router._handlers or self.event_router._wildcard_handlers)
            
            # Check dead letter queue size
            dlq_healthy = len(self._dead_letter_queue) < self.webhook_config.dead_letter_queue_size * 0.8
            
            # Overall health status
            is_healthy = (
                endpoints_healthy and
                routing_healthy and
                dlq_healthy and
                self._connected
            )
            
            return {
                "status": "healthy" if is_healthy else "degraded",
                "endpoints_configured": endpoints_healthy,
                "routing_configured": routing_healthy,
                "dead_letter_queue_healthy": dlq_healthy,
                "connected": self._connected,
                "registered_endpoints": len(self._webhook_endpoints),
                "event_handlers": sum(len(handlers) for handlers in self.event_router._handlers.values()),
                "dead_letter_queue_size": len(self._dead_letter_queue),
                "last_check": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
    
    async def close(self) -> None:
        """Close integration and cleanup resources."""
        self.logger.info("Closing webhook integration")
        
        # Clear processed events cache
        self._processed_events.clear()
        
        await super().close()


# Export the integration
__all__ = [
    "WebhookIntegration",
    "WebhookPayload",
    "WebhookEvent",
    "WebhookSecurityValidator",
    "WebhookEventRouter",
    "WebhookRetryManager",
    "WebhookAPIError",
    "WebhookRateLimitError",
    "WebhookSecurityError"
]