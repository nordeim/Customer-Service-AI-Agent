"""
Atlassian Jira integration with comprehensive issue management and workflow automation.

Provides enterprise-grade Jira integration including:
- Jira Cloud and Server API support
- Issue lifecycle management (create, update, transition, comment)
- Custom field mapping and validation
- Workflow automation and transition management
- Attachment handling and file uploads
- JQL (Jira Query Language) support
- Agile board and sprint management
- Time tracking and worklog management
- Webhook event processing
- Rate limiting and retry mechanisms
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


class JiraAPIError(ExternalServiceError):
    """Jira API specific errors."""
    pass


class JiraRateLimitError(RateLimitError):
    """Jira rate limit exceeded error."""
    pass


class JiraIssue:
    """Represents a Jira issue."""
    
    def __init__(
        self,
        key: str,
        summary: str,
        issue_type: str,
        status: str,
        priority: str,
        assignee: Optional[str] = None,
        reporter: Optional[str] = None,
        description: Optional[str] = None,
        created: Optional[datetime] = None,
        updated: Optional[datetime] = None,
        labels: Optional[List[str]] = None,
        components: Optional[List[str]] = None,
        fix_versions: Optional[List[str]] = None,
        affect_versions: Optional[List[str]] = None,
        custom_fields: Optional[Dict[str, Any]] = None
    ):
        self.key = key
        self.summary = summary
        self.issue_type = issue_type
        self.status = status
        self.priority = priority
        self.assignee = assignee
        self.reporter = reporter
        self.description = description
        self.created = created or datetime.utcnow()
        self.updated = updated or datetime.utcnow()
        self.labels = labels or []
        self.components = components or []
        self.fix_versions = fix_versions or []
        self.affect_versions = affect_versions or []
        self.custom_fields = custom_fields or {}


class JiraComment:
    """Represents a Jira issue comment."""
    
    def __init__(
        self,
        id: str,
        body: str,
        author: str,
        created: datetime,
        updated: Optional[datetime] = None,
        visibility: Optional[Dict[str, str]] = None
    ):
        self.id = id
        self.body = body
        self.author = author
        self.created = created
        self.updated = updated or created
        self.visibility = visibility


class JiraWorklog:
    """Represents a Jira worklog entry."""
    
    def __init__(
        self,
        id: str,
        time_spent: str,
        time_spent_seconds: int,
        author: str,
        created: datetime,
        updated: Optional[datetime] = None,
        comment: Optional[str] = None,
        started: Optional[datetime] = None
    ):
        self.id = id
        self.time_spent = time_spent
        self.time_spent_seconds = time_spent_seconds
        self.author = author
        self.created = created
        self.updated = updated or created
        self.comment = comment
        self.started = started or created


class JiraSprint:
    """Represents a Jira Agile sprint."""
    
    def __init__(
        self,
        id: int,
        name: str,
        state: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        complete_date: Optional[datetime] = None,
        origin_board_id: Optional[int] = None,
        goal: Optional[str] = None
    ):
        self.id = id
        self.name = name
        self.state = state
        self.start_date = start_date
        self.end_date = end_date
        self.complete_date = complete_date
        self.origin_board_id = origin_board_id
        self.goal = goal


class JiraProject:
    """Represents a Jira project."""
    
    def __init__(
        self,
        key: str,
        name: str,
        project_type: str,
        lead: Optional[str] = None,
        description: Optional[str] = None,
        url: Optional[str] = None,
        avatar_urls: Optional[Dict[str, str]] = None
    ):
        self.key = key
        self.name = name
        self.project_type = project_type
        self.lead = lead
        self.description = description
        self.url = url
        self.avatar_urls = avatar_urls or {}


class JiraField:
    """Represents a Jira field definition."""
    
    def __init__(
        self,
        id: str,
        name: str,
        field_type: str,
        custom: bool = False,
        orderable: bool = True,
        navigable: bool = True,
        searchable: bool = True,
        clause_names: Optional[List[str]] = None,
        schema: Optional[Dict[str, Any]] = None
    ):
        self.id = id
        self.name = name
        self.field_type = field_type
        self.custom = custom
        self.orderable = orderable
        self.navigable = navigable
        self.searchable = searchable
        self.clause_names = clause_names or []
        self.schema = schema or {}


class JiraIntegration(BaseIntegrationImpl):
    """Atlassian Jira integration with comprehensive issue management."""
    
    def __init__(self, config: BaseIntegrationConfig):
        super().__init__(IntegrationType.JIRA, config.dict())
        
        self.jira_config = config
        self.logger = logger.getChild("jira")
        
        # Jira API configuration
        self.api_version = "3"  # Jira Cloud API v3
        self.base_url = self._determine_base_url()
        
        # OAuth client for API authentication
        self.oauth_client: Optional[OAuth2Client] = None
        
        # Connection state
        self._connected = False
        self._user_info: Dict[str, Any] = {}
        self._server_info: Dict[str, Any] = {}
        self._project_cache: Dict[str, JiraProject] = {}
        self._field_cache: Dict[str, JiraField] = {}
        
        # Rate limiting
        self._rate_limit_info = {
            "remaining": 100,  # Jira Cloud default
            "reset": None,
            "retry_after": None
        }
        
        # Event tracking
        self._issue_handlers: List[Callable] = []
        self._webhook_secret: Optional[str] = None
    
    def _determine_base_url(self) -> str:
        """Determine Jira base URL based on configuration."""
        if hasattr(self.jira_config, 'instance_url'):
            return str(self.jira_config.instance_url).rstrip('/')
        elif hasattr(self.jira_config, 'base_url'):
            return str(self.jira_config.base_url).rstrip('/')
        else:
            raise JiraAPIError("No Jira instance URL configured")
    
    # Authentication and Connection
    
    async def authenticate(self) -> bool:
        """Authenticate with Jira API."""
        try:
            # Set up OAuth client if credentials are provided
            if hasattr(self.jira_config, 'oauth') and self.jira_config.oauth:
                from ..base import OAuth2Config
                
                oauth_config = OAuth2Config(
                    client_id=self.jira_config.oauth.client_id,
                    client_secret=self.jira_config.oauth.client_secret,
                    authorization_url=self.jira_config.oauth.authorization_url,
                    token_url=self.jira_config.oauth.token_url,
                    redirect_uri=self.jira_config.oauth.redirect_uri,
                    scope=self.jira_config.oauth.scope
                )
                
                self.oauth_client = OAuth2Client(oauth_config)
            
            # Test API connectivity
            server_info = await self.get_server_info()
            self._server_info = server_info
            
            # Get user information
            user_info = await self.get_current_user()
            self._user_info = user_info
            
            self.logger.info(f"Authenticated with Jira as {user_info.get('displayName', 'Unknown')}")
            self._connected = True
            
            return True
            
        except Exception as e:
            self.logger.error(f"Jira authentication failed: {e}")
            raise JiraAPIError(f"Authentication failed: {e}")
    
    async def _api_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to Jira API."""
        url = f"{self.base_url}/rest/api/{self.api_version}/{endpoint.lstrip('/')}"
        
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
        elif hasattr(self.jira_config, 'api_token') and self.jira_config.api_token:
            # Basic auth with API token
            auth_string = f"{self.jira_config.email}:{self.jira_config.api_token}"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()
            headers["Authorization"] = f"Basic {encoded_auth}"
        else:
            raise JiraAPIError("No authentication credentials configured")
        
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
                elif method.upper() == "DELETE":
                    response = await client.delete(url, headers=headers)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                # Check for rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    self._rate_limit_info["retry_after"] = retry_after
                    raise JiraRateLimitError(
                        f"Jira rate limit exceeded. Retry after {retry_after}s",
                        IntegrationType.JIRA,
                        {"retry_after": retry_after}
                    )
                
                response.raise_for_status()
                
                # Update rate limit info
                self._update_rate_limit_info(response)
                
                return response.json() if response.content else {}
                
        except httpx.RequestError as e:
            self.logger.error(f"Jira request error: {e}")
            raise JiraAPIError(f"Request failed: {e}")
    
    def _update_rate_limit_info(self, response: httpx.Response) -> None:
        """Update rate limit information from response headers."""
        # Extract rate limit info from headers if available
        remaining = response.headers.get("X-RateLimit-Remaining")
        reset = response.headers.get("X-RateLimit-Reset")
        
        if remaining:
            self._rate_limit_info["remaining"] = int(remaining)
        
        if reset:
            self._rate_limit_info["reset"] = int(reset)
    
    # Server and User Information
    
    async def get_server_info(self) -> Dict[str, Any]:
        """Get Jira server information."""
        return await self._api_request("GET", "serverInfo")
    
    async def get_current_user(self) -> Dict[str, Any]:
        """Get current user information."""
        return await self._api_request("GET", "myself")
    
    # Project Management
    
    async def get_projects(self, max_results: int = 50) -> List[JiraProject]:
        """Get all accessible projects."""
        result = await self._api_request("GET", "project", params={"maxResults": max_results})
        
        projects = []
        for project_data in result:
            project = JiraProject(
                key=project_data["key"],
                name=project_data["name"],
                project_type=project_data["projectTypeKey"],
                lead=project_data.get("lead", {}).get("displayName"),
                description=project_data.get("description"),
                url=project_data.get("url"),
                avatar_urls=project_data.get("avatarUrls", {})
            )
            projects.append(project)
            self._project_cache[project.key] = project
        
        return projects
    
    async def get_project(self, project_key: str) -> JiraProject:
        """Get project by key."""
        if project_key in self._project_cache:
            return self._project_cache[project_key]
        
        project_data = await self._api_request("GET", f"project/{project_key}")
        
        project = JiraProject(
            key=project_data["key"],
            name=project_data["name"],
            project_type=project_data["projectTypeKey"],
            lead=project_data.get("lead", {}).get("displayName"),
            description=project_data.get("description"),
            url=project_data.get("url"),
            avatar_urls=project_data.get("avatarUrls", {})
        )
        
        self._project_cache[project_key] = project
        return project
    
    # Issue Management
    
    async def create_issue(
        self,
        project_key: str,
        summary: str,
        issue_type: str,
        description: Optional[str] = None,
        priority: Optional[str] = None,
        assignee: Optional[str] = None,
        labels: Optional[List[str]] = None,
        components: Optional[List[str]] = None,
        custom_fields: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new Jira issue."""
        issue_data = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "issuetype": {"name": issue_type}
            }
        }
        
        # Add optional fields
        if description:
            issue_data["fields"]["description"] = description
        
        if priority:
            issue_data["fields"]["priority"] = {"name": priority}
        
        if assignee:
            issue_data["fields"]["assignee"] = {"name": assignee}
        
        if labels:
            issue_data["fields"]["labels"] = labels
        
        if components:
            issue_data["fields"]["components"] = [{"name": comp} for comp in components]
        
        if custom_fields:
            issue_data["fields"].update(custom_fields)
        
        result = await self._api_request("POST", "issue", json_data=issue_data)
        
        issue_key = result["key"]
        self.logger.info(f"Created Jira issue: {issue_key}")
        
        return issue_key
    
    async def get_issue(self, issue_key: str, expand: Optional[List[str]] = None) -> JiraIssue:
        """Get issue by key."""
        params = {}
        if expand:
            params["expand"] = ",".join(expand)
        
        issue_data = await self._api_request("GET", f"issue/{issue_key}", params=params)
        
        fields = issue_data["fields"]
        
        return JiraIssue(
            key=issue_data["key"],
            summary=fields["summary"],
            issue_type=fields["issuetype"]["name"],
            status=fields["status"]["name"],
            priority=fields["priority"]["name"],
            assignee=fields.get("assignee", {}).get("displayName"),
            reporter=fields.get("reporter", {}).get("displayName"),
            description=fields.get("description"),
            created=datetime.fromisoformat(fields["created"].replace("Z", "+00:00")),
            updated=datetime.fromisoformat(fields["updated"].replace("Z", "+00:00")),
            labels=fields.get("labels", []),
            components=[comp["name"] for comp in fields.get("components", [])],
            fix_versions=[ver["name"] for ver in fields.get("fixVersions", [])],
            affect_versions=[ver["name"] for ver in fields.get("versions", [])]
        )
    
    async def update_issue(
        self,
        issue_key: str,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[str] = None,
        assignee: Optional[str] = None,
        labels: Optional[List[str]] = None,
        components: Optional[List[str]] = None,
        custom_fields: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update existing Jira issue."""
        update_data = {"fields": {}}
        
        if summary:
            update_data["fields"]["summary"] = summary
        
        if description:
            update_data["fields"]["description"] = description
        
        if priority:
            update_data["fields"]["priority"] = {"name": priority}
        
        if assignee:
            update_data["fields"]["assignee"] = {"name": assignee}
        
        if labels:
            update_data["fields"]["labels"] = labels
        
        if components:
            update_data["fields"]["components"] = [{"name": comp} for comp in components]
        
        if custom_fields:
            update_data["fields"].update(custom_fields)
        
        if not update_data["fields"]:
            raise ValueError("No fields to update")
        
        await self._api_request("PUT", f"issue/{issue_key}", json_data=update_data)
        
        self.logger.info(f"Updated Jira issue: {issue_key}")
    
    async def delete_issue(self, issue_key: str) -> None:
        """Delete Jira issue."""
        await self._api_request("DELETE", f"issue/{issue_key}")
        self.logger.info(f"Deleted Jira issue: {issue_key}")
    
    # Issue Transitions and Workflow
    
    async def get_transitions(self, issue_key: str) -> List[Dict[str, Any]]:
        """Get available transitions for issue."""
        result = await self._api_request("GET", f"issue/{issue_key}/transitions")
        return result.get("transitions", [])
    
    async def transition_issue(
        self,
        issue_key: str,
        transition_id: str,
        comment: Optional[str] = None,
        resolution: Optional[str] = None,
        custom_fields: Optional[Dict[str, Any]] = None
    ) -> None:
        """Transition issue to new status."""
        transition_data = {
            "transition": {"id": transition_id}
        }
        
        update_fields = {}
        
        if comment:
            update_fields["comment"] = [{"add": {"body": comment}}]
        
        if resolution:
            update_fields["resolution"] = [{"set": {"name": resolution}}]
        
        if custom_fields:
            for field_name, field_value in custom_fields.items():
                update_fields[field_name] = [{"set": field_value}]
        
        if update_fields:
            transition_data["update"] = update_fields
        
        await self._api_request("POST", f"issue/{issue_key}/transitions", json_data=transition_data)
        
        self.logger.info(f"Transitioned Jira issue {issue_key} to transition {transition_id}")
    
    # Comments
    
    async def add_comment(self, issue_key: str, body: str, visibility: Optional[Dict[str, str]] = None) -> str:
        """Add comment to issue."""
        comment_data = {"body": body}
        
        if visibility:
            comment_data["visibility"] = visibility
        
        result = await self._api_request("POST", f"issue/{issue_key}/comment", json_data=comment_data)
        
        comment_id = result["id"]
        self.logger.info(f"Added comment {comment_id} to issue {issue_key}")
        
        return comment_id
    
    async def get_comments(self, issue_key: str) -> List[JiraComment]:
        """Get all comments for issue."""
        result = await self._api_request("GET", f"issue/{issue_key}/comment")
        
        comments = []
        for comment_data in result.get("comments", []):
            comment = JiraComment(
                id=comment_data["id"],
                body=comment_data["body"],
                author=comment_data["author"]["displayName"],
                created=datetime.fromisoformat(comment_data["created"].replace("Z", "+00:00")),
                updated=datetime.fromisoformat(comment_data["updated"].replace("Z", "+00:00")),
                visibility=comment_data.get("visibility")
            )
            comments.append(comment)
        
        return comments
    
    # Search and JQL
    
    async def search_issues(
        self,
        jql: str,
        max_results: int = 50,
        start_at: int = 0,
        fields: Optional[List[str]] = None
    ) -> List[JiraIssue]:
        """Search issues using JQL."""
        search_data = {
            "jql": jql,
            "maxResults": max_results,
            "startAt": start_at
        }
        
        if fields:
            search_data["fields"] = fields
        
        result = await self._api_request("POST", "search", json_data=search_data)
        
        issues = []
        for issue_data in result.get("issues", []):
            fields = issue_data["fields"]
            
            issue = JiraIssue(
                key=issue_data["key"],
                summary=fields["summary"],
                issue_type=fields["issuetype"]["name"],
                status=fields["status"]["name"],
                priority=fields["priority"]["name"],
                assignee=fields.get("assignee", {}).get("displayName"),
                reporter=fields.get("reporter", {}).get("displayName"),
                description=fields.get("description"),
                created=datetime.fromisoformat(fields["created"].replace("Z", "+00:00")),
                updated=datetime.fromisoformat(fields["updated"].replace("Z", "+00:00")),
                labels=fields.get("labels", []),
                components=[comp["name"] for comp in fields.get("components", [])],
                fix_versions=[ver["name"] for ver in fields.get("fixVersions", [])],
                affect_versions=[ver["name"] for ver in fields.get("versions", [])]
            )
            issues.append(issue)
        
        return issues
    
    # Attachments
    
    async def add_attachment(self, issue_key: str, file_path: str, filename: Optional[str] = None) -> str:
        """Add attachment to issue."""
        import os
        
        if not os.path.exists(file_path):
            raise JiraAPIError(f"File not found: {file_path}")
        
        filename = filename or os.path.basename(file_path)
        
        with open(file_path, "rb") as file:
            files = {
                "file": (filename, file, "application/octet-stream")
            }
            
            result = await self._api_request(
                "POST",
                f"issue/{issue_key}/attachments",
                files=files
            )
        
        attachment_id = result[0]["id"]
        self.logger.info(f"Added attachment {attachment_id} to issue {issue_key}")
        
        return attachment_id
    
    # Fields and Custom Fields
    
    async def get_fields(self) -> List[JiraField]:
        """Get all available fields."""
        result = await self._api_request("GET", "field")
        
        fields = []
        for field_data in result:
            field = JiraField(
                id=field_data["id"],
                name=field_data["name"],
                field_type=field_data.get("schema", {}).get("type", "unknown"),
                custom=field_data.get("custom", False),
                orderable=field_data.get("orderable", True),
                navigable=field_data.get("navigable", True),
                searchable=field_data.get("searchable", True),
                clause_names=field_data.get("clauseNames", []),
                schema=field_data.get("schema")
            )
            fields.append(field)
            self._field_cache[field.id] = field
        
        return fields
    
    # Agile and Sprint Management
    
    async def get_boards(self, project_key: Optional[str] = None, max_results: int = 50) -> List[Dict[str, Any]]:
        """Get agile boards."""
        params = {"maxResults": max_results}
        if project_key:
            params["projectKeyOrId"] = project_key
        
        result = await self._api_request("GET", "agile/1.0/board", params=params)
        return result.get("values", [])
    
    async def get_sprints(self, board_id: int, state: str = "active,future") -> List[JiraSprint]:
        """Get sprints for board."""
        params = {"state": state}
        result = await self._api_request("GET", f"agile/1.0/board/{board_id}/sprint", params=params)
        
        sprints = []
        for sprint_data in result.get("values", []):
            sprint = JiraSprint(
                id=sprint_data["id"],
                name=sprint_data["name"],
                state=sprint_data["state"],
                start_date=datetime.fromisoformat(sprint_data["startDate"].replace("Z", "+00:00")) if sprint_data.get("startDate") else None,
                end_date=datetime.fromisoformat(sprint_data["endDate"].replace("Z", "+00:00")) if sprint_data.get("endDate") else None,
                complete_date=datetime.fromisoformat(sprint_data["completeDate"].replace("Z", "+00:00")) if sprint_data.get("completeDate") else None,
                origin_board_id=sprint_data.get("originBoardId"),
                goal=sprint_data.get("goal")
            )
            sprints.append(sprint)
        
        return sprints
    
    async def move_issues_to_sprint(self, sprint_id: int, issue_keys: List[str]) -> None:
        """Move issues to sprint."""
        data = {
            "issues": issue_keys
        }
        
        await self._api_request("POST", f"agile/1.0/sprint/{sprint_id}/issue", json_data=data)
        
        self.logger.info(f"Moved {len(issue_keys)} issues to sprint {sprint_id}")
    
    # Worklog and Time Tracking
    
    async def add_worklog(
        self,
        issue_key: str,
        time_spent: str,
        comment: Optional[str] = None,
        started: Optional[datetime] = None
    ) -> str:
        """Add worklog to issue."""
        worklog_data = {"timeSpent": time_spent}
        
        if comment:
            worklog_data["comment"] = comment
        
        if started:
            worklog_data["started"] = started.isoformat()
        
        result = await self._api_request("POST", f"issue/{issue_key}/worklog", json_data=worklog_data)
        
        worklog_id = result["id"]
        self.logger.info(f"Added worklog {worklog_id} to issue {issue_key}")
        
        return worklog_id
    
    async def get_worklogs(self, issue_key: str) -> List[JiraWorklog]:
        """Get all worklogs for issue."""
        result = await self._api_request("GET", f"issue/{issue_key}/worklog")
        
        worklogs = []
        for worklog_data in result.get("worklogs", []):
            worklog = JiraWorklog(
                id=worklog_data["id"],
                time_spent=worklog_data["timeSpent"],
                time_spent_seconds=worklog_data["timeSpentSeconds"],
                author=worklog_data["author"]["displayName"],
                created=datetime.fromisoformat(worklog_data["created"].replace("Z", "+00:00")),
                updated=datetime.fromisoformat(worklog_data["updated"].replace("Z", "+00:00")),
                comment=worklog_data.get("comment"),
                started=datetime.fromisoformat(worklog_data["started"].replace("Z", "+00:00")) if worklog_data.get("started") else None
            )
            worklogs.append(worklog)
        
        return worklogs
    
    # Webhook Management
    
    async def create_webhook(
        self,
        url: str,
        events: List[str],
        jql_filter: Optional[str] = None,
        secret: Optional[str] = None
    ) -> str:
        """Create webhook for issue events."""
        webhook_data = {
            "url": url,
            "events": events
        }
        
        if jql_filter:
            webhook_data["jqlFilter"] = jql_filter
        
        if secret:
            webhook_data["secret"] = secret
            self._webhook_secret = secret
        
        result = await self._api_request("POST", "webhook", json_data=webhook_data)
        
        webhook_id = result["id"]
        self.logger.info(f"Created webhook {webhook_id} for URL {url}")
        
        return webhook_id
    
    async def delete_webhook(self, webhook_id: str) -> None:
        """Delete webhook."""
        await self._api_request("DELETE", f"webhook/{webhook_id}")
        self.logger.info(f"Deleted webhook {webhook_id}")
    
    # Event Registration
    
    def add_issue_handler(self, handler: Callable[[JiraIssue], None]) -> None:
        """Add Jira issue event handler."""
        self._issue_handlers.append(handler)
    
    def remove_issue_handler(self, handler: Callable) -> None:
        """Remove Jira issue event handler."""
        if handler in self._issue_handlers:
            self._issue_handlers.remove(handler)
    
    def verify_webhook_signature(self, payload: str, signature: str) -> bool:
        """Verify Jira webhook signature."""
        if not self._webhook_secret:
            return True  # No secret configured
        
        try:
            expected_signature = hmac.new(
                self._webhook_secret.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(expected_signature, signature)
            
        except Exception as e:
            self.logger.error(f"Webhook signature verification failed: {e}")
            return False
    
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
            server_info = await self.get_server_info()
            
            # Test user authentication
            user_info = await self.get_current_user()
            
            # Test project access
            projects = await self.get_projects(max_results=1)
            
            # Check connection state
            connected = self._connected and bool(self._user_info)
            
            # Overall health status
            is_healthy = (
                connected and
                bool(server_info) and
                bool(user_info) and
                len(projects) > 0
            )
            
            return {
                "status": "healthy" if is_healthy else "degraded",
                "api_connectivity": True,
                "user_authenticated": bool(user_info),
                "projects_accessible": len(projects) > 0,
                "connection_state": connected,
                "server_version": server_info.get("version", "Unknown"),
                "user_display_name": user_info.get("displayName", "Unknown"),
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
        self.logger.info("Closing Jira integration")
        
        # Clear caches
        self._project_cache.clear()
        self._field_cache.clear()
        
        # Close OAuth client
        if self.oauth_client:
            await self.oauth_client.close()
        
        await super().close()


# Export the integration
__all__ = ["JiraIntegration", "JiraIssue", "JiraComment", "JiraWorklog", "JiraSprint", "JiraProject", "JiraField", "JiraAPIError", "JiraRateLimitError"]