"""
Test configuration and fixtures for integration tests.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime
from typing import Dict, Any, Optional

from src.integrations.base import BaseIntegrationImpl
from src.integrations.config import IntegrationConfig


class MockIntegration(BaseIntegrationImpl):
    """Mock integration for testing purposes."""
    
    def __init__(self, integration_type: str = "test", config: Optional[Dict[str, Any]] = None):
        config = config or {}
        super().__init__(integration_type, config)
        self._health_status = "healthy"
        self._response_time = 100.0
    
    async def authenticate(self) -> bool:
        """Mock authentication."""
        return True
    
    async def health_check(self) -> Dict[str, Any]:
        """Mock health check."""
        return {
            "status": self._health_status,
            "response_time": self._response_time,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def sync_data(self, direction: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Mock data sync."""
        return {
            "synced": True,
            "direction": direction,
            "items_processed": 10,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def set_health_status(self, status: str, response_time: float = 100.0):
        """Set mock health status."""
        self._health_status = status
        self._response_time = response_time


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_integration():
    """Provide a mock integration instance."""
    return MockIntegration("test")


@pytest.fixture
def mock_integration_config():
    """Provide a mock integration configuration."""
    return IntegrationConfig(
        name="test_integration",
        type="test",
        enabled=True,
        config={
            "api_key": "test_api_key",
            "base_url": "https://test.example.com",
            "timeout": 30
        },
        rate_limit={"requests_per_second": 10},
        retry={"max_attempts": 3, "base_delay": 0.1},
        circuit_breaker={"failure_threshold": 3, "recovery_timeout": 60.0}
    )


@pytest.fixture
def mock_oauth_config():
    """Provide a mock OAuth configuration."""
    return {
        "client_id": "test_client_id",
        "client_secret": "test_client_secret",
        "authorization_url": "https://auth.example.com/authorize",
        "token_url": "https://auth.example.com/token",
        "redirect_uri": "https://app.example.com/callback",
        "scope": "read write"
    }


@pytest.fixture
def mock_salesforce_config():
    """Provide a mock Salesforce configuration."""
    return {
        "server_url": "https://test.salesforce.com",
        "username": "test@example.com",
        "password": "test_password",
        "security_token": "test_security_token",
        "client_id": "test_client_id",
        "client_secret": "test_client_secret",
        "api_version": "v58.0"
    }


@pytest.fixture
def mock_slack_config():
    """Provide a mock Slack configuration."""
    return {
        "bot_token": "xoxb-test-bot-token",
        "app_token": "xapp-test-app-token",
        "signing_secret": "test_signing_secret",
        "rate_limit": {"requests_per_second": 10}
    }


@pytest.fixture
def mock_teams_config():
    """Provide a mock Teams configuration."""
    return {
        "app_id": "test_app_id",
        "app_password": "test_app_password",
        "tenant_id": "test_tenant_id",
        "rate_limit": {"requests_per_second": 20}
    }


@pytest.fixture
def mock_email_config():
    """Provide a mock email configuration."""
    return {
        "imap_server": "imap.gmail.com",
        "imap_port": 993,
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "username": "test@example.com",
        "password": "test_password",
        "use_ssl": True,
        "rate_limit": {"requests_per_second": 5}
    }


@pytest.fixture
def mock_whatsapp_config():
    """Provide a mock WhatsApp configuration."""
    return {
        "access_token": "test_access_token",
        "phone_number_id": "1234567890",
        "business_account_id": "0987654321",
        "webhook_verify_token": "test_verify_token",
        "rate_limit": {"requests_per_second": 20}
    }


@pytest.fixture
def mock_webhook_config():
    """Provide a mock webhook configuration."""
    return {
        "webhook_url": "https://example.com/webhook",
        "secret_key": "test_secret_key",
        "signature_header": "X-Hub-Signature-256",
        "algorithm": "sha256",
        "rate_limit": {"requests_per_second": 100}
    }


@pytest.fixture
def mock_jira_config():
    """Provide a mock Jira configuration."""
    return {
        "server_url": "https://test.atlassian.net",
        "username": "test@example.com",
        "api_token": "test_api_token",
        "project_key": "TEST",
        "rate_limit": {"requests_per_second": 50}
    }


@pytest.fixture
def mock_servicenow_config():
    """Provide a mock ServiceNow configuration."""
    return {
        "instance_url": "https://test.service-now.com",
        "username": "test_user",
        "password": "test_password",
        "client_id": "test_client_id",
        "client_secret": "test_client_secret",
        "rate_limit": {"requests_per_second": 30}
    }


@pytest.fixture
def mock_zendesk_config():
    """Provide a mock Zendesk configuration."""
    return {
        "subdomain": "test",
        "email": "test@example.com",
        "api_token": "test_api_token",
        "rate_limit": {"requests_per_second": 40}
    }


@pytest.fixture
def mock_oauth_provider_config():
    """Provide a mock OAuth provider configuration."""
    return {
        "issuer": "https://auth.example.com",
        "authorization_endpoint": "https://auth.example.com/authorize",
        "token_endpoint": "https://auth.example.com/token",
        "jwks_uri": "https://auth.example.com/.well-known/jwks.json",
        "scopes_supported": ["openid", "profile", "email", "api"],
        "grant_types_supported": ["authorization_code", "client_credentials", "refresh_token"],
        "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post"],
        "code_challenge_methods_supported": ["S256", "plain"]
    }


