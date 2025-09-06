"""
Salesforce object models and field mapping schemas.

Provides Pydantic models for Salesforce objects with:
- Type-safe field definitions
- Validation rules
- Data transformation logic
- Sync state tracking
- Field mapping configuration
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, validator


# Salesforce Case Enums

class SalesforceCaseStatus(str, Enum):
    """Salesforce Case status values."""
    NEW = "New"
    WORKING = "Working"
    ESCALATED = "Escalated"
    CLOSED = "Closed"


class SalesforceCasePriority(str, Enum):
    """Salesforce Case priority values."""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class SalesforceCaseOrigin(str, Enum):
    """Salesforce Case origin values."""
    WEB = "Web"
    EMAIL = "Email"
    PHONE = "Phone"
    CHAT = "Chat"
    FACEBOOK = "Facebook"
    TWITTER = "Twitter"
    COMMUNITIES = "Communities"


class SalesforceCaseType(str, Enum):
    """Salesforce Case type values."""
    TECHNICAL_SUPPORT = "Technical Support"
    ACCOUNT_MANAGEMENT = "Account Management"
    BILLING_INQUIRY = "Billing Inquiry"
    GENERAL_QUESTION = "General Question"
    ESCALATION_REQUEST = "Escalation Request"


class SalesforceCaseReason(str, Enum):
    """Salesforce Case reason values."""
    COMPLEX_TECHNICAL_ISSUE = "Complex Technical Issue"
    BILLING_DISPUTE = "Billing Dispute"
    ACCOUNT_ACCESS_ISSUE = "Account Access Issue"
    PRODUCT_FEATURE_REQUEST = "Product Feature Request"
    SERVICE_OUTAGE = "Service Outage"


# Omni-Channel Enums

class SalesforceOmniChannelStatus(str, Enum):
    """Omni-Channel status values."""
    ONLINE = "Online"
    AWAY = "Away"
    OFFLINE = "Offline"


class SalesforceOmniChannelPresenceStatus(str, Enum):
    """Omni-Channel presence status values."""
    AVAILABLE = "Available"
    BUSY = "Busy"
    AWAY = "Away"
    OFFLINE = "Offline"


# Knowledge Base Enums

class SalesforceKnowledgeArticleStatus(str, Enum):
    """Knowledge article status values."""
    DRAFT = "Draft"
    PUBLISHED = "Published"
    ARCHIVED = "Archived"


# Live Agent Enums

class SalesforceLiveAgentStatus(str, Enum):
    """Live Agent status values."""
    WAITING = "Waiting"
    CHATTING = "Chatting"
    ENDED = "Ended"


# Base Models

class BaseSalesforceModel(BaseModel):
    """Base model for all Salesforce objects."""
    
    id: Optional[str] = Field(default=None, description="Salesforce 18-character ID")
    organization_id: UUID = Field(description="Local organization ID for multi-tenancy")
    created_date: Optional[datetime] = Field(default=None, description="Record creation date")
    last_modified_date: Optional[datetime] = Field(default=None, description="Last modification date")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
            UUID: lambda v: str(v)
        }


# Case Models

class SalesforceCase(BaseSalesforceModel):
    """Salesforce Case object model."""
    
    case_number: Optional[str] = Field(default=None, description="Auto-generated case number")
    subject: str = Field(description="Case subject/title")
    description: str = Field(description="Case description")
    status: SalesforceCaseStatus = Field(default=SalesforceCaseStatus.NEW, description="Case status")
    priority: SalesforceCasePriority = Field(default=SalesforceCasePriority.MEDIUM, description="Case priority")
    origin: SalesforceCaseOrigin = Field(default=SalesforceCaseOrigin.WEB, description="Case origin")
    type: Optional[SalesforceCaseType] = Field(default=None, description="Case type")
    reason: Optional[SalesforceCaseReason] = Field(default=None, description="Case reason")
    contact_id: Optional[str] = Field(default=None, description="Related Contact ID")
    account_id: Optional[str] = Field(default=None, description="Related Account ID")
    
    # AI-specific fields
    ai_confidence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="AI confidence score")
    ai_intent_classified: Optional[str] = Field(default=None, description="AI classified intent")
    ai_sentiment_analysis: Optional[str] = Field(default=None, description="AI sentiment analysis")
    ai_source_system: Optional[str] = Field(default=None, description="AI source system")
    ai_conversation_id: Optional[str] = Field(default=None, description="AI conversation ID")
    
    @validator("ai_confidence_score")
    def validate_confidence_score(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (v < 0.0 or v > 1.0):
            raise ValueError("AI confidence score must be between 0.0 and 1.0")
        return v


class SalesforceCaseComment(BaseSalesforceModel):
    """Salesforce Case Comment object model."""
    
    case_id: str = Field(description="Parent Case ID")
    comment: str = Field(description="Comment text")
    is_public: bool = Field(default=False, description="Whether comment is public")
    created_by_id: Optional[str] = Field(default=None, description="User ID who created the comment")
    
    @validator("comment")
    def validate_comment(cls, v: str) -> str:
        if len(v) > 4000:
            raise ValueError("Comment cannot exceed 4000 characters")
        return v


# Contact Models

class SalesforceContact(BaseSalesforceModel):
    """Salesforce Contact object model."""
    
    first_name: Optional[str] = Field(default=None, max_length=40, description="First name")
    last_name: str = Field(max_length=80, description="Last name")
    email: Optional[str] = Field(default=None, description="Email address")
    phone: Optional[str] = Field(default=None, description="Phone number")
    mobile_phone: Optional[str] = Field(default=None, description="Mobile phone number")
    title: Optional[str] = Field(default=None, max_length=128, description="Job title")
    department: Optional[str] = Field(default=None, max_length=80, description="Department")
    account_id: Optional[str] = Field(default=None, description="Related Account ID")
    
    @validator("email")
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v and "@" not in v:
            raise ValueError("Invalid email format")
        return v
    
    @validator("phone", "mobile_phone")
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v and len(v) > 40:
            raise ValueError("Phone number cannot exceed 40 characters")
        return v


# Account Models

class SalesforceAccount(BaseSalesforceModel):
    """Salesforce Account object model."""
    
    name: str = Field(max_length=255, description="Account name")
    type: Optional[str] = Field(default=None, description="Account type")
    industry: Optional[str] = Field(default=None, description="Industry")
    annual_revenue: Optional[float] = Field(default=None, ge=0, description="Annual revenue")
    number_of_employees: Optional[int] = Field(default=None, ge=0, description="Number of employees")
    billing_address: Optional[Dict[str, str]] = Field(default=None, description="Billing address")
    shipping_address: Optional[Dict[str, str]] = Field(default=None, description="Shipping address")
    
    @validator("annual_revenue")
    def validate_revenue(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("Annual revenue cannot be negative")
        return v
    
    @validator("number_of_employees")
    def validate_employees(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("Number of employees cannot be negative")
        return v


# Omni-Channel Models

class SalesforceAgentWork(BaseSalesforceModel):
    """Salesforce Agent Work (Omni-Channel) object model."""
    
    user_id: str = Field(description="User ID of the agent")
    case_id: Optional[str] = Field(default=None, description="Related Case ID")
    status: SalesforceOmniChannelPresenceStatus = Field(description="Agent presence status")
    capacity_weight: int = Field(default=1, ge=1, le=10, description="Capacity weight")
    is_active: bool = Field(default=True, description="Whether agent work is active")
    
    @validator("capacity_weight")
    def validate_capacity(cls, v: int) -> int:
        if v < 1 or v > 10:
            raise ValueError("Capacity weight must be between 1 and 10")
        return v


# Knowledge Base Models

class SalesforceKnowledgeArticle(BaseSalesforceModel):
    """Salesforce Knowledge Article object model."""
    
    title: str = Field(max_length=255, description="Article title")
    summary: Optional[str] = Field(default=None, max_length=1000, description="Article summary")
    url_name: str = Field(description="URL name for the article")
    article_type: str = Field(description="Article type")
    language: str = Field(default="en-US", description="Article language")
    article_number: Optional[str] = Field(default=None, description="Article number")
    last_published_date: Optional[datetime] = Field(default=None, description="Last published date")
    content: Optional[str] = Field(default=None, description="Article content")
    type_details: Optional[Dict[str, Any]] = Field(default=None, description="Type-specific details")
    
    @validator("language")
    def validate_language(cls, v: str) -> str:
        if len(v) != 5 or "-" not in v:
            raise ValueError("Language must be in format 'xx-XX'")
        return v


# Live Agent Models

class SalesforceLiveAgentSession(BaseSalesforceModel):
    """Salesforce Live Agent Session object model."""
    
    deployment_id: str = Field(description="Live Agent deployment ID")
    visitor_name: str = Field(description="Visitor name")
    visitor_email: Optional[str] = Field(default=None, description="Visitor email")
    status: SalesforceLiveAgentStatus = Field(default=SalesforceLiveAgentStatus.WAITING, description="Session status")
    session_start_date: datetime = Field(description="Session start date")
    session_end_date: Optional[datetime] = Field(default=None, description="Session end date")
    
    @validator("visitor_email")
    def validate_visitor_email(cls, v: Optional[str]) -> Optional[str]:
        if v and "@" not in v:
            raise ValueError("Invalid visitor email format")
        return v


# Sync Models

class SalesforceSyncState(BaseModel):
    """Salesforce synchronization state tracking."""
    
    local_id: str = Field(description="Local system ID")
    salesforce_id: str = Field(description="Salesforce 18-character ID")
    object_type: str = Field(description="Salesforce object type")
    sync_direction: str = Field(description="Sync direction (inbound/outbound/bidirectional)")
    last_sync_date: datetime = Field(description="Last successful sync date")
    local_modified_date: datetime = Field(description="Local last modified date")
    remote_modified_date: datetime = Field(description="Remote last modified date")
    sync_status: str = Field(description="Sync status (synced/pending/failed/conflict)")
    conflict_resolution: str = Field(description="Conflict resolution strategy used")
    error_message: Optional[str] = Field(default=None, description="Error message if sync failed")
    retry_count: int = Field(default=0, ge=0, description="Number of retry attempts")
    
    @validator("sync_status")
    def validate_sync_status(cls, v: str) -> str:
        allowed_statuses = ["synced", "pending", "failed", "conflict"]
        if v not in allowed_statuses:
            raise ValueError(f"Sync status must be one of: {allowed_statuses}")
        return v
    
    @validator("conflict_resolution")
    def validate_conflict_resolution(cls, v: str) -> str:
        allowed_strategies = ["last_write_wins", "merge", "manual", "source_wins", "target_wins"]
        if v not in allowed_strategies:
            raise ValueError(f"Conflict resolution must be one of: {allowed_strategies}")
        return v


class SalesforceFieldMapping(BaseModel):
    """Salesforce field mapping configuration."""
    
    local_field: str = Field(description="Local system field name")
    salesforce_field: str = Field(description="Salesforce field name")
    field_type: str = Field(description="Field data type")
    is_required: bool = Field(default=False, description="Whether field is required")
    transformation_rule: Optional[str] = Field(default=None, description="Data transformation rule")
    validation_rule: Optional[str] = Field(default=None, description="Field validation rule")
    
    @validator("field_type")
    def validate_field_type(cls, v: str) -> str:
        allowed_types = ["string", "integer", "float", "boolean", "datetime", "email", "phone", "url"]
        if v not in allowed_types:
            raise ValueError(f"Field type must be one of: {allowed_types}")
        return v


class SalesforceObjectMapping(BaseModel):
    """Salesforce object mapping configuration."""
    
    local_object_type: str = Field(description="Local object type")
    salesforce_object_type: str = Field(description="Salesforce object type")
    field_mappings: List[SalesforceFieldMapping] = Field(description="Field mappings")
    sync_direction: str = Field(description="Synchronization direction")
    conflict_resolution: str = Field(description="Conflict resolution strategy")
    is_enabled: bool = Field(default=True, description="Whether mapping is enabled")
    
    @validator("sync_direction")
    def validate_sync_direction(cls, v: str) -> str:
        allowed_directions = ["inbound", "outbound", "bidirectional"]
        if v not in allowed_directions:
            raise ValueError(f"Sync direction must be one of: {allowed_directions}")
        return v


# Response Models

class SalesforceAPIResponse(BaseModel):
    """Base Salesforce API response."""
    
    success: bool = Field(description="Whether the operation was successful")
    id: Optional[str] = Field(default=None, description="Salesforce ID if applicable")
    errors: List[str] = Field(default_factory=list, description="Error messages")
    warnings: List[str] = Field(default_factory=list, description="Warning messages")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class SalesforceBulkOperationResponse(BaseModel):
    """Salesforce bulk operation response."""
    
    job_id: str = Field(description="Bulk job ID")
    state: str = Field(description="Job state")
    records_processed: int = Field(default=0, description="Number of records processed")
    records_failed: int = Field(default=0, description="Number of records failed")
    total_processing_time_seconds: float = Field(default=0.0, description="Total processing time")
    api_version: str = Field(description="Salesforce API version used")
    
    @validator("state")
    def validate_state(cls, v: str) -> str:
        allowed_states = ["Open", "UploadComplete", "InProgress", "JobComplete", "Failed", "Aborted"]
        if v not in allowed_states:
            raise ValueError(f"Job state must be one of: {allowed_states}")
        return v


# Utility Functions

def validate_salesforce_id(salesforce_id: str) -> bool:
    """Validate Salesforce 18-character ID format."""
    if len(salesforce_id) != 18:
        return False
    
    # Check if it's alphanumeric
    if not salesforce_id.isalnum():
        return False
    
    # Basic checksum validation (simplified)
    try:
        # Salesforce IDs have a checksum in the last 3 characters
        # This is a simplified validation
        return True
    except:
        return False


def convert_to_salesforce_id(local_id: str) -> str:
    """Convert local UUID to Salesforce-compatible ID format."""
    # Remove hyphens and take first 15 characters
    clean_id = local_id.replace("-", "")[:15]
    
    # Add checksum characters (simplified implementation)
    # In a real implementation, this would use Salesforce's ID encoding
    checksum = "ABC"  # Placeholder checksum
    
    return clean_id + checksum


def map_local_to_salesforce(local_data: Dict[str, Any], field_mapping: Dict[str, str]) -> Dict[str, Any]:
    """Map local data to Salesforce format using field mapping."""
    salesforce_data = {}
    
    for local_field, salesforce_field in field_mapping.items():
        if local_field in local_data:
            salesforce_data[salesforce_field] = local_data[local_field]
    
    return salesforce_data


def map_salesforce_to_local(salesforce_data: Dict[str, Any], field_mapping: Dict[str, str]) -> Dict[str, Any]:
    """Map Salesforce data to local format using field mapping."""
    local_data = {}
    
    for local_field, salesforce_field in field_mapping.items():
        if salesforce_field in salesforce_data:
            local_data[local_field] = salesforce_data[salesforce_field]
    
    return local_data


# Export all models
__all__ = [
    # Enums
    "SalesforceCaseStatus",
    "SalesforceCasePriority",
    "SalesforceCaseOrigin",
    "SalesforceCaseType",
    "SalesforceCaseReason",
    "SalesforceOmniChannelStatus",
    "SalesforceOmniChannelPresenceStatus",
    "SalesforceKnowledgeArticleStatus",
    "SalesforceLiveAgentStatus",
    
    # Models
    "BaseSalesforceModel",
    "SalesforceCase",
    "SalesforceCaseComment",
    "SalesforceContact",
    "SalesforceAccount",
    "SalesforceAgentWork",
    "SalesforceKnowledgeArticle",
    "SalesforceLiveAgentSession",
    "SalesforceSyncState",
    "SalesforceFieldMapping",
    "SalesforceObjectMapping",
    "SalesforceAPIResponse",
    "SalesforceBulkOperationResponse",
    
    # Utility Functions
    "validate_salesforce_id",
    "convert_to_salesforce_id",
    "map_local_to_salesforce",
    "map_salesforce_to_local",
]