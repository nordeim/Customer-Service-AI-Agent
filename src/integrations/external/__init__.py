"""
Third-party service integrations for enterprise customer service workflows.

This module provides integrations with popular enterprise service management platforms:
- Atlassian Jira: Issue tracking and project management
- ServiceNow: ITSM and CSM platform integration
- Zendesk: Customer service and support platform

All integrations follow enterprise-grade patterns with:
- OAuth 2.0 authentication flows
- Comprehensive API coverage with rate limiting
- Real-time event processing and webhooks
- Bulk operations and data synchronization
- Enterprise security and compliance features
"""

from __future__ import annotations

from typing import Dict, Type
from ..base import BaseIntegrationImpl
from . import IntegrationType

# Import all external integrations
from .jira import JiraIntegration, JiraIssue, JiraComment, JiraWorklog, JiraSprint, JiraProject, JiraField, JiraAPIError, JiraRateLimitError
from .servicenow import (
    ServiceNowIntegration,
    ServiceNowIncident,
    ServiceNowRequest,
    ServiceNowUser,
    ServiceNowGroup,
    ServiceNowCatalogItem,
    ServiceNowAttachment,
    ServiceNowAPIError,
    ServiceNowRateLimitError
)
from .zendesk import (
    ZendeskIntegration,
    ZendeskTicket,
    ZendeskUser,
    ZendeskOrganization,
    ZendeskComment,
    ZendeskView,
    ZendeskMacro,
    ZendeskAPIError,
    ZendeskRateLimitError
)

# Integration registry
INTEGRATION_REGISTRY: Dict[IntegrationType, Type[BaseIntegrationImpl]] = {
    IntegrationType.JIRA: JiraIntegration,
    IntegrationType.SERVICENOW: ServiceNowIntegration,
    IntegrationType.ZENDESK: ZendeskIntegration,
}


# Export all public symbols
__all__ = [
    # Integration types
    "IntegrationType",
    
    # Jira integration
    "JiraIntegration",
    "JiraIssue",
    "JiraComment",
    "JiraWorklog",
    "JiraSprint",
    "JiraProject",
    "JiraField",
    "JiraAPIError",
    "JiraRateLimitError",
    
    # ServiceNow integration
    "ServiceNowIntegration",
    "ServiceNowIncident",
    "ServiceNowRequest",
    "ServiceNowUser",
    "ServiceNowGroup",
    "ServiceNowCatalogItem",
    "ServiceNowAttachment",
    "ServiceNowAPIError",
    "ServiceNowRateLimitError",
    
    # Zendesk integration
    "ZendeskIntegration",
    "ZendeskTicket",
    "ZendeskUser",
    "ZendeskOrganization",
    "ZendeskComment",
    "ZendeskView",
    "ZendeskMacro",
    "ZendeskAPIError",
    "ZendeskRateLimitError",
    
    # Registry
    "INTEGRATION_REGISTRY",
]