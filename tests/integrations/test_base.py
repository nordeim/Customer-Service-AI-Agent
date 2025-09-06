"""
Tests for integration base classes and infrastructure.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from src.integrations.base import (
    BaseIntegrationImpl,
    OAuth2Client,
    RateLimiter,
    RetryHandler,
    CircuitBreaker,
    RateLimitError,
    OAuth2Config
)
from src.integrations.config import (
    RateLimitConfig,
    RetryConfig,
    CircuitBreakerConfig,
    OAuth2ClientConfig
)


class TestOAuth2Client:
    """Test OAuth2Client functionality."""
    
    @pytest.fixture
    def oauth_config(self):
        return OAuth2Config(
            client_id="test_client",
            client_secret="test_secret",
            authorization_url="https://auth.example.com/authorize",
            token_url="https://auth.example.com/token",
            redirect_uri="https://app.example.com/callback",
            scope="read write"
        )
    
    @pytest.fixture
    def oauth_client(self, oauth_config):
        return OAuth2Client(oauth_config)
    
    @pytest.mark.asyncio
    async def test_initialization(self, oauth_client, oauth_config):
        """Test OAuth2Client initialization."""
        assert oauth_client.config == oauth_config
        assert oauth_client.access_token is None
        assert oauth_client.refresh_token is None
        assert oauth_client.token_expires_at is None
    
    @pytest.mark.asyncio
    async def test_get_authorization_url(self, oauth_client):
        """Test authorization URL generation."""
        url = oauth_client.get_authorization_url(state="test_state")
        
        assert "https://auth.example.com/authorize" in url
        assert "client_id=test_client" in url
        assert "response_type=code" in url
        assert "state=test_state" in url
    
    @pytest.mark.asyncio
    async def test_exchange_code_for_token_success(self, oauth_client):
        """Test successful code exchange."""
        mock_response = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_in": 3600,
            "token_type": "Bearer"
        }
        
        with patch.object(oauth_client, '_make_token_request', return_value=mock_response):
            token = await oauth_client.exchange_code_for_token("test_code")
            
            assert token == "test_access_token"
            assert oauth_client.access_token == "test_access_token"
            assert oauth_client.refresh_token == "test_refresh_token"
            assert oauth_client.token_expires_at is not None
    
    @pytest.mark.asyncio
    async def test_get_valid_access_token_cached(self, oauth_client):
        """Test getting cached valid access token."""
        oauth_client.access_token = "cached_token"
        oauth_client.token_expires_at = datetime.utcnow() + timedelta(hours=1)
        
        token = await oauth_client.get_valid_access_token()
        
        assert token == "cached_token"
    
    @pytest.mark.asyncio
    async def test_get_valid_access_token_expired(self, oauth_client):
        """Test getting new access token when cached token is expired."""
        oauth_client.access_token = "expired_token"
        oauth_client.token_expires_at = datetime.utcnow() - timedelta(hours=1)
        oauth_client.refresh_token = "valid_refresh_token"
        
        mock_response = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600,
            "token_type": "Bearer"
        }
        
        with patch.object(oauth_client, '_make_token_request', return_value=mock_response):
            token = await oauth_client.get_valid_access_token()
            
            assert token == "new_access_token"
            assert oauth_client.access_token == "new_access_token"
    
    @pytest.mark.asyncio
    async def test_refresh_access_token(self, oauth_client):
        """Test access token refresh."""
        oauth_client.refresh_token = "valid_refresh_token"
        
        mock_response = {
            "access_token": "refreshed_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600,
            "token_type": "Bearer"
        }
        
        with patch.object(oauth_client, '_make_token_request', return_value=mock_response):
            token = await oauth_client.refresh_access_token()
            
            assert token == "refreshed_token"
            assert oauth_client.access_token == "refreshed_token"
    
    @pytest.mark.asyncio
    async def test_close(self, oauth_client):
        """Test cleanup."""
        oauth_client.access_token = "test_token"
        oauth_client.refresh_token = "test_refresh"
        
        await oauth_client.close()
        
        assert oauth_client.access_token is None
        assert oauth_client.refresh_token is None


class TestRateLimiter:
    """Test RateLimiter functionality."""
    
    @pytest.fixture
    def rate_limit_config(self):
        return RateLimitConfig(
            requests_per_second=10,
            burst_capacity=20,
            window_seconds=60
        )
    
    @pytest.fixture
    def rate_limiter(self, rate_limit_config):
        return RateLimiter(rate_limit_config)
    
    @pytest.mark.asyncio
    async def test_initialization(self, rate_limiter, rate_limit_config):
        """Test RateLimiter initialization."""
        assert rate_limiter.config == rate_limit_config
        assert rate_limiter._tokens == 20
        assert rate_limiter._last_refill is not None
    
    @pytest.mark.asyncio
    async def test_is_allowed_within_limit(self, rate_limiter):
        """Test requests within rate limit."""
        # Should allow first request
        allowed = await rate_limiter.is_allowed("test_key")
        assert allowed is True
        
        # Should allow up to burst capacity
        for i in range(19):
            allowed = await rate_limiter.is_allowed("test_key")
            assert allowed is True
        
        # Should deny next request
        allowed = await rate_limiter.is_allowed("test_key")
        assert allowed is False
    
    @pytest.mark.asyncio
    async def test_token_refill(self, rate_limiter):
        """Test token refill over time."""
        # Consume all tokens
        for i in range(20):
            await rate_limiter.is_allowed("test_key")
        
        # Should be denied
        allowed = await rate_limiter.is_allowed("test_key")
        assert allowed is False
        
        # Wait for tokens to refill
        await asyncio.sleep(1.1)
        
        # Should allow request now
        allowed = await rate_limiter.is_allowed("test_key")
        assert allowed is True
    
    @pytest.mark.asyncio
    async def test_get_retry_after(self, rate_limiter):
        """Test getting retry after time."""
        # Consume all tokens
        for i in range(20):
            await rate_limiter.is_allowed("test_key")
        
        retry_after = await rate_limiter.get_retry_after("test_key")
        assert retry_after > 0
        assert retry_after <= 1.0
    
    @pytest.mark.asyncio
    async def test_different_keys(self, rate_limiter):
        """Test rate limiting for different keys."""
        # Consume tokens for key1
        for i in range(10):
            await rate_limiter.is_allowed("key1")
        
        # key2 should still have full capacity
        for i in range(20):
            allowed = await rate_limiter.is_allowed("key2")
            assert allowed is True
    
    @pytest.mark.asyncio
    async def test_rate_limit_error(self, rate_limiter):
        """Test rate limit error generation."""
        # Consume all tokens
        for i in range(20):
            await rate_limiter.is_allowed("test_key")
        
        with pytest.raises(RateLimitError):
            await rate_limiter.check_rate_limit("test_key")


class TestRetryHandler:
    """Test RetryHandler functionality."""
    
    @pytest.fixture
    def retry_config(self):
        return RetryConfig(
            max_attempts=3,
            base_delay=0.1,
            max_delay=1.0,
            exponential_base=2.0
        )
    
    @pytest.fixture
    def retry_handler(self, retry_config):
        return RetryHandler(retry_config)
    
    @pytest.mark.asyncio
    async def test_successful_operation(self, retry_handler):
        """Test successful operation without retries."""
        async def success_func():
            return "success"
        
        result = await retry_handler.execute_with_retry(success_func)
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_retry_on_failure(self, retry_handler):
        """Test retry on operation failure."""
        call_count = 0
        
        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"
        
        result = await retry_handler.execute_with_retry(failing_func)
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, retry_handler):
        """Test failure after max retries."""
        async def always_failing_func():
            raise Exception("Permanent failure")
        
        with pytest.raises(Exception, match="Permanent failure"):
            await retry_handler.execute_with_retry(always_failing_func)
    
    @pytest.mark.asyncio
    async def test_delay_calculation(self, retry_handler):
        """Test retry delay calculation."""
        assert retry_handler.calculate_delay(0) == 0.1  # base_delay
        assert retry_handler.calculate_delay(1) == 0.2  # base_delay * 2^1
        assert retry_handler.calculate_delay(2) == 0.4  # base_delay * 2^2
        assert retry_handler.calculate_delay(10) == 1.0  # max_delay
    
    @pytest.mark.asyncio
    async def test_custom_retry_condition(self, retry_handler):
        """Test custom retry condition."""
        def should_retry(error):
            return isinstance(error, ValueError)
        
        call_count = 0
        
        async def value_error_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Retry this")
            elif call_count == 2:
                raise RuntimeError("Don't retry this")
            return "success"
        
        with pytest.raises(RuntimeError, match="Don't retry this"):
            await retry_handler.execute_with_retry(value_error_func, should_retry=should_retry)
        
        assert call_count == 2


class TestCircuitBreaker:
    """Test CircuitBreaker functionality."""
    
    @pytest.fixture
    def circuit_breaker_config(self):
        return CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=1.0,
            success_threshold=2,
            half_open_max_calls=5
        )
    
    @pytest.fixture
    def circuit_breaker(self, circuit_breaker_config):
        return CircuitBreaker(circuit_breaker_config)
    
    @pytest.mark.asyncio
    async def test_initial_state(self, circuit_breaker):
        """Test initial circuit breaker state."""
        assert circuit_breaker.state == "CLOSED"
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.success_count == 0
    
    @pytest.mark.asyncio
    async def test_successful_calls(self, circuit_breaker):
        """Test successful calls in closed state."""
        async def success_func():
            return "success"
        
        result = await circuit_breaker.execute(success_func)
        assert result == "success"
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.success_count == 1
    
    @pytest.mark.asyncio
    async def test_failure_counting(self, circuit_breaker):
        """Test failure counting and state transition."""
        async def failing_func():
            raise Exception("Test failure")
        
        # First two failures
        for i in range(2):
            with pytest.raises(Exception):
                await circuit_breaker.execute(failing_func)
        
        assert circuit_breaker.state == "CLOSED"
        assert circuit_breaker.failure_count == 2
        
        # Third failure should open circuit
        with pytest.raises(Exception):
            await circuit_breaker.execute(failing_func)
        
        assert circuit_breaker.state == "OPEN"
    
    @pytest.mark.asyncio
    async def test_open_circuit_blocks_calls(self, circuit_breaker):
        """Test that open circuit blocks calls."""
        # Open the circuit
        circuit_breaker.state = "OPEN"
        circuit_breaker._opened_at = datetime.utcnow()
        
        async def any_func():
            return "should not execute"
        
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            await circuit_breaker.execute(any_func)
    
    @pytest.mark.asyncio
    async def test_circuit_recovery(self, circuit_breaker):
        """Test circuit recovery process."""
        # Open the circuit
        circuit_breaker.state = "OPEN"
        circuit_breaker._opened_at = datetime.utcnow() - timedelta(seconds=2)  # Past recovery timeout
        
        # Should transition to half-open
        async def success_func():
            return "success"
        
        result = await circuit_breaker.execute(success_func)
        assert result == "success"
        assert circuit_breaker.state == "HALF_OPEN"
        assert circuit_breaker.success_count == 1
    
    @pytest.mark.asyncio
    async def test_half_open_to_closed(self, circuit_breaker):
        """Test transition from half-open to closed."""
        circuit_breaker.state = "HALF_OPEN"
        circuit_breaker.success_count = 1
        circuit_breaker.config.success_threshold = 2
        
        async def success_func():
            return "success"
        
        result = await circuit_breaker.execute(success_func)
        assert result == "success"
        assert circuit_breaker.state == "CLOSED"
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.success_count == 0
    
    @pytest.mark.asyncio
    async def test_half_open_to_open_on_failure(self, circuit_breaker):
        """Test transition from half-open to open on failure."""
        circuit_breaker.state = "HALF_OPEN"
        
        async def failing_func():
            raise Exception("Test failure")
        
        with pytest.raises(Exception):
            await circuit_breaker.execute(failing_func)
        
        assert circuit_breaker.state == "OPEN"


class TestBaseIntegrationImpl:
    """Test BaseIntegrationImpl functionality."""
    
    @pytest.fixture
    def base_integration(self):
        config = {"test": "config"}
        return BaseIntegrationImpl("test_type", config)
    
    def test_initialization(self, base_integration):
        """Test BaseIntegrationImpl initialization."""
        assert base_integration.integration_type == "test_type"
        assert base_integration.config == {"test": "config"}
        assert base_integration._connected is False
    
    @pytest.mark.asyncio
    async def test_connect_success(self, base_integration):
        """Test successful connection."""
        base_integration.authenticate = AsyncMock(return_value=True)
        
        success = await base_integration.connect()
        
        assert success is True
        assert base_integration._connected is True
        base_integration.authenticate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connect_failure(self, base_integration):
        """Test connection failure."""
        base_integration.authenticate = AsyncMock(return_value=False)
        
        success = await base_integration.connect()
        
        assert success is False
        assert base_integration._connected is False
    
    @pytest.mark.asyncio
    async def test_disconnect(self, base_integration):
        """Test disconnection."""
        base_integration._connected = True
        
        await base_integration.disconnect()
        
        assert base_integration._connected is False
    
    def test_is_connected(self, base_integration):
        """Test connection status check."""
        assert base_integration.is_connected() is False
        
        base_integration._connected = True
        assert base_integration.is_connected() is True
    
    @pytest.mark.asyncio
    async def test_health_check_not_implemented(self, base_integration):
        """Test that health_check raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            await base_integration.health_check()
    
    @pytest.mark.asyncio
    async def test_sync_data_not_implemented(self, base_integration):
        """Test that sync_data raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            await base_integration.sync_data("inbound")
    
    @pytest.mark.asyncio
    async def test_close(self, base_integration):
        """Test cleanup."""
        base_integration._connected = True
        
        await base_integration.close()
        
        assert base_integration._connected is False
    
    def test_get_rate_limit_info_not_connected(self, base_integration):
        """Test rate limit info when not connected."""
        info = base_integration.get_rate_limit_info()
        
        assert info["connected"] is False
        assert "error" in info
    
    def test_str_representation(self, base_integration):
        """Test string representation."""
        assert str(base_integration) == "BaseIntegrationImpl(test_type)"


# Integration with rate limiting, retry, and circuit breaker
class TestIntegrationWithResilience:
    """Test integration with resilience patterns."""
    
    @pytest.fixture
    def resilient_integration(self):
        class ResilientIntegration(BaseIntegrationImpl):
            def __init__(self):
                config = {
                    "rate_limit": {"requests_per_second": 10},
                    "retry": {"max_attempts": 3, "base_delay": 0.1},
                    "circuit_breaker": {"failure_threshold": 3, "recovery_timeout": 1.0}
                }
                super().__init__("resilient_test", config)
                self.auth_call_count = 0
                self.health_check_count = 0
            
            async def authenticate(self) -> bool:
                self.auth_call_count += 1
                if self.auth_call_count <= 2:
                    raise Exception("Auth temporary failure")
                return True
            
            async def health_check(self) -> Dict[str, Any]:
                self.health_check_count += 1
                if self.health_check_count == 1:
                    raise Exception("Health check failure")
                return {"status": "healthy"}
            
            async def sync_data(self, direction: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
                return {"synced": True, "direction": direction}
        
        return ResilientIntegration()
    
    @pytest.mark.asyncio
    async def test_resilient_authentication(self, resilient_integration):
        """Test authentication with retry logic."""
        success = await resilient_integration.connect()
        
        assert success is True
        assert resilient_integration.auth_call_count == 3
        assert resilient_integration.is_connected() is True
    
    @pytest.mark.asyncio
    async def test_resilient_health_check(self, resilient_integration):
        """Test health check with retry logic."""
        await resilient_integration.connect()  # Connect first
        
        health = await resilient_integration.health_check()
        
        assert health["status"] == "healthy"
        assert resilient_integration.health_check_count == 2
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, resilient_integration):
        """Test rate limiting functionality."""
        await resilient_integration.connect()
        
        # Should allow requests within rate limit
        for i in range(10):
            allowed = await resilient_integration.rate_limiter.is_allowed("test")
            assert allowed is True
        
        # Should deny requests exceeding rate limit
        allowed = await resilient_integration.rate_limiter.is_allowed("test")
        assert allowed is False
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self, resilient_integration):
        """Test circuit breaker integration."""
        # Force circuit to open by simulating failures
        resilient_integration.circuit_breaker.state = "OPEN"
        
        # Should block calls when circuit is open
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            await resilient_integration.circuit_breaker.execute(lambda: "test")


# Performance tests
@pytest.mark.integration
class TestIntegrationPerformance:
    """Performance tests for integration components."""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_performance(self):
        """Test rate limiter performance under load."""
        config = RateLimitConfig(requests_per_second=1000, burst_capacity=1000)
        rate_limiter = RateLimiter(config)
        
        start_time = time.time()
        
        # Test 10000 requests
        tasks = []
        for i in range(10000):
            tasks.append(rate_limiter.is_allowed(f"key_{i % 100}"))
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in reasonable time (< 5 seconds)
        assert duration < 5.0
        assert len([r for r in results if r is True]) > 0
    
    @pytest.mark.asyncio
    async def test_retry_handler_performance(self):
        """Test retry handler performance."""
        config = RetryConfig(max_attempts=5, base_delay=0.01)
        retry_handler = RetryHandler(config)
        
        async def fast_operation():
            return "result"
        
        start_time = time.time()
        
        # Test 100 operations
        tasks = []
        for i in range(100):
            tasks.append(retry_handler.execute_with_retry(fast_operation))
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in reasonable time (< 2 seconds)
        assert duration < 2.0
        assert all(r == "result" for r in results)
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_performance(self):
        """Test circuit breaker performance."""
        config = CircuitBreakerConfig(failure_threshold=100, recovery_timeout=0.1)
        circuit_breaker = CircuitBreaker(config)
        
        async def fast_operation():
            return "result"
        
        start_time = time.time()
        
        # Test 1000 operations
        tasks = []
        for i in range(1000):
            tasks.append(circuit_breaker.execute(fast_operation))
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in reasonable time (< 1 second)
        assert duration < 1.0
        assert all(r == "result" for r in results)


# Error handling tests
@pytest.mark.asyncio
class TestIntegrationErrorHandling:
    """Test error handling in integration components."""
    
    async def test_oauth2_error_handling(self):
        """Test OAuth2 error handling."""
        config = OAuth2Config(
            client_id="test_client",
            client_secret="test_secret",
            authorization_url="https://auth.example.com/authorize",
            token_url="https://auth.example.com/token",
            redirect_uri="https://app.example.com/callback",
            scope="read write"
        )
        
        oauth_client = OAuth2Client(config)
        
        # Test with network error
        with patch.object(oauth_client, '_make_token_request', side_effect=Exception("Network error")):
            with pytest.raises(Exception, match="Network error"):
                await oauth_client.exchange_code_for_token("test_code")
    
    async def test_rate_limiter_error_handling(self):
        """Test rate limiter error handling."""
        config = RateLimitConfig(requests_per_second=1, burst_capacity=1)
        rate_limiter = RateLimiter(config)
        
        # Should handle concurrent access gracefully
        tasks = []
        for i in range(10):
            tasks.append(rate_limiter.is_allowed("test_key"))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Should not raise exceptions
        assert not any(isinstance(r, Exception) for r in results)
    
    async def test_circuit_breaker_error_handling(self):
        """Test circuit breaker error handling."""
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=1.0)
        circuit_breaker = CircuitBreaker(config)
        
        async def failing_func():
            raise ValueError("Test error")
        
        # Circuit should handle errors gracefully
        with pytest.raises(ValueError, match="Test error"):
            await circuit_breaker.execute(failing_func)
        
        # Circuit should still be functional
        assert circuit_breaker.state in ["CLOSED", "OPEN"]