@pytest.fixture
def mock_response_data():
    """Provide mock HTTP response data."""
    return {
        "status_code": 200,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"success": True, "data": {"id": "123", "name": "Test"}},
        "text_data": '{"success": true, "data": {"id": "123", "name": "Test"}}'
    }


@pytest.fixture
def mock_error_response():
    """Provide mock error response data."""
    return {
        "status_code": 400,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"error": "Bad Request", "message": "Invalid parameters"},
        "text_data": '{"error": "Bad Request", "message": "Invalid parameters"}'
    }


@pytest.fixture
def mock_rate_limit_response():
    """Provide mock rate limit response data."""
    return {
        "status_code": 429,
        "headers": {
            "Content-Type": "application/json",
            "X-RateLimit-Limit": "100",
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": "1234567890"
        },
        "json_data": {"error": "Rate limit exceeded", "retry_after": 60},
        "text_data": '{"error": "Rate limit exceeded", "retry_after": 60}'
    }


@pytest.fixture
def mock_webhook_payload():
    """Provide mock webhook payload data."""
    return {
        "event_type": "user.created",
        "data": {
            "id": "user123",
            "email": "test@example.com",
            "name": "Test User",
            "created_at": "2024-01-01T00:00:00Z"
        },
        "timestamp": "2024-01-01T00:00:00Z",
        "signature": "sha256=test_signature"
    }


@pytest.fixture
def mock_health_check_response():
    """Provide mock health check response data."""
    return {
        "status": "healthy",
        "response_time": 150.0,
        "timestamp": "2024-01-01T00:00:00Z",
        "version": "1.0.0",
        "dependencies": {
            "database": "healthy",
            "cache": "healthy",
            "external_api": "healthy"
        }
    }


@pytest.fixture
def mock_oauth_tokens():
    """Provide mock OAuth tokens."""
    return {
        "access_token": "test_access_token_12345",
        "refresh_token": "test_refresh_token_67890",
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": "read write",
        "id_token": "test_id_token"
    }


@pytest.fixture
def mock_jwt_token():
    """Provide mock JWT token data."""
    import jwt
    from datetime import datetime, timedelta
    
    payload = {
        "sub": "user123",
        "iss": "https://auth.example.com",
        "aud": "test_client_id",
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
        "scope": "read write"
    }
    
    return jwt.encode(payload, "test_secret_key", algorithm="HS256")


# Test utilities
class AsyncMock(Mock):
    """Async mock for testing async functions."""
    
    async def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)


def assert_async_called(mock_obj):
    """Assert that an async mock was called."""
    assert mock_obj.called


def assert_async_called_with(mock_obj, *args, **kwargs):
    """Assert that an async mock was called with specific arguments."""
    mock_obj.assert_called_with(*args, **kwargs)


def create_mock_response(status_code=200, json_data=None, text_data=None, headers=None):
    """Create a mock HTTP response."""
    response = Mock()
    response.status_code = status_code
    response.headers = headers or {}
    response.text = text_data or json.dumps(json_data or {})
    response.json = AsyncMock(return_value=json_data or {})
    response.raise_for_status = Mock()
    return response


# Pytest configuration
def pytest_configure(config):
    """Configure pytest for integration tests."""
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as a performance test"
    )
    config.addinivalue_line(
        "markers", "security: mark test as a security test"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to handle async tests."""
    for item in items:
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)


# Async test helpers
@pytest.fixture
def async_return():
    """Helper to create async return values."""
    def _async_return(value):
        future = asyncio.Future()
        future.set_result(value)
        return future
    return _async_return


@pytest.fixture
def async_raise():
    """Helper to create async exceptions."""
    def _async_raise(exception):
        future = asyncio.Future()
        future.set_exception(exception)
        return future
    return _async_raise


# Performance test configuration
@pytest.fixture(scope="session")
def performance_thresholds():
    """Define performance thresholds for tests."""
    return {
        "api_request_max_time": 0.5,  # 500ms
        "health_check_max_time": 2.0,  # 2 seconds
        "metrics_export_max_time": 0.1,  # 100ms
        "bulk_operation_max_time": 5.0,  # 5 seconds
        "concurrent_operation_max_time": 3.0,  # 3 seconds
    }


# Security test configuration
@pytest.fixture(scope="session")
def security_test_data():
    """Provide security test data."""
    return {
        "malicious_payloads": [
            "<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
            "../../../etc/passwd",
            "javascript:alert('xss')",
            "<iframe src='javascript:alert(1)'></iframe>"
        ],
        "test_secrets": [
            "sk_test_1234567890abcdef",
            "AKIAIOSFODNN7EXAMPLE",
            "ghp_1234567890abcdefghijklmnopqrstuvwxyz",
            "xoxb-1234567890-1234567890-abcdefghijklmnopqrstuvwx"
        ]
    }