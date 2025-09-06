"""
Multi-channel communication adapters for customer service integrations.

This module provides comprehensive integrations for various communication channels:
- Slack Bot integration with RTM/WebSocket support
- Microsoft Teams integration with Bot Framework
- Email processing with IMAP/SMTP
- WhatsApp Business API integration
- Generic webhook framework with security hardening

All integrations follow enterprise-grade patterns with:
- OAuth 2.0 authentication flows
- Rate limiting and circuit breaker patterns
- Comprehensive error handling and retry logic
- Real-time event processing
- Security hardening (HMAC signatures, IP whitelisting)
- Health monitoring and metrics collection
"""

from __future__ import annotations

from typing import Dict, Type, Any
from enum import Enum

from ..base import BaseIntegrationImpl
from ..config import (
    SlackIntegrationConfig,
    TeamsIntegrationConfig,
    EmailIntegrationConfig,
    WhatsAppIntegrationConfig,
    WebhookIntegrationConfig,
)


class IntegrationType(str, Enum):
    """Supported integration types."""
    
    SALESFORCE = "salesforce"
    SLACK = "slack"
    TEAMS = "teams"
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    WEBHOOK = "webhook"
    JIRA = "jira"
    SERVICENOW = "servicenow"
    ZENDESK = "zendesk"


# Import all channel integrations
from .slack import SlackIntegration, SlackMessage, SlackAPIError, SlackRateLimitError
from .teams import TeamsIntegration, TeamsMessage, AdaptiveCard, TeamsAPIError, TeamsRateLimitError
from .email import EmailIntegration, EmailMessage, EmailValidator, EmailAPIError, EmailRateLimitError
from .whatsapp import (
    WhatsAppIntegration, 
    WhatsAppMessage, 
    WhatsAppMedia, 
    WhatsAppTemplate,
    WhatsAppAPIError, 
    WhatsAppRateLimitError
)
from .webhook import (
    WebhookIntegration,
    WebhookPayload,
    WebhookEvent,
    WebhookSecurityValidator,
    WebhookEventRouter,
    WebhookRetryManager,
    WebhookAPIError,
    WebhookRateLimitError,
    WebhookSecurityError
)


# Integration registry for dynamic loading
INTEGRATION_REGISTRY: Dict[IntegrationType, Type[BaseIntegrationImpl]] = {
    IntegrationType.SLACK: SlackIntegration,
    IntegrationType.TEAMS: TeamsIntegration,
    IntegrationType.EMAIL: EmailIntegration,
    IntegrationType.WHATSAPP: WhatsAppIntegration,
    IntegrationType.WEBHOOK: WebhookIntegration,
}


# Configuration registry
CONFIG_REGISTRY: Dict[IntegrationType, Type[Any]] = {
    IntegrationType.SLACK: SlackIntegrationConfig,
    IntegrationType.TEAMS: TeamsIntegrationConfig,
    IntegrationType.EMAIL: EmailIntegrationConfig,
    IntegrationType.WHATSAPP: WhatsAppIntegrationConfig,
    IntegrationType.WEBHOOK: WebhookIntegrationConfig,
}


def get_integration_class(integration_type: IntegrationType) -> Type[BaseIntegrationImpl]:
    """Get integration class by type."""
    return INTEGRATION_REGISTRY.get(integration_type)


def get_config_class(integration_type: IntegrationType) -> Type[Any]:
    """Get configuration class by integration type."""
    return CONFIG_REGISTRY.get(integration_type)


def list_integration_types() -> list[IntegrationType]:
    """List all available integration types."""
    return list(INTEGRATION_REGISTRY.keys())


# Export all public symbols
__all__ = [
    # Integration types
    "IntegrationType",
    
    # Slack integration
    "SlackIntegration",
    "SlackMessage", 
    "SlackAPIError",
    "SlackRateLimitError",
    
    # Teams integration
    "TeamsIntegration",
    "TeamsMessage",
    "AdaptiveCard",
    "TeamsAPIError", 
    "TeamsRateLimitError",
    
    # Email integration
    "EmailIntegration",
    "EmailMessage",
    "EmailValidator",
    "EmailAPIError",
    "EmailRateLimitError",
    
    # WhatsApp integration
    "WhatsAppIntegration",
    "WhatsAppMessage",
    "WhatsAppMedia",
    "WhatsAppTemplate",
    "WhatsAppAPIError",
    "WhatsAppRateLimitError",
    
    # Webhook integration
    "WebhookIntegration",
    "WebhookPayload",
    "WebhookEvent",
    "WebhookSecurityValidator",
    "WebhookEventRouter",
    "WebhookRetryManager",
    "WebhookAPIError",
    "WebhookRateLimitError",
    "WebhookSecurityError",
    
    # Registry functions
    "INTEGRATION_REGISTRY",
    "CONFIG_REGISTRY",
    "get_integration_class",
    "get_config_class",
    "list_integration_types",
]