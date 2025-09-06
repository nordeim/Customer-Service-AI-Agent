"""
Integration package for external system connections.

This package provides integration capabilities for:
- Salesforce Service Cloud
- Multi-channel communication (Slack, Teams, Email, WhatsApp)
- Third-party systems (Jira, ServiceNow, Zendesk)
- OAuth 2.0 / OIDC authentication
- Integration monitoring and health checks
"""

from typing import Dict, Type, Optional, Any
from abc import ABC, abstractmethod
from enum import Enum
import logging
from datetime import datetime

# Package version
__version__ = "1.0.0"

# Configure logger
logger = logging.getLogger(__name__)


class IntegrationStatus(Enum):
    """Integration health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class IntegrationType(Enum):
    """Supported integration types."""
    SALESFORCE = "salesforce"
    SLACK = "slack"
    TEAMS = "teams"
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    JIRA = "jira"
    SERVICENOW = "servicenow"
    ZENDESK = "zendesk"
    WEBHOOK = "webhook"


class IntegrationHealth:
    """Integration health status information."""
    
    def __init__(
        self,
        status: IntegrationStatus,
        last_check: datetime,
        response_time_ms: Optional[float] = None,
        error_rate: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.status = status
        self.last_check = last_check
        self.response_time_ms = response_time_ms
        self.error_rate = error_rate
        self.details = details or {}


class IntegrationException(Exception):
    """Base exception for integration errors."""
    
    def __init__(self, message: str, integration_type: IntegrationType, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.integration_type = integration_type
        self.details = details or {}
        self.timestamp = datetime.utcnow()


class AuthError(IntegrationException):
    """Authentication or authorization error."""
    pass


class RateLimitError(IntegrationException):
    """Rate limit exceeded error."""
    pass


class SyncError(IntegrationException):
    """Data synchronization error."""
    pass


class ConfigurationError(IntegrationException):
    """Integration configuration error."""
    pass


class BaseIntegration(ABC):
    """Abstract base class for all integrations."""
    
    def __init__(self, integration_type: IntegrationType, config: Dict[str, Any]):
        self.integration_type = integration_type
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{integration_type.value}")
        self._health_status = IntegrationHealth(
            status=IntegrationStatus.UNKNOWN,
            last_check=datetime.utcnow()
        )
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with the external system."""
        pass
    
    @abstractmethod
    async def health_check(self) -> IntegrationHealth:
        """Perform health check of the integration."""
        pass
    
    @abstractmethod
    async def sync_data(self, direction: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Synchronize data with the external system."""
        pass
    
    async def close(self) -> None:
        """Close integration connections and cleanup resources."""
        self.logger.info(f"Closing {self.integration_type.value} integration")
    
    def get_health_status(self) -> IntegrationHealth:
        """Get current health status."""
        return self._health_status
    
    def _update_health_status(self, health: IntegrationHealth) -> None:
        """Update health status."""
        self._health_status = health
        self.logger.debug(f"Health status updated: {health.status.value}")


class IntegrationRegistry:
    """Registry for managing integrations."""
    
    def __init__(self):
        self._integrations: Dict[IntegrationType, BaseIntegration] = {}
        self._logger = logging.getLogger(f"{__name__}.registry")
    
    def register(self, integration: BaseIntegration) -> None:
        """Register an integration."""
        self._integrations[integration.integration_type] = integration
        self._logger.info(f"Registered integration: {integration.integration_type.value}")
    
    def unregister(self, integration_type: IntegrationType) -> None:
        """Unregister an integration."""
        if integration_type in self._integrations:
            del self._integrations[integration_type]
            self._logger.info(f"Unregistered integration: {integration_type.value}")
    
    def get(self, integration_type: IntegrationType) -> Optional[BaseIntegration]:
        """Get integration by type."""
        return self._integrations.get(integration_type)
    
    def list_integrations(self) -> list[IntegrationType]:
        """List all registered integration types."""
        return list(self._integrations.keys())
    
    async def health_check_all(self) -> Dict[IntegrationType, IntegrationHealth]:
        """Perform health check on all integrations."""
        results = {}
        for integration_type, integration in self._integrations.items():
            try:
                health = await integration.health_check()
                results[integration_type] = health
            except Exception as e:
                self._logger.error(f"Health check failed for {integration_type.value}: {e}")
                results[integration_type] = IntegrationHealth(
                    status=IntegrationStatus.UNHEALTHY,
                    last_check=datetime.utcnow(),
                    details={"error": str(e)}
                )
        return results
    
    async def close_all(self) -> None:
        """Close all integrations."""
        self._logger.info("Closing all integrations")
        for integration in self._integrations.values():
            try:
                await integration.close()
            except Exception as e:
                self._logger.error(f"Error closing integration: {e}")


# Global integration registry
_integration_registry = IntegrationRegistry()


def get_integration_registry() -> IntegrationRegistry:
    """Get the global integration registry."""
    return _integration_registry


def register_integration(integration: BaseIntegration) -> None:
    """Register an integration in the global registry."""
    get_integration_registry().register(integration)


def get_integration(integration_type: IntegrationType) -> Optional[BaseIntegration]:
    """Get integration from global registry."""
    return get_integration_registry().get(integration_type)


# Export key components
__all__ = [
    "__version__",
    "IntegrationStatus",
    "IntegrationType",
    "IntegrationHealth",
    "IntegrationException",
    "AuthError",
    "RateLimitError",
    "SyncError",
    "ConfigurationError",
    "BaseIntegration",
    "IntegrationRegistry",
    "get_integration_registry",
    "register_integration",
    "get_integration",
]