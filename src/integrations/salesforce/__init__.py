"""
Salesforce Service Cloud integration module.

Provides comprehensive Salesforce integration including:
- REST API client with OAuth 2.0 JWT bearer flow
- Service Cloud case management
- Bi-directional synchronization engine
- Bulk API 2.0 support
- Platform Events integration
- Omni-Channel support
- Governor limit monitoring
"""

from __future__ import annotations

# Import Salesforce client
from .client import SalesforceClient

# Import Service Cloud integration
from .service_cloud import ServiceCloudIntegration as SalesforceServiceCloud

# Import Salesforce models
from .models import (
    SalesforceCase,
    SalesforceContact,
    SalesforceAccount,
    SalesforceCaseComment,
    SalesforceKnowledgeArticle,
    SalesforceCaseStatus,
    SalesforceCasePriority,
    SalesforceCaseOrigin
)

# Import sync engine
from .sync import SalesforceSyncEngine, SyncDirection, ConflictResolutionStrategy

# Export main components
__all__ = [
    # Client
    "SalesforceClient",
    
    # Service Cloud
    "SalesforceServiceCloud",
    
    # Models
    "SalesforceCase",
    "SalesforceContact", 
    "SalesforceAccount",
    "SalesforceCaseComment",
    "SalesforceKnowledgeArticle",
    "SalesforceCaseStatus",
    "SalesforceCasePriority", 
    "SalesforceCaseOrigin",
    
    # Sync Engine
    "SalesforceSyncEngine",
    "SyncDirection",
    "ConflictResolutionStrategy"
]