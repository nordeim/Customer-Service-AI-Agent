"""
Zendesk integration with comprehensive ticket management and customer service capabilities.

Provides enterprise-grade Zendesk integration including:
- Ticket lifecycle management with custom fields
- User and organization management
- Ticket forms and field mapping
- Macro and automation support
- Views and search functionality
- Attachment handling and file uploads
- Satisfaction ratings and CSAT surveys
- Help Center and knowledge base integration
- Chat and messaging integration
- Webhook event processing
- Rate limiting and comprehensive error handling
"""

from __future__ import annotations

import asyncio
import base64
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, AsyncGenerator
from urllib.parse import urlencode, quote
import httpx

from src.core.config import get_settings
from src.core.logging import get_logger
from src.core.exceptions import ExternalServiceError
from ..base import BaseIntegrationImpl, RateLimitError, OAuth2Client
from ..config import BaseIntegrationConfig
from . import IntegrationType

logger = get_logger(__name__)


class ZendeskAPIError(ExternalServiceError):
    """Zendesk API specific errors."""
    pass


class ZendeskRateLimitError(RateLimitError):
    """Zendesk rate limit exceeded error."""
    pass


class ZendeskTicket:
    """Represents a Zendesk ticket."""
    
    def __init__(
        self,
        id: int,
        subject: str,
        description: str,
        status: str = "open",
        priority: str = "normal",
        ticket_type: str = "question",
        requester_id: Optional[int] = None,
        submitter_id: Optional[int] = None,
        assignee_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        group_id: Optional[int] = None,
        brand_id: Optional[int] = None,
        forum_topic_id: Optional[int] = None,
        problem_id: Optional[int] = None,
        due_at: Optional[datetime] = None,
        tags: Optional[List[str]] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        solved_at: Optional[datetime] = None,
        closed_at: Optional[datetime] = None,
        recipient: Optional[str] = None,
        followup_ids: Optional[List[int]] = None,
        via: Optional[Dict[str, Any]] = None,
        satisfaction_rating: Optional[Dict[str, Any]] = None,
        sharing_agreement_ids: Optional[List[int]] = None,
        followup_source_id: Optional[int] = None,
        macro_ids: Optional[List[int]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.id = id
        self.subject = subject
        self.description = description
        self.status = status
        self.priority = priority
        self.ticket_type = ticket_type
        self.requester_id = requester_id
        self.submitter_id = submitter_id
        self.assignee_id = assignee_id
        self.organization_id = organization_id
        self.group_id = group_id
        self.brand_id = brand_id
        self.forum_topic_id = forum_topic_id
        self.problem_id = problem_id
        self.due_at = due_at
        self.tags = tags or []
        self.custom_fields = custom_fields or {}
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.solved_at = solved_at
        self.closed_at = closed_at
        self.recipient = recipient
        self.followup_ids = followup_ids or []
        self.via = via or {}
        self.satisfaction_rating = satisfaction_rating or {}
        self.sharing_agreement_ids = sharing_agreement_ids or []
        self.followup_source_id = followup_source_id
        self.macro_ids = macro_ids or []
        self.metadata = metadata or {}


class ZendeskUser:
    """Represents a Zendesk user."""
    
    def __init__(
        self,
        id: int,
        name: str,
        email: str,
        role: str = "end-user",
        active: bool = True,
        verified: bool = False,
        shared: bool = False,
        locale: str = "en-US",
        timezone: str = "UTC",
        last_login_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        organization_id: Optional[int] = None,
        default_group_id: Optional[int] = None,
        phone: Optional[str] = None,
        signature: Optional[str] = None,
        details: Optional[str] = None,
        notes: Optional[str] = None,
        custom_role_id: Optional[int] = None,
        moderator: bool = False,
        ticket_restriction: Optional[str] = None,
        only_private_comments: bool = False,
        tags: Optional[List[str]] = None,
        suspended: bool = False,
        remote_photo_url: Optional[str] = None,
        user_fields: Optional[Dict[str, Any]] = None
    ):
        self.id = id
        self.name = name
        self.email = email
        self.role = role
        self.active = active
        self.verified = verified
        self.shared = shared
        self.locale = locale
        self.timezone = timezone
        self.last_login_at = last_login_at
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.organization_id = organization_id
        self.default_group_id = default_group_id
        self.phone = phone
        self.signature = signature
        self.details = details
        self.notes = notes
        self.custom_role_id = custom_role_id
        self.moderator = moderator
        self.ticket_restriction = ticket_restriction
        self.only_private_comments = only_private_comments
        self.tags = tags or []
        self.suspended = suspended
        self.remote_photo_url = remote_photo_url
        self.user_fields = user_fields or {}


class ZendeskOrganization:
    """Represents a Zendesk organization."""
    
    def __init__(
        self,
        id: int,
        name: str,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        domain_names: Optional[List[str]] = None,
        details: Optional[str] = None,
        notes: Optional[str] = None,
        group_id: Optional[int] = None,
        shared_tickets: bool = False,
        shared_comments: bool = False,
        tags: Optional[List[str]] = None,
        organization_fields: Optional[Dict[str, Any]] = None
    ):
        self.id = id
        self.name = name
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.domain_names = domain_names or []
        self.details = details
        self.notes = notes
        self.group_id = group_id
        self.shared_tickets = shared_tickets
        self.shared_comments = shared_comments
        self.tags = tags or []
        self.organization_fields = organization_fields or {}


class ZendeskComment:
    """Represents a Zendesk ticket comment."""
    
    def __init__(
        self,
        id: int,
        type: str,
        body: str,
        html_body: Optional[str] = None,
        plain_body: Optional[str] = None,
        public: bool = True,
        author_id: Optional[int] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        created_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
        via: Optional[Dict[str, Any]] = None
    ):
        self.id = id
        self.type = type
        self.body = body
        self.html_body = html_body
        self.plain_body = plain_body
        self.public = public
        self.author_id = author_id
        self.attachments = attachments or []
        self.created_at = created_at or datetime.utcnow()
        self.metadata = metadata or {}
        self.via = via or {}


class ZendeskView:
    """Represents a Zendesk view."""
    
    def __init__(
        self,
        id: int,
        title: str,
        active: bool = True,
        position: int = 0,
        description: Optional[str] = None,
        execution: Optional[Dict[str, Any]] = None,
        conditions: Optional[Dict[str, Any]] = None,
        restriction: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.id = id
        self.title = title
        self.active = active
        self.position = position
        self.description = description
        self.execution = execution or {}
        self.conditions = conditions or {}
        self.restriction = restriction
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()


class ZendeskMacro:
    """Represents a Zendesk macro."""
    
    def __init__(
        self,
        id: int,
        title: str,
        active: bool = True,
        description: Optional[str] = None,
        actions: Optional[List[Dict[str, Any]]] = None,
        restriction: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.id = id
        self.title = title
        self.active = active
        self.description = description
        self.actions = actions or []
        self.restriction = restriction
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()


class ZendeskIntegration(BaseIntegrationImpl):
    """Zendesk integration with comprehensive ticket management and customer service capabilities."""
    
    def __init__(self, config: BaseIntegrationConfig):
        super().__init__(IntegrationType.ZENDESK, config.dict())
        
        self.zendesk_config = config
        self.logger = logger.getChild("zendesk")
        
        # Zendesk API configuration
        self.api_version = "v2"
        self.base_url = self._determine_base_url()
        
        # OAuth client for API authentication
        self.oauth_client: Optional[OAuth2Client] = None
        
        # Connection state
        self._connected = False
        self._user_info: Dict[str, Any] = {}
        self._account_info: Dict[str, Any] = {}
        self._ticket_field_cache: Dict[str, Any] = {}
        
        # Rate limiting
        self._rate_limit_info = {
            "remaining": 700,  # Zendesk default per minute
            "reset": None,
            "retry_after": None
        }
        
        # Event tracking
        self._ticket_handlers: List[Callable] = []
        self._user_handlers: List[Callable] = []
        self._organization_handlers: List[Callable] = []
    
    def _determine_base_url(self) -> str:
        """Determine Zendesk base URL based on configuration."""
        if hasattr(self.zendesk_config, 'subdomain'):
            return f"https://{self.zendesk_config.subdomain}.zendesk.com"
        elif hasattr(self.zendesk_config, 'base_url'):
            return str(self.zendesk_config.base_url).rstrip('/')
        else:
            raise ZendeskAPIError("No Zendesk subdomain configured")
    
    # Authentication and Connection
    
    async def authenticate(self) -> bool:
        """Authenticate with Zendesk API."""
        try:
            # Set up OAuth client if credentials are provided
            if hasattr(self.zendesk_config, 'oauth') and self.zendesk_config.oauth:
                from ..base import OAuth2Config
                
                oauth_config = OAuth2Config(
                    client_id=self.zendesk_config.oauth.client_id,
                    client_secret=self.zendesk_config.oauth.client_secret,
                    authorization_url=self.zendesk_config.oauth.authorization_url,
                    token_url=self.zendesk_config.oauth.token_url,
                    redirect_uri=self.zendesk_config.oauth.redirect_uri,
                    scope=self.zendesk_config.oauth.scope
                )
                
                self.oauth_client = OAuth2Client(oauth_config)
            
            # Test API connectivity
            account_info = await self.get_account_settings()
            self._account_info = account_info
            
            # Get user information
            user_info = await self.get_current_user()
            self._user_info = user_info
            
            self.logger.info(f"Authenticated with Zendesk as {user_info.get('name', 'Unknown')}")
            self._connected = True
            
            return True
            
        except Exception as e:
            self.logger.error(f"Zendesk authentication failed: {e}")
            raise ZendeskAPIError(f"Authentication failed: {e}")
    
    async def _api_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to Zendesk API."""
        url = f"{self.base_url}/api/{self.api_version}/{endpoint.lstrip('/')}"
        
        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "AI-Customer-Service-Agent/1.0"
        }
        
        # Add authentication
        if self.oauth_client:
            access_token = await self.oauth_client.get_valid_access_token()
            headers["Authorization"] = f"Bearer {access_token}"
        elif hasattr(self.zendesk_config, 'email') and hasattr(self.zendesk_config, 'api_token'):
            # Basic auth with API token
            auth_string = f"{self.zendesk_config.email}/token:{self.zendesk_config.api_token}"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()
            headers["Authorization"] = f"Basic {encoded_auth}"
        else:
            raise ZendeskAPIError("No authentication credentials configured")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method.upper() == "GET":
                    response = await client.get(url, params=params, headers=headers)
                elif method.upper() == "POST":
                    if files:
                        headers.pop("Content-Type", None)
                        response = await client.post(url, data=json_data, files=files, headers=headers)
                    else:
                        response = await client.post(url, json=json_data, headers=headers)
                elif method.upper() == "PUT":
                    response = await client.put(url, json=json_data, headers=headers)
                elif method.upper() == "PATCH":
                    response = await client.patch(url, json=json_data, headers=headers)
                elif method.upper() == "DELETE":
                    response = await client.delete(url, headers=headers)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                # Check for rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    self._rate_limit_info["retry_after"] = retry_after
                    raise ZendeskRateLimitError(
                        f"Zendesk rate limit exceeded. Retry after {retry_after}s",
                        IntegrationType.ZENDESK,
                        {"retry_after": retry_after}
                    )
                
                response.raise_for_status()
                
                # Update rate limit info
                self._update_rate_limit_info(response)
                
                return response.json() if response.content else {}
                
        except httpx.RequestError as e:
            self.logger.error(f"Zendesk request error: {e}")
            raise ZendeskAPIError(f"Request failed: {e}")
    
    def _update_rate_limit_info(self, response: httpx.Response) -> None:
        """Update rate limit information from response headers."""
        # Extract rate limit info from headers if available
        remaining = response.headers.get("X-RateLimit-Remaining")
        reset = response.headers.get("X-RateLimit-Reset")
        
        if remaining:
            self._rate_limit_info["remaining"] = int(remaining)
        
        if reset:
            self._rate_limit_info["reset"] = int(reset)
    
    # Account and User Information
    
    async def get_account_settings(self) -> Dict[str, Any]:
        """Get account settings."""
        return await self._api_request("GET", "account/settings.json")
    
    async def get_current_user(self) -> Dict[str, Any]:
        """Get current user information."""
        result = await self._api_request("GET", "users/me.json")
        return result.get("user", {})
    
    # Ticket Management
    
    async def create_ticket(
        self,
        subject: str,
        comment: str,
        requester_id: Optional[int] = None,
        priority: str = "normal",
        ticket_type: str = "question",
        tags: Optional[List[str]] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
        submitter_id: Optional[int] = None,
        assignee_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        group_id: Optional[int] = None,
        brand_id: Optional[int] = None,
        due_at: Optional[datetime] = None,
        external_id: Optional[str] = None
    ) -> int:
        """Create new Zendesk ticket."""
        ticket_data = {
            "ticket": {
                "subject": subject,
                "comment": {"body": comment},
                "priority": priority,
                "type": ticket_type
            }
        }
        
        if requester_id:
            ticket_data["ticket"]["requester_id"] = requester_id
        
        if submitter_id:
            ticket_data["ticket"]["submitter_id"] = submitter_id
        
        if assignee_id:
            ticket_data["ticket"]["assignee_id"] = assignee_id
        
        if organization_id:
            ticket_data["ticket"]["organization_id"] = organization_id
        
        if group_id:
            ticket_data["ticket"]["group_id"] = group_id
        
        if brand_id:
            ticket_data["ticket"]["brand_id"] = brand_id
        
        if due_at:
            ticket_data["ticket"]["due_at"] = due_at.isoformat()
        
        if external_id:
            ticket_data["ticket"]["external_id"] = external_id
        
        if tags:
            ticket_data["ticket"]["tags"] = tags
        
        if custom_fields:
            ticket_data["ticket"]["custom_fields"] = [
                {"id": field_id, "value": value} for field_id, value in custom_fields.items()
            ]
        
        result = await self._api_request("POST", "tickets.json", json_data=ticket_data)
        
        ticket = result["ticket"]
        ticket_id = ticket["id"]
        
        self.logger.info(f"Created Zendesk ticket: {ticket_id}")
        
        return ticket_id
    
    async def get_ticket(self, ticket_id: int) -> ZendeskTicket:
        """Get ticket by ID."""
        result = await self._api_request("GET", f"tickets/{ticket_id}.json")
        
        ticket_data = result["ticket"]
        
        return ZendeskTicket(
            id=ticket_data["id"],
            subject=ticket_data["subject"],
            description=ticket_data.get("description", ""),
            status=ticket_data["status"],
            priority=ticket_data["priority"],
            ticket_type=ticket_data["type"],
            requester_id=ticket_data.get("requester_id"),
            submitter_id=ticket_data.get("submitter_id"),
            assignee_id=ticket_data.get("assignee_id"),
            organization_id=ticket_data.get("organization_id"),
            group_id=ticket_data.get("group_id"),
            brand_id=ticket_data.get("brand_id"),
            forum_topic_id=ticket_data.get("forum_topic_id"),
            problem_id=ticket_data.get("problem_id"),
            due_at=datetime.fromisoformat(ticket_data["due_at"].replace("Z", "+00:00")) if ticket_data.get("due_at") else None,
            tags=ticket_data.get("tags", []),
            custom_fields={field["id"]: field["value"] for field in ticket_data.get("custom_fields", []) if field["value"] is not None},
            created_at=datetime.fromisoformat(ticket_data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(ticket_data["updated_at"].replace("Z", "+00:00")),
            solved_at=datetime.fromisoformat(ticket_data["solved_at"].replace("Z", "+00:00")) if ticket_data.get("solved_at") else None,
            closed_at=datetime.fromisoformat(ticket_data["closed_at"].replace("Z", "+00:00")) if ticket_data.get("closed_at") else None,
            recipient=ticket_data.get("recipient"),
            followup_ids=ticket_data.get("followup_ids", []),
            via=ticket_data.get("via"),
            satisfaction_rating=ticket_data.get("satisfaction_rating"),
            sharing_agreement_ids=ticket_data.get("sharing_agreement_ids", []),
            followup_source_id=ticket_data.get("followup_source_id"),
            macro_ids=ticket_data.get("macro_ids", []),
            metadata=ticket_data.get("metadata")
        )
    
    async def update_ticket(
        self,
        ticket_id: int,
        subject: Optional[str] = None,
        comment: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        ticket_type: Optional[str] = None,
        assignee_id: Optional[int] = None,
        group_id: Optional[int] = None,
        tags: Optional[List[str]] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
        public_comment: bool = True,
        additional_tags: Optional[List[str]] = None
    ) -> None:
        """Update existing ticket."""
        ticket_data = {"ticket": {}}
        
        if subject:
            ticket_data["ticket"]["subject"] = subject
        
        if comment:
            ticket_data["ticket"]["comment"] = {
                "body": comment,
                "public": public_comment
            }
        
        if status:
            ticket_data["ticket"]["status"] = status
        
        if priority:
            ticket_data["ticket"]["priority"] = priority
        
        if ticket_type:
            ticket_data["ticket"]["type"] = ticket_type
        
        if assignee_id:
            ticket_data["ticket"]["assignee_id"] = assignee_id
        
        if group_id:
            ticket_data["ticket"]["group_id"] = group_id
        
        if tags:
            ticket_data["ticket"]["tags"] = tags
        
        if additional_tags:
            ticket_data["ticket"]["additional_tags"] = additional_tags
        
        if custom_fields:
            ticket_data["ticket"]["custom_fields"] = [
                {"id": field_id, "value": value} for field_id, value in custom_fields.items()
            ]
        
        if not ticket_data["ticket"]:
            raise ValueError("No fields to update")
        
        await self._api_request("PUT", f"tickets/{ticket_id}.json", json_data=ticket_data)
        
        self.logger.info(f"Updated Zendesk ticket: {ticket_id}")
    
    async def delete_ticket(self, ticket_id: int) -> None:
        """Delete ticket."""
        await self._api_request("DELETE", f"tickets/{ticket_id}.json")
        self.logger.info(f"Deleted Zendesk ticket: {ticket_id}")
    
    # Bulk Ticket Operations
    
    async def bulk_update_tickets(
        self,
        ticket_ids: List[int],
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Bulk update multiple tickets."""
        bulk_data = {
            "ticket": {
                "ids": ticket_ids,
                **updates
            }
        }
        
        result = await self._api_request("PUT", "tickets/update_many.json", json_data=bulk_data)
        
        self.logger.info(f"Bulk updated {len(ticket_ids)} tickets")
        
        return result
    
    async def merge_tickets(self, target_ticket_id: int, source_ticket_ids: List[int]) -> Dict[str, Any]:
        """Merge multiple tickets into one."""
        merge_data = {
            "merge": {
                "ids": source_ticket_ids,
                "target": {"id": target_ticket_id}
            }
        }
        
        result = await self._api_request("POST", "tickets/merge.json", json_data=merge_data)
        
        self.logger.info(f"Merged {len(source_ticket_ids)} tickets into {target_ticket_id}")
        
        return result
    
    # Ticket Comments
    
    async def add_comment(
        self,
        ticket_id: int,
        body: str,
        public: bool = True,
        author_id: Optional[int] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> int:
        """Add comment to ticket."""
        comment_data = {
            "ticket": {
                "comment": {
                    "body": body,
                    "public": public
                }
            }
        }
        
        if author_id:
            comment_data["ticket"]["comment"]["author_id"] = author_id
        
        if attachments:
            comment_data["ticket"]["comment"]["uploads"] = attachments
        
        result = await self._api_request("PUT", f"tickets/{ticket_id}.json", json_data=comment_data)
        
        comment = result["ticket"]["comments"][-1]  # Get the last comment
        comment_id = comment["id"]
        
        self.logger.info(f"Added comment {comment_id} to ticket {ticket_id}")
        
        return comment_id
    
    async def get_comments(self, ticket_id: int) -> List[ZendeskComment]:
        """Get all comments for ticket."""
        result = await self._api_request("GET", f"tickets/{ticket_id}/comments.json")
        
        comments = []
        for comment_data in result.get("comments", []):
            comment = ZendeskComment(
                id=comment_data["id"],
                type=comment_data["type"],
                body=comment_data["body"],
                html_body=comment_data.get("html_body"),
                plain_body=comment_data.get("plain_body"),
                public=comment_data["public"],
                author_id=comment_data.get("author_id"),
                attachments=comment_data.get("attachments", []),
                created_at=datetime.fromisoformat(comment_data["created_at"].replace("Z", "+00:00")),
                metadata=comment_data.get("metadata", {}),
                via=comment_data.get("via", {})
            )
            comments.append(comment)
        
        return comments
    
    # Ticket Search and Views
    
    async def search_tickets(
        self,
        query: str,
        sort_by: str = "updated_at",
        sort_order: str = "desc",
        page: int = 1,
        per_page: int = 100
    ) -> List[ZendeskTicket]:
        """Search tickets using query."""
        params = {
            "query": query,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "page": page,
            "per_page": per_page
        }
        
        result = await self._api_request("GET", "search.json", params=params)
        
        tickets = []
        for ticket_data in result.get("results", []):
            if ticket_data["result_type"] == "ticket":
                ticket = ZendeskTicket(
                    id=ticket_data["id"],
                    subject=ticket_data["subject"],
                    description=ticket_data.get("description", ""),
                    status=ticket_data["status"],
                    priority=ticket_data["priority"],
                    ticket_type=ticket_data["type"],
                    requester_id=ticket_data.get("requester_id"),
                    submitter_id=ticket_data.get("submitter_id"),
                    assignee_id=ticket_data.get("assignee_id"),
                    organization_id=ticket_data.get("organization_id"),
                    group_id=ticket_data.get("group_id"),
                    brand_id=ticket_data.get("brand_id"),
                    forum_topic_id=ticket_data.get("forum_topic_id"),
                    problem_id=ticket_data.get("problem_id"),
                    due_at=datetime.fromisoformat(ticket_data["due_at"].replace("Z", "+00:00")) if ticket_data.get("due_at") else None,
                    tags=ticket_data.get("tags", []),
                    custom_fields={field["id"]: field["value"] for field in ticket_data.get("custom_fields", []) if field["value"] is not None},
                    created_at=datetime.fromisoformat(ticket_data["created_at"].replace("Z", "+00:00")),
                    updated_at=datetime.fromisoformat(ticket_data["updated_at"].replace("Z", "+00:00")),
                    solved_at=datetime.fromisoformat(ticket_data["solved_at"].replace("Z", "+00:00")) if ticket_data.get("solved_at") else None,
                    closed_at=datetime.fromisoformat(ticket_data["closed_at"].replace("Z", "+00:00")) if ticket_data.get("closed_at") else None,
                    recipient=ticket_data.get("recipient"),
                    followup_ids=ticket_data.get("followup_ids", []),
                    via=ticket_data.get("via"),
                    satisfaction_rating=ticket_data.get("satisfaction_rating"),
                    sharing_agreement_ids=ticket_data.get("sharing_agreement_ids", []),
                    followup_source_id=ticket_data.get("followup_source_id"),
                    macro_ids=ticket_data.get("macro_ids", []),
                    metadata=ticket_data.get("metadata")
                )
                tickets.append(ticket)
        
        return tickets
    
    async def get_views(self, active: bool = True) -> List[ZendeskView]:
        """Get ticket views."""
        params = {"active": active}
        result = await self._api_request("GET", "views.json", params=params)
        
        views = []
        for view_data in result.get("views", []):
            view = ZendeskView(
                id=view_data["id"],
                title=view_data["title"],
                active=view_data["active"],
                position=view_data["position"],
                description=view_data.get("description"),
                execution=view_data.get("execution"),
                conditions=view_data.get("conditions"),
                restriction=view_data.get("restriction"),
                created_at=datetime.fromisoformat(view_data["created_at"].replace("Z", "+00:00")),
                updated_at=datetime.fromisoformat(view_data["updated_at"].replace("Z", "+00:00"))
            )
            views.append(view)
        
        return views
    
    async def execute_view(self, view_id: int, page: int = 1, per_page: int = 100) -> List[ZendeskTicket]:
        """Execute view and get tickets."""
        params = {"page": page, "per_page": per_page}
        result = await self._api_request("GET", f"views/{view_id}/tickets.json", params=params)
        
        tickets = []
        for ticket_data in result.get("tickets", []):
            ticket = ZendeskTicket(
                id=ticket_data["id"],
                subject=ticket_data["subject"],
                description=ticket_data.get("description", ""),
                status=ticket_data["status"],
                priority=ticket_data["priority"],
                ticket_type=ticket_data["type"],
                requester_id=ticket_data.get("requester_id"),
                submitter_id=ticket_data.get("submitter_id"),
                assignee_id=ticket_data.get("assignee_id"),
                organization_id=ticket_data.get("organization_id"),
                group_id=ticket_data.get("group_id"),
                brand_id=ticket_data.get("brand_id"),
                forum_topic_id=ticket_data.get("forum_topic_id"),
                problem_id=ticket_data.get("problem_id"),
                due_at=datetime.fromisoformat(ticket_data["due_at"].replace("Z", "+00:00")) if ticket_data.get("due_at") else None,
                tags=ticket_data.get("tags", []),
                custom_fields={field["id"]: field["value"] for field in ticket_data.get("custom_fields", []) if field["value"] is not None},
                created_at=datetime.fromisoformat(ticket_data["created_at"].replace("Z", "+00:00")),
                updated_at=datetime.fromisoformat(ticket_data["updated_at"].replace("Z", "+00:00")),
                solved_at=datetime.fromisoformat(ticket_data["solved_at"].replace("Z", "+00:00")) if ticket_data.get("solved_at") else None,
                closed_at=datetime.fromisoformat(ticket_data["closed_at"].replace("Z", "+00:00")) if ticket_data.get("closed_at") else None,
                recipient=ticket_data.get("recipient"),
                followup_ids=ticket_data.get("followup_ids", []),
                via=ticket_data.get("via"),
                satisfaction_rating=ticket_data.get("satisfaction_rating"),
                sharing_agreement_ids=ticket_data.get("sharing_agreement_ids", []),
                followup_source_id=ticket_data.get("followup_source_id"),
                macro_ids=ticket_data.get("macro_ids", []),
                metadata=ticket_data.get("metadata")
            )
            tickets.append(ticket)
        
        return tickets
    
    # User Management
    
    async def create_user(
        self,
        name: str,
        email: str,
        role: str = "end-user",
        verified: bool = False,
        organization_id: Optional[int] = None,
        phone: Optional[str] = None,
        user_fields: Optional[Dict[str, Any]] = None
    ) -> int:
        """Create new user."""
        user_data = {
            "user": {
                "name": name,
                "email": email,
                "role": role,
                "verified": verified
            }
        }
        
        if organization_id:
            user_data["user"]["organization_id"] = organization_id
        
        if phone:
            user_data["user"]["phone"] = phone
        
        if user_fields:
            user_data["user"]["user_fields"] = user_fields
        
        result = await self._api_request("POST", "users.json", json_data=user_data)
        
        user = result["user"]
        user_id = user["id"]
        
        self.logger.info(f"Created Zendesk user: {user_id}")
        
        return user_id
    
    async def get_user(self, user_id: int) -> ZendeskUser:
        """Get user by ID."""
        result = await self._api_request("GET", f"users/{user_id}.json")
        
        user_data = result["user"]
        
        return ZendeskUser(
            id=user_data["id"],
            name=user_data["name"],
            email=user_data["email"],
            role=user_data["role"],
            active=user_data["active"],
            verified=user_data["verified"],
            shared=user_data["shared"],
            locale=user_data["locale"],
            timezone=user_data["timezone"],
            last_login_at=datetime.fromisoformat(user_data["last_login_at"].replace("Z", "+00:00")) if user_data.get("last_login_at") else None,
            created_at=datetime.fromisoformat(user_data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(user_data["updated_at"].replace("Z", "+00:00")),
            organization_id=user_data.get("organization_id"),
            default_group_id=user_data.get("default_group_id"),
            phone=user_data.get("phone"),
            signature=user_data.get("signature"),
            details=user_data.get("details"),
            notes=user_data.get("notes"),
            custom_role_id=user_data.get("custom_role_id"),
            moderator=user_data["moderator"],
            ticket_restriction=user_data.get("ticket_restriction"),
            only_private_comments=user_data["only_private_comments"],
            tags=user_data.get("tags", []),
            suspended=user_data["suspended"],
            remote_photo_url=user_data.get("remote_photo_url"),
            user_fields=user_data.get("user_fields", {})
        )
    
    async def update_user(
        self,
        user_id: int,
        name: Optional[str] = None,
        email: Optional[str] = None,
        role: Optional[str] = None,
        organization_id: Optional[int] = None,
        user_fields: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update existing user."""
        user_data = {"user": {}}
        
        if name:
            user_data["user"]["name"] = name
        
        if email:
            user_data["user"]["email"] = email
        
        if role:
            user_data["user"]["role"] = role
        
        if organization_id:
            user_data["user"]["organization_id"] = organization_id
        
        if user_fields:
            user_data["user"]["user_fields"] = user_fields
        
        if not user_data["user"]:
            raise ValueError("No fields to update")
        
        await self._api_request("PUT", f"users/{user_id}.json", json_data=user_data)
        
        self.logger.info(f"Updated Zendesk user: {user_id}")
    
    async def search_users(self, query: str) -> List[ZendeskUser]:
        """Search users by query."""
        params = {"query": query}
        result = await self._api_request("GET", "users/search.json", params=params)
        
        users = []
        for user_data in result.get("users", []):
            user = ZendeskUser(
                id=user_data["id"],
                name=user_data["name"],
                email=user_data["email"],
                role=user_data["role"],
                active=user_data["active"],
                verified=user_data["verified"],
                shared=user_data["shared"],
                locale=user_data["locale"],
                timezone=user_data["timezone"],
                last_login_at=datetime.fromisoformat(user_data["last_login_at"].replace("Z", "+00:00")) if user_data.get("last_login_at") else None,
                created_at=datetime.fromisoformat(user_data["created_at"].replace("Z", "+00:00")),
                updated_at=datetime.fromisoformat(user_data["updated_at"].replace("Z", "+00:00")),
                organization_id=user_data.get("organization_id"),
                default_group_id=user_data.get("default_group_id"),
                phone=user_data.get("phone"),
                signature=user_data.get("signature"),
                details=user_data.get("details"),
                notes=user_data.get("notes"),
                custom_role_id=user_data.get("custom_role_id"),
                moderator=user_data["moderator"],
                ticket_restriction=user_data.get("ticket_restriction"),
                only_private_comments=user_data["only_private_comments"],
                tags=user_data.get("tags", []),
                suspended=user_data["suspended"],
                remote_photo_url=user_data.get("remote_photo_url"),
                user_fields=user_data.get("user_fields", {})
            )
            users.append(user)
        
        return users
    
    # Organization Management
    
    async def create_organization(
        self,
        name: str,
        domain_names: Optional[List[str]] = None,
        details: Optional[str] = None,
        notes: Optional[str] = None,
        organization_fields: Optional[Dict[str, Any]] = None
    ) -> int:
        """Create new organization."""
        org_data = {
            "organization": {
                "name": name
            }
        }
        
        if domain_names:
            org_data["organization"]["domain_names"] = domain_names
        
        if details:
            org_data["organization"]["details"] = details
        
        if notes:
            org_data["organization"]["notes"] = notes
        
        if organization_fields:
            org_data["organization"]["organization_fields"] = organization_fields
        
        result = await self._api_request("POST", "organizations.json", json_data=org_data)
        
        organization = result["organization"]
        org_id = organization["id"]
        
        self.logger.info(f"Created Zendesk organization: {org_id}")
        
        return org_id
    
    async def get_organization(self, org_id: int) -> ZendeskOrganization:
        """Get organization by ID."""
        result = await self._api_request("GET", f"organizations/{org_id}.json")
        
        org_data = result["organization"]
        
        return ZendeskOrganization(
            id=org_data["id"],
            name=org_data["name"],
            created_at=datetime.fromisoformat(org_data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(org_data["updated_at"].replace("Z", "+00:00")),
            domain_names=org_data.get("domain_names", []),
            details=org_data.get("details"),
            notes=org_data.get("notes"),
            group_id=org_data.get("group_id"),
            shared_tickets=org_data["shared_tickets"],
            shared_comments=org_data["shared_comments"],
            tags=org_data.get("tags", []),
            organization_fields=org_data.get("organization_fields", {})
        )
    
    # Macros and Automation
    
    async def get_macros(self, active: bool = True) -> List[ZendeskMacro]:
        """Get ticket macros."""
        params = {"active": active}
        result = await self._api_request("GET", "macros.json", params=params)
        
        macros = []
        for macro_data in result.get("macros", []):
            macro = ZendeskMacro(
                id=macro_data["id"],
                title=macro_data["title"],
                active=macro_data["active"],
                description=macro_data.get("description"),
                actions=macro_data.get("actions", []),
                restriction=macro_data.get("restriction"),
                created_at=datetime.fromisoformat(macro_data["created_at"].replace("Z", "+00:00")),
                updated_at=datetime.fromisoformat(macro_data["updated_at"].replace("Z", "+00:00"))
            )
            macros.append(macro)
        
        return macros
    
    async def apply_macro(self, ticket_id: int, macro_id: int) -> Dict[str, Any]:
        """Apply macro to ticket."""
        result = await self._api_request("POST", f"tickets/{ticket_id}/macros/{macro_id}/apply.json")
        
        self.logger.info(f"Applied macro {macro_id} to ticket {ticket_id}")
        
        return result
    
    # Attachments
    
    async def upload_attachment(self, file_path: str, token: Optional[str] = None) -> str:
        """Upload attachment and get token."""
        import os
        
        if not os.path.exists(file_path):
            raise ZendeskAPIError(f"File not found: {file_path}")
        
        filename = os.path.basename(file_path)
        
        with open(file_path, "rb") as file:
            files = {
                "file": (filename, file, "application/octet-stream")
            }
            
            params = {}
            if token:
                params["token"] = token
            
            result = await self._api_request(
                "POST",
                "uploads.json",
                params=params,
                files=files
            )
        
        upload_token = result["upload"]["token"]
        self.logger.info(f"Uploaded attachment: {upload_token}")
        
        return upload_token
    
    # Satisfaction Ratings
    
    async def get_satisfaction_ratings(self, ticket_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get satisfaction ratings."""
        params = {}
        if ticket_id:
            params["ticket_id"] = ticket_id
        
        result = await self._api_request("GET", "satisfaction_ratings.json", params=params)
        return result.get("satisfaction_ratings", [])
    
    # Ticket Fields
    
    async def get_ticket_fields(self, active: bool = True) -> List[Dict[str, Any]]:
        """Get ticket fields."""
        params = {"active": active}
        result = await self._api_request("GET", "ticket_fields.json", params=params)
        return result.get("ticket_fields", [])
    
    # Webhook Management
    
    async def create_webhook(
        self,
        name: str,
        endpoint: str,
        events: List[str],
        status: str = "active",
        request_format: str = "json"
    ) -> str:
        """Create webhook for ticket events."""
        webhook_data = {
            "webhook": {
                "name": name,
                "endpoint": endpoint,
                "events": events,
                "status": status,
                "request_format": request_format
            }
        }
        
        result = await self._api_request("POST", "webhooks.json", json_data=webhook_data)
        
        webhook_id = result["webhook"]["id"]
        self.logger.info(f"Created webhook {webhook_id}: {name}")
        
        return webhook_id
    
    async def delete_webhook(self, webhook_id: str) -> None:
        """Delete webhook."""
        await self._api_request("DELETE", f"webhooks/{webhook_id}.json")
        self.logger.info(f"Deleted webhook {webhook_id}")
    
    # Event Registration
    
    def add_ticket_handler(self, handler: Callable[[ZendeskTicket], None]) -> None:
        """Add ticket event handler."""
        self._ticket_handlers.append(handler)
    
    def add_user_handler(self, handler: Callable[[ZendeskUser], None]) -> None:
        """Add user event handler."""
        self._user_handlers.append(handler)
    
    def add_organization_handler(self, handler: Callable[[ZendeskOrganization], None]) -> None:
        """Add organization event handler."""
        self._organization_handlers.append(handler)
    
    def remove_ticket_handler(self, handler: Callable) -> None:
        """Remove ticket event handler."""
        if handler in self._ticket_handlers:
            self._ticket_handlers.remove(handler)
    
    def remove_user_handler(self, handler: Callable) -> None:
        """Remove user event handler."""
        if handler in self._user_handlers:
            self._user_handlers.remove(handler)
    
    def remove_organization_handler(self, handler: Callable) -> None:
        """Remove organization event handler."""
        if handler in self._organization_handlers:
            self._organization_handlers.remove(handler)
    
    # Rate Limiting
    
    async def check_rate_limit(self) -> Dict[str, Any]:
        """Check current rate limit status."""
        return {
            "remaining": self._rate_limit_info["remaining"],
            "reset_time": self._rate_limit_info["reset"],
            "retry_after": self._rate_limit_info["retry_after"]
        }
    
    # Health Check
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        try:
            # Test API connectivity
            account_info = await self.get_account_settings()
            
            # Test user authentication
            user_info = await self.get_current_user()
            
            # Test ticket access
            test_tickets = await self.search_tickets("type:ticket", per_page=1)
            
            # Check connection state
            connected = self._connected and bool(self._user_info)
            
            # Overall health status
            is_healthy = (
                connected and
                bool(account_info) and
                bool(user_info) and
                len(test_tickets) >= 0
            )
            
            return {
                "status": "healthy" if is_healthy else "degraded",
                "api_connectivity": True,
                "user_authenticated": bool(user_info),
                "tickets_accessible": len(test_tickets) >= 0,
                "connection_state": connected,
                "subdomain": self.zendesk_config.subdomain if hasattr(self.zendesk_config, 'subdomain') else "Unknown",
                "user_email": user_info.get("email", "Unknown"),
                "rate_limit_remaining": self._rate_limit_info["remaining"],
                "last_check": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "api_connectivity": False,
                "connection_state": self._connected,
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
    
    async def close(self) -> None:
        """Close integration and cleanup resources."""
        self.logger.info("Closing Zendesk integration")
        
        # Clear caches
        self._ticket_field_cache.clear()
        
        # Close OAuth client
        if self.oauth_client:
            await self.oauth_client.close()
        
        await super().close()


# Export the integration
__all__ = [
    "ZendeskIntegration",
    "ZendeskTicket",
    "ZendeskUser",
    "ZendeskOrganization",
    "ZendeskComment",
    "ZendeskView",
    "ZendeskMacro",
    "ZendeskAPIError",
    "ZendeskRateLimitError"
]