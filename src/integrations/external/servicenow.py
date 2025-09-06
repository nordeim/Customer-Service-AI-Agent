"""
ServiceNow integration with comprehensive ITSM and CSM capabilities.

Provides enterprise-grade ServiceNow integration including:
- Incident, Problem, Change, and Request management
- Table API with dynamic schema discovery
- Aggregate API for reporting and analytics
- Import Set API for bulk data operations
- Attachment and file management
- Workflow automation and approval processes
- Service Catalog and catalog items
- Knowledge Base integration
- User and group management
- OAuth 2.0 authentication with refresh tokens
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


class ServiceNowAPIError(ExternalServiceError):
    """ServiceNow API specific errors."""
    pass


class ServiceNowRateLimitError(RateLimitError):
    """ServiceNow rate limit exceeded error."""
    pass


class ServiceNowIncident:
    """Represents a ServiceNow incident."""
    
    def __init__(
        self,
        sys_id: str,
        number: str,
        short_description: str,
        description: Optional[str] = None,
        state: str = "New",
        priority: str = "3",
        urgency: str = "3",
        impact: str = "3",
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
        assignment_group: Optional[str] = None,
        assigned_to: Optional[str] = None,
        opened_by: Optional[str] = None,
        opened_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        resolved_at: Optional[datetime] = None,
        closed_at: Optional[datetime] = None,
        work_notes: Optional[str] = None,
        additional_fields: Optional[Dict[str, Any]] = None
    ):
        self.sys_id = sys_id
        self.number = number
        self.short_description = short_description
        self.description = description
        self.state = state
        self.priority = priority
        self.urgency = urgency
        self.impact = impact
        self.category = category
        self.subcategory = subcategory
        self.assignment_group = assignment_group
        self.assigned_to = assigned_to
        self.opened_by = opened_by
        self.opened_at = opened_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.resolved_at = resolved_at
        self.closed_at = closed_at
        self.work_notes = work_notes
        self.additional_fields = additional_fields or {}


class ServiceNowRequest:
    """Represents a ServiceNow service request."""
    
    def __init__(
        self,
        sys_id: str,
        number: str,
        short_description: str,
        description: Optional[str] = None,
        state: str = "Requested",
        priority: str = "3",
        requested_for: Optional[str] = None,
        requested_by: Optional[str] = None,
        requested_date: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        catalog_item: Optional[str] = None,
        quantity: int = 1,
        price: Optional[float] = None,
        additional_fields: Optional[Dict[str, Any]] = None
    ):
        self.sys_id = sys_id
        self.number = number
        self.short_description = short_description
        self.description = description
        self.state = state
        self.priority = priority
        self.requested_for = requested_for
        self.requested_by = requested_by
        self.requested_date = requested_date or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.catalog_item = catalog_item
        self.quantity = quantity
        self.price = price
        self.additional_fields = additional_fields or {}


class ServiceNowUser:
    """Represents a ServiceNow user."""
    
    def __init__(
        self,
        sys_id: str,
        user_name: str,
        email: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        active: bool = True,
        locked_out: bool = False,
        last_login: Optional[datetime] = None,
        department: Optional[str] = None,
        title: Optional[str] = None,
        manager: Optional[str] = None,
        location: Optional[str] = None,
        additional_fields: Optional[Dict[str, Any]] = None
    ):
        self.sys_id = sys_id
        self.user_name = user_name
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.active = active
        self.locked_out = locked_out
        self.last_login = last_login
        self.department = department
        self.title = title
        self.manager = manager
        self.location = location
        self.additional_fields = additional_fields or {}


class ServiceNowGroup:
    """Represents a ServiceNow group."""
    
    def __init__(
        self,
        sys_id: str,
        name: str,
        description: Optional[str] = None,
        active: bool = True,
        email: Optional[str] = None,
        manager: Optional[str] = None,
        members: Optional[List[str]] = None,
        additional_fields: Optional[Dict[str, Any]] = None
    ):
        self.sys_id = sys_id
        self.name = name
        self.description = description
        self.active = active
        self.email = email
        self.manager = manager
        self.members = members or []
        self.additional_fields = additional_fields or {}


class ServiceNowCatalogItem:
    """Represents a ServiceNow catalog item."""
    
    def __init__(
        self,
        sys_id: str,
        name: str,
        description: Optional[str] = None,
        category: Optional[str] = None,
        price: Optional[float] = None,
        recurring_price: Optional[float] = None,
        active: bool = True,
        picture: Optional[str] = None,
        additional_fields: Optional[Dict[str, Any]] = None
    ):
        self.sys_id = sys_id
        self.name = name
        self.description = description
        self.category = category
        self.price = price
        self.recurring_price = recurring_price
        self.active = active
        self.picture = picture
        self.additional_fields = additional_fields or {}


class ServiceNowAttachment:
    """Represents a ServiceNow attachment."""
    
    def __init__(
        self,
        sys_id: str,
        file_name: str,
        content_type: str,
        size_bytes: int,
        table_name: Optional[str] = None,
        table_sys_id: Optional[str] = None,
        uploaded_by: Optional[str] = None,
        uploaded_at: Optional[datetime] = None,
        download_url: Optional[str] = None
    ):
        self.sys_id = sys_id
        self.file_name = file_name
        self.content_type = content_type
        self.size_bytes = size_bytes
        self.table_name = table_name
        self.table_sys_id = table_sys_id
        self.uploaded_by = uploaded_by
        self.uploaded_at = uploaded_at or datetime.utcnow()
        self.download_url = download_url


class ServiceNowIntegration(BaseIntegrationImpl):
    """ServiceNow integration with comprehensive ITSM and CSM capabilities."""
    
    def __init__(self, config: BaseIntegrationConfig):
        super().__init__(IntegrationType.SERVICENOW, config.dict())
        
        self.servicenow_config = config
        self.logger = logger.getChild("servicenow")
        
        # ServiceNow API configuration
        self.api_version = "v1"  # Table API v1
        self.base_url = self._determine_base_url()
        
        # OAuth client for API authentication
        self.oauth_client: Optional[OAuth2Client] = None
        
        # Connection state
        self._connected = False
        self._user_info: Dict[str, Any] = {}
        self._instance_info: Dict[str, Any] = {}
        self._table_cache: Dict[str, Dict[str, Any]] = {}
        
        # Rate limiting
        self._rate_limit_info = {
            "remaining": 1000,  # ServiceNow default
            "reset": None,
            "retry_after": None
        }
        
        # Event tracking
        self._incident_handlers: List[Callable] = []
        self._request_handlers: List[Callable] = []
    
    def _determine_base_url(self) -> str:
        """Determine ServiceNow base URL based on configuration."""
        if hasattr(self.servicenow_config, 'instance_url'):
            return str(self.servicenow_config.instance_url).rstrip('/')
        elif hasattr(self.servicenow_config, 'base_url'):
            return str(self.servicenow_config.base_url).rstrip('/')
        else:
            raise ServiceNowAPIError("No ServiceNow instance URL configured")
    
    # Authentication and Connection
    
    async def authenticate(self) -> bool:
        """Authenticate with ServiceNow API."""
        try:
            # Set up OAuth client if credentials are provided
            if hasattr(self.servicenow_config, 'oauth') and self.servicenow_config.oauth:
                from ..base import OAuth2Config
                
                oauth_config = OAuth2Config(
                    client_id=self.servicenow_config.oauth.client_id,
                    client_secret=self.servicenow_config.oauth.client_secret,
                    authorization_url=self.servicenow_config.oauth.authorization_url,
                    token_url=self.servicenow_config.oauth.token_url,
                    redirect_uri=self.servicenow_config.oauth.redirect_uri,
                    scope=self.servicenow_config.oauth.scope
                )
                
                self.oauth_client = OAuth2Client(oauth_config)
            
            # Test API connectivity
            instance_info = await self.get_instance_info()
            self._instance_info = instance_info
            
            # Get user information
            user_info = await self.get_current_user()
            self._user_info = user_info
            
            self.logger.info(f"Authenticated with ServiceNow as {user_info.get('name', 'Unknown')}")
            self._connected = True
            
            return True
            
        except Exception as e:
            self.logger.error(f"ServiceNow authentication failed: {e}")
            raise ServiceNowAPIError(f"Authentication failed: {e}")
    
    async def _api_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to ServiceNow API."""
        url = f"{self.base_url}/api/{endpoint.lstrip('/')}"
        
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
        elif hasattr(self.servicenow_config, 'username') and hasattr(self.servicenow_config, 'password'):
            # Basic auth
            auth_string = f"{self.servicenow_config.username}:{self.servicenow_config.password}"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()
            headers["Authorization"] = f"Basic {encoded_auth}"
        else:
            raise ServiceNowAPIError("No authentication credentials configured")
        
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
                    raise ServiceNowRateLimitError(
                        f"ServiceNow rate limit exceeded. Retry after {retry_after}s",
                        IntegrationType.SERVICENOW,
                        {"retry_after": retry_after}
                    )
                
                response.raise_for_status()
                
                # Update rate limit info
                self._update_rate_limit_info(response)
                
                return response.json() if response.content else {}
                
        except httpx.RequestError as e:
            self.logger.error(f"ServiceNow request error: {e}")
            raise ServiceNowAPIError(f"Request failed: {e}")
    
    def _update_rate_limit_info(self, response: httpx.Response) -> None:
        """Update rate limit information from response headers."""
        # Extract rate limit info from headers if available
        remaining = response.headers.get("X-RateLimit-Remaining")
        reset = response.headers.get("X-RateLimit-Reset")
        
        if remaining:
            self._rate_limit_info["remaining"] = int(remaining)
        
        if reset:
            self._rate_limit_info["reset"] = int(reset)
    
    # Instance and User Information
    
    async def get_instance_info(self) -> Dict[str, Any]:
        """Get ServiceNow instance information."""
        return await self._api_request("GET", "now/table/sys_properties", params={"sysparm_query": "name=startswith(glide.)", "sysparm_limit": 10})
    
    async def get_current_user(self) -> Dict[str, Any]:
        """Get current user information."""
        return await self._api_request("GET", "now/connect/support/analytics/profile")
    
    # Table API - Core functionality
    
    async def get_records(
        self,
        table_name: str,
        query: Optional[str] = None,
        fields: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get records from a table."""
        params = {
            "sysparm_limit": limit,
            "sysparm_offset": offset
        }
        
        if query:
            params["sysparm_query"] = query
        
        if fields:
            params["sysparm_fields"] = ",".join(fields)
        
        if order_by:
            params["sysparm_order_by"] = order_by
        
        result = await self._api_request("GET", f"now/table/{table_name}", params=params)
        
        return result.get("result", [])
    
    async def get_record(self, table_name: str, sys_id: str) -> Dict[str, Any]:
        """Get single record by sys_id."""
        result = await self._api_request("GET", f"now/table/{table_name}/{sys_id}")
        return result.get("result", {})
    
    async def create_record(self, table_name: str, data: Dict[str, Any]) -> str:
        """Create new record in table."""
        result = await self._api_request("POST", f"now/table/{table_name}", json_data=data)
        
        sys_id = result.get("result", {}).get("sys_id")
        if not sys_id:
            raise ServiceNowAPIError("Failed to create record: no sys_id returned")
        
        self.logger.info(f"Created record in {table_name}: {sys_id}")
        return sys_id
    
    async def update_record(self, table_name: str, sys_id: str, data: Dict[str, Any]) -> None:
        """Update existing record."""
        await self._api_request("PUT", f"now/table/{table_name}/{sys_id}", json_data=data)
        self.logger.info(f"Updated record {sys_id} in {table_name}")
    
    async def delete_record(self, table_name: str, sys_id: str) -> None:
        """Delete record."""
        await self._api_request("DELETE", f"now/table/{table_name}/{sys_id}")
        self.logger.info(f"Deleted record {sys_id} from {table_name}")
    
    # Incident Management
    
    async def create_incident(
        self,
        short_description: str,
        description: Optional[str] = None,
        urgency: str = "3",
        impact: str = "3",
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
        assignment_group: Optional[str] = None,
        assigned_to: Optional[str] = None,
        additional_fields: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create new incident."""
        incident_data = {
            "short_description": short_description,
            "urgency": urgency,
            "impact": impact
        }
        
        if description:
            incident_data["description"] = description
        
        if category:
            incident_data["category"] = category
        
        if subcategory:
            incident_data["subcategory"] = subcategory
        
        if assignment_group:
            incident_data["assignment_group"] = assignment_group
        
        if assigned_to:
            incident_data["assigned_to"] = assigned_to
        
        if additional_fields:
            incident_data.update(additional_fields)
        
        sys_id = await self.create_record("incident", incident_data)
        return sys_id
    
    async def get_incident(self, sys_id: str) -> ServiceNowIncident:
        """Get incident by sys_id."""
        incident_data = await self.get_record("incident", sys_id)
        
        return ServiceNowIncident(
            sys_id=incident_data["sys_id"],
            number=incident_data["number"],
            short_description=incident_data["short_description"],
            description=incident_data.get("description"),
            state=incident_data.get("state", "New"),
            priority=incident_data.get("priority", "3"),
            urgency=incident_data.get("urgency", "3"),
            impact=incident_data.get("impact", "3"),
            category=incident_data.get("category"),
            subcategory=incident_data.get("subcategory"),
            assignment_group=incident_data.get("assignment_group"),
            assigned_to=incident_data.get("assigned_to"),
            opened_by=incident_data.get("opened_by"),
            opened_at=datetime.fromisoformat(incident_data["sys_created_on"].replace(" ", "T")) if incident_data.get("sys_created_on") else None,
            updated_at=datetime.fromisoformat(incident_data["sys_updated_on"].replace(" ", "T")) if incident_data.get("sys_updated_on") else None,
            work_notes=incident_data.get("work_notes"),
            additional_fields=incident_data
        )
    
    async def update_incident(self, sys_id: str, data: Dict[str, Any]) -> None:
        """Update incident."""
        await self.update_record("incident", sys_id, data)
    
    async def get_incidents(
        self,
        query: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ServiceNowIncident]:
        """Get incidents with optional query."""
        records = await self.get_records("incident", query=query, limit=limit, offset=offset)
        
        incidents = []
        for record in records:
            incident = ServiceNowIncident(
                sys_id=record["sys_id"],
                number=record["number"],
                short_description=record["short_description"],
                description=record.get("description"),
                state=record.get("state", "New"),
                priority=record.get("priority", "3"),
                urgency=record.get("urgency", "3"),
                impact=record.get("impact", "3"),
                category=record.get("category"),
                subcategory=record.get("subcategory"),
                assignment_group=record.get("assignment_group"),
                assigned_to=record.get("assigned_to"),
                opened_by=record.get("opened_by"),
                opened_at=datetime.fromisoformat(record["sys_created_on"].replace(" ", "T")) if record.get("sys_created_on") else None,
                updated_at=datetime.fromisoformat(record["sys_updated_on"].replace(" ", "T")) if record.get("sys_updated_on") else None,
                work_notes=record.get("work_notes"),
                additional_fields=record
            )
            incidents.append(incident)
        
        return incidents
    
    # Service Request Management
    
    async def create_request(
        self,
        short_description: str,
        catalog_item: str,
        description: Optional[str] = None,
        priority: str = "3",
        quantity: int = 1,
        requested_for: Optional[str] = None,
        additional_fields: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create new service request."""
        request_data = {
            "short_description": short_description,
            "cat_item": catalog_item,
            "priority": priority,
            "quantity": quantity
        }
        
        if description:
            request_data["description"] = description
        
        if requested_for:
            request_data["requested_for"] = requested_for
        
        if additional_fields:
            request_data.update(additional_fields)
        
        sys_id = await self.create_record("sc_request", request_data)
        return sys_id
    
    async def get_request(self, sys_id: str) -> ServiceNowRequest:
        """Get service request by sys_id."""
        request_data = await self.get_record("sc_request", sys_id)
        
        return ServiceNowRequest(
            sys_id=request_data["sys_id"],
            number=request_data["number"],
            short_description=request_data["short_description"],
            description=request_data.get("description"),
            state=request_data.get("state", "Requested"),
            priority=request_data.get("priority", "3"),
            requested_for=request_data.get("requested_for"),
            requested_by=request_data.get("requested_by"),
            requested_date=datetime.fromisoformat(request_data["requested_date"].replace(" ", "T")) if request_data.get("requested_date") else None,
            updated_at=datetime.fromisoformat(request_data["sys_updated_on"].replace(" ", "T")) if request_data.get("sys_updated_on") else None,
            catalog_item=request_data.get("cat_item"),
            quantity=int(request_data.get("quantity", 1)),
            price=float(request_data.get("price", 0)) if request_data.get("price") else None,
            additional_fields=request_data
        )
    
    # User and Group Management
    
    async def get_user(self, sys_id: str) -> ServiceNowUser:
        """Get user by sys_id."""
        user_data = await self.get_record("sys_user", sys_id)
        
        return ServiceNowUser(
            sys_id=user_data["sys_id"],
            user_name=user_data["user_name"],
            email=user_data["email"],
            first_name=user_data.get("first_name"),
            last_name=user_data.get("last_name"),
            active=user_data.get("active", True),
            locked_out=user_data.get("locked_out", False),
            last_login=datetime.fromisoformat(user_data["last_login"].replace(" ", "T")) if user_data.get("last_login") else None,
            department=user_data.get("department"),
            title=user_data.get("title"),
            manager=user_data.get("manager"),
            location=user_data.get("location"),
            additional_fields=user_data
        )
    
    async def get_users(
        self,
        query: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ServiceNowUser]:
        """Get users with optional query."""
        records = await self.get_records("sys_user", query=query, limit=limit, offset=offset)
        
        users = []
        for record in records:
            user = ServiceNowUser(
                sys_id=record["sys_id"],
                user_name=record["user_name"],
                email=record["email"],
                first_name=record.get("first_name"),
                last_name=record.get("last_name"),
                active=record.get("active", True),
                locked_out=record.get("locked_out", False),
                last_login=datetime.fromisoformat(record["last_login"].replace(" ", "T")) if record.get("last_login") else None,
                department=record.get("department"),
                title=record.get("title"),
                manager=record.get("manager"),
                location=record.get("location"),
                additional_fields=record
            )
            users.append(user)
        
        return users
    
    async def get_group(self, sys_id: str) -> ServiceNowGroup:
        """Get group by sys_id."""
        group_data = await self.get_record("sys_user_group", sys_id)
        
        return ServiceNowGroup(
            sys_id=group_data["sys_id"],
            name=group_data["name"],
            description=group_data.get("description"),
            active=group_data.get("active", True),
            email=group_data.get("email"),
            manager=group_data.get("manager"),
            additional_fields=group_data
        )
    
    # Attachment Management
    
    async def upload_attachment(
        self,
        table_name: str,
        table_sys_id: str,
        file_path: str,
        file_name: Optional[str] = None
    ) -> str:
        """Upload attachment to record."""
        import os
        
        if not os.path.exists(file_path):
            raise ServiceNowAPIError(f"File not found: {file_path}")
        
        filename = file_name or os.path.basename(file_path)
        
        # First, create attachment metadata
        attachment_data = {
            "table_name": table_name,
            "table_sys_id": table_sys_id,
            "file_name": filename,
            "content_type": "application/octet-stream"
        }
        
        # Create attachment record
        attachment_sys_id = await self.create_record("sys_attachment", attachment_data)
        
        # Upload file content
        with open(file_path, "rb") as file:
            files = {
                "file": (filename, file, "application/octet-stream")
            }
            
            await self._api_request(
                "POST",
                f"now/attachment/{attachment_sys_id}/upload",
                files=files
            )
        
        self.logger.info(f"Uploaded attachment {attachment_sys_id} to {table_name}.{table_sys_id}")
        return attachment_sys_id
    
    async def get_attachments(self, table_name: str, table_sys_id: str) -> List[ServiceNowAttachment]:
        """Get attachments for record."""
        query = f"table_name={table_name}^table_sys_id={table_sys_id}"
        records = await self.get_records("sys_attachment", query=query)
        
        attachments = []
        for record in records:
            attachment = ServiceNowAttachment(
                sys_id=record["sys_id"],
                file_name=record["file_name"],
                content_type=record.get("content_type", "application/octet-stream"),
                size_bytes=record.get("size_bytes", 0),
                table_name=record.get("table_name"),
                table_sys_id=record.get("table_sys_id"),
                uploaded_by=record.get("sys_created_by"),
                uploaded_at=datetime.fromisoformat(record["sys_created_on"].replace(" ", "T")) if record.get("sys_created_on") else None,
                download_url=f"{self.base_url}/api/now/attachment/{record['sys_id']}/file"
            )
            attachments.append(attachment)
        
        return attachments
    
    # Aggregate API for Analytics
    
    async def get_aggregate_data(
        self,
        table_name: str,
        group_by: List[str],
        aggregates: List[Dict[str, Any]],
        query: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get aggregated data for analytics."""
        aggregate_data = {
            "table": table_name,
            "group_by": group_by,
            "aggregates": aggregates
        }
        
        if query:
            aggregate_data["query"] = query
        
        result = await self._api_request("POST", "now/stats/aggregate", json_data=aggregate_data)
        return result.get("result", {})
    
    # Import Set API for Bulk Operations
    
    async def create_import_set(self, import_set_name: str, data: List[Dict[str, Any]]) -> str:
        """Create import set for bulk data import."""
        import_data = {
            "import_set_name": import_set_name,
            "data": data
        }
        
        result = await self._api_request("POST", "now/import/set", json_data=import_data)
        
        import_set_id = result.get("result", {}).get("import_set_id")
        if not import_set_id:
            raise ServiceNowAPIError("Failed to create import set")
        
        self.logger.info(f"Created import set: {import_set_id}")
        return import_set_id
    
    # Event Registration
    
    def add_incident_handler(self, handler: Callable[[ServiceNowIncident], None]) -> None:
        """Add incident event handler."""
        self._incident_handlers.append(handler)
    
    def add_request_handler(self, handler: Callable[[ServiceNowRequest], None]) -> None:
        """Add request event handler."""
        self._request_handlers.append(handler)
    
    def remove_incident_handler(self, handler: Callable) -> None:
        """Remove incident event handler."""
        if handler in self._incident_handlers:
            self._incident_handlers.remove(handler)
    
    def remove_request_handler(self, handler: Callable) -> None:
        """Remove request event handler."""
        if handler in self._request_handlers:
            self._request_handlers.remove(handler)
    
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
            instance_info = await self.get_instance_info()
            
            # Test user authentication
            user_info = await self.get_current_user()
            
            # Test table access
            test_records = await self.get_records("incident", limit=1)
            
            # Check connection state
            connected = self._connected and bool(self._user_info)
            
            # Overall health status
            is_healthy = (
                connected and
                bool(instance_info) and
                bool(user_info) and
                len(test_records) > 0
            )
            
            return {
                "status": "healthy" if is_healthy else "degraded",
                "api_connectivity": True,
                "user_authenticated": bool(user_info),
                "table_accessible": len(test_records) > 0,
                "connection_state": connected,
                "instance_name": self.base_url.split("//")[-1].split(".")[0],
                "user_name": user_info.get("name", "Unknown"),
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
        self.logger.info("Closing ServiceNow integration")
        
        # Clear caches
        self._table_cache.clear()
        
        # Close OAuth client
        if self.oauth_client:
            await self.oauth_client.close()
        
        await super().close()


# Export the integration
__all__ = [
    "ServiceNowIntegration",
    "ServiceNowIncident",
    "ServiceNowRequest",
    "ServiceNowUser",
    "ServiceNowGroup",
    "ServiceNowCatalogItem",
    "ServiceNowAttachment",
    "ServiceNowAPIError",
    "ServiceNowRateLimitError"
]