"""
Microsoft Teams integration with Bot Framework and Graph API.

Provides comprehensive Teams integration including:
- Microsoft Bot Framework integration
- Adaptive cards for rich messaging
- Channel and team management
- File sharing capabilities
- Meeting integration
- SSO with Azure AD
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
from ..base import BaseIntegrationImpl, OAuth2Client, RateLimitError
from ..config import TeamsIntegrationConfig
from . import IntegrationType

logger = get_logger(__name__)


class TeamsAPIError(ExternalServiceError):
    """Microsoft Teams API specific errors."""
    pass


class TeamsRateLimitError(RateLimitError):
    """Teams rate limit exceeded error."""
    pass


class TeamsMessage:
    """Represents a Teams message."""
    
    def __init__(
        self,
        conversation_id: str,
        text: str,
        user: Optional[str] = None,
        timestamp: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        entities: Optional[List[Dict[str, Any]]] = None
    ):
        self.conversation_id = conversation_id
        self.text = text
        self.user = user
        self.timestamp = timestamp
        self.attachments = attachments or []
        self.entities = entities or []
        self.created_at = datetime.utcnow()


class AdaptiveCard:
    """Microsoft Adaptive Card."""
    
    def __init__(self, card_data: Dict[str, Any]):
        self.card_data = card_data
        self.version = card_data.get("version", "1.3")
        self.type = "AdaptiveCard"


class TeamsIntegration(BaseIntegrationImpl):
    """Microsoft Teams integration with Bot Framework and Graph API."""
    
    def __init__(self, config: TeamsIntegrationConfig):
        super().__init__(IntegrationType.TEAMS, config.dict())
        
        self.teams_config = config
        self.logger = logger.getChild("teams")
        
        # Microsoft Graph API configuration
        self.graph_base_url = "https://graph.microsoft.com/v1.0"
        self.bot_framework_url = "https://smba.trafficmanager.net/amer"
        
        # OAuth client for Graph API
        self.graph_oauth_client = self._create_graph_oauth_client()
        
        # Bot state tracking
        self._service_url: Optional[str] = None
        self._conversation_references: Dict[str, Dict[str, Any]] = {}
        self._message_handlers: List[Callable] = []
        
        # Connection state
        self._connected = False
        self._bot_info: Dict[str, Any] = {}
        self._team_info: Dict[str, Any] = {}
        
        # Rate limiting
        self._rate_limit_info = {
            "remaining": 10000,  # Graph API default
            "reset": None,
            "retry_after": None
        }
    
    # Authentication and Connection
    
    async def authenticate(self) -> bool:
        """Authenticate with Microsoft Graph API."""
        try:
            # Test Graph API connectivity
            me = await self._graph_request("GET", "me")
            
            self.logger.info(f"Authenticated as {me.get('displayName', 'Unknown')}")
            
            # Get bot information
            bot_info = await self._graph_request("GET", f"applications/{self.teams_config.app_id}")
            self._bot_info = bot_info
            
            self.logger.info(f"Bot info: {bot_info.get('displayName', 'Unknown')}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Teams authentication failed: {e}")
            raise TeamsAPIError(f"Authentication failed: {e}")
    
    def _create_graph_oauth_client(self) -> OAuth2Client:
        """Create OAuth 2.0 client for Microsoft Graph."""
        from ..base import OAuth2Config
        
        oauth_config = OAuth2Config(
            client_id=self.teams_config.app_id,
            client_secret=self.teams_config.app_password,
            authorization_url="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
            token_url="https://login.microsoftonline.com/common/oauth2/v2.0/token",
            redirect_uri="https://your-app.com/auth/teams/callback",
            scope="https://graph.microsoft.com/.default"
        )
        
        return OAuth2Client(oauth_config)
    
    async def _graph_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to Microsoft Graph API."""
        url = f"{self.graph_base_url}/{endpoint.lstrip('/')}"
        
        # Get valid access token
        access_token = await self.graph_oauth_client.get_valid_access_token()
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method.upper() == "GET":
                    response = await client.get(url, params=params, headers=headers)
                elif method.upper() == "POST":
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
                    raise TeamsRateLimitError(
                        f"Teams rate limit exceeded. Retry after {retry_after}s",
                        IntegrationType.TEAMS,
                        {"retry_after": retry_after}
                    )
                
                response.raise_for_status()
                
                # Update rate limit info
                self._update_rate_limit_info(response)
                
                return response.json() if response.content else {}
                
        except httpx.RequestError as e:
            self.logger.error(f"Teams request error: {e}")
            raise TeamsAPIError(f"Request failed: {e}")
    
    def _update_rate_limit_info(self, response: httpx.Response) -> None:
        """Update rate limit information from response headers."""
        # Extract rate limit info from headers if available
        remaining = response.headers.get("RateLimit-Remaining")
        reset = response.headers.get("RateLimit-Reset")
        
        if remaining:
            self._rate_limit_info["remaining"] = int(remaining)
        
        if reset:
            self._rate_limit_info["reset"] = int(reset)
    
    # Bot Framework Integration
    
    async def send_bot_message(
        self,
        conversation_id: str,
        text: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
        suggested_actions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Send message through Bot Framework."""
        message_data = {
            "type": "message",
            "timestamp": datetime.utcnow().isoformat(),
            "text": text,
            "from": {
                "id": self.teams_config.app_id,
                "name": self._bot_info.get("displayName", "AI Assistant")
            },
            "recipient": {
                "id": "user",
                "name": "User"
            },
            "conversation": {
                "id": conversation_id
            }
        }
        
        if attachments:
            message_data["attachments"] = attachments
        
        if suggested_actions:
            message_data["suggestedActions"] = {
                "actions": [
                    {"type": "imBack", "title": action, "value": action}
                    for action in suggested_actions
                ]
            }
        
        # Use stored conversation reference if available
        conversation_ref = self._conversation_references.get(conversation_id)
        if conversation_ref:
            service_url = conversation_ref.get("serviceUrl", self._service_url)
        else:
            service_url = self._service_url or self.bot_framework_url
        
        if not service_url:
            raise TeamsAPIError("No service URL available for bot message")
        
        url = f"{service_url}/v3/conversations/{conversation_id}/activities"
        
        # Use direct HTTP client for Bot Framework
        headers = {
            "Authorization": f"Bearer {await self._get_bot_access_token()}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=message_data, headers=headers)
            response.raise_for_status()
            
            return response.json()
    
    async def _get_bot_access_token(self) -> str:
        """Get access token for Bot Framework."""
        # Bot Framework uses Microsoft App credentials
        from ..base import OAuth2Config
        
        bot_oauth_config = OAuth2Config(
            client_id=self.teams_config.app_id,
            client_secret=self.teams_config.app_password,
            authorization_url="https://login.microsoftonline.com/botframework/oauth2/v2.0/authorize",
            token_url="https://login.microsoftonline.com/botframework/oauth2/v2.0/token",
            redirect_uri="https://token.botframework.com/.auth/web/redirect",
            scope="https://api.botframework.com/.default"
        )
        
        bot_oauth_client = OAuth2Client(bot_oauth_config)
        return await bot_oauth_client.get_valid_access_token()
    
    # Adaptive Cards
    
    async def send_adaptive_card(
        self,
        conversation_id: str,
        card: AdaptiveCard,
        text_fallback: str = "Card message"
    ) -> Dict[str, Any]:
        """Send adaptive card message."""
        if not self.teams_config.enable_message_reactions:
            raise TeamsAPIError("Adaptive cards are not enabled")
        
        attachment = {
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": card.card_data
        }
        
        return await self.send_bot_message(
            conversation_id=conversation_id,
            text=text_fallback,
            attachments=[attachment]
        )
    
    def create_adaptive_card(
        self,
        title: str,
        body: List[Dict[str, Any]],
        actions: Optional[List[Dict[str, Any]]] = None
    ) -> AdaptiveCard:
        """Create adaptive card."""
        card_data = {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.3",
            "body": [
                {
                    "type": "TextBlock",
                    "text": title,
                    "size": "Large",
                    "weight": "Bolder"
                },
                *body
            ]
        }
        
        if actions:
            card_data["actions"] = actions
        
        return AdaptiveCard(card_data)
    
    # Channel and Team Management
    
    async def get_team_info(self, team_id: str) -> Dict[str, Any]:
        """Get team information."""
        return await self._graph_request("GET", f"teams/{team_id}")
    
    async def get_channel_info(self, team_id: str, channel_id: str) -> Dict[str, Any]:
        """Get channel information."""
        return await self._graph_request("GET", f"teams/{team_id}/channels/{channel_id}")
    
    async def get_channels(self, team_id: str) -> List[Dict[str, Any]]:
        """Get all channels in a team."""
        result = await self._graph_request("GET", f"teams/{team_id}/channels")
        return result.get("value", [])
    
    async def create_channel(
        self,
        team_id: str,
        name: str,
        description: Optional[str] = None,
        channel_type: str = "standard"
    ) -> Dict[str, Any]:
        """Create new channel in team."""
        channel_data = {
            "displayName": name,
            "description": description or "",
            "membershipType": channel_type
        }
        
        return await self._graph_request("POST", f"teams/{team_id}/channels", json_data=channel_data)
    
    async def delete_channel(self, team_id: str, channel_id: str) -> Dict[str, Any]:
        """Delete channel from team."""
        return await self._graph_request("DELETE", f"teams/{team_id}/channels/{channel_id}")
    
    async def get_team_members(self, team_id: str) -> List[Dict[str, Any]]:
        """Get team members."""
        result = await self._graph_request("GET", f"groups/{team_id}/members")
        return result.get("value", [])
    
    async def add_team_member(self, team_id: str, user_id: str) -> Dict[str, Any]:
        """Add member to team."""
        member_data = {
            "@odata.id": f"https://graph.microsoft.com/v1.0/users/{user_id}"
        }
        
        return await self._graph_request("POST", f"groups/{team_id}/members/$ref", json_data=member_data)
    
    # File Operations
    
    async def upload_file(
        self,
        team_id: str,
        channel_id: str,
        file_path: str,
        file_name: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upload file to Teams channel."""
        if not self.teams_config.enable_file_sharing:
            raise TeamsAPIError("File sharing is not enabled")
        
        import os
        
        if not os.path.exists(file_path):
            raise TeamsAPIError(f"File not found: {file_path}")
        
        # Create upload session
        upload_data = {
            "item": {
                "@microsoft.graph.conflictBehavior": "rename",
                "name": file_name,
                "description": description or ""
            }
        }
        
        upload_session = await self._graph_request(
            "POST",
            f"teams/{team_id}/channels/{channel_id}/filesFolder/driveItem/createUploadSession",
            json_data=upload_data
        )
        
        upload_url = upload_session.get("uploadUrl")
        if not upload_url:
            raise TeamsAPIError("Failed to create upload session")
        
        # Upload file in chunks
        file_size = os.path.getsize(file_path)
        chunk_size = 4 * 1024 * 1024  # 4MB chunks
        
        with open(file_path, "rb") as file:
            offset = 0
            while offset < file_size:
                chunk = file.read(chunk_size)
                chunk_end = offset + len(chunk) - 1
                
                headers = {
                    "Content-Length": str(len(chunk)),
                    "Content-Range": f"bytes {offset}-{chunk_end}/{file_size}"
                }
                
                async with httpx.AsyncClient() as client:
                    response = await client.put(upload_url, content=chunk, headers=headers)
                    response.raise_for_status()
                
                offset += len(chunk)
        
        return {"status": "completed", "file_name": file_name}
    
    async def get_files(self, team_id: str, channel_id: str) -> List[Dict[str, Any]]:
        """Get files in channel."""
        result = await self._graph_request("GET", f"teams/{team_id}/channels/{channel_id}/filesFolder/children")
        return result.get("value", [])
    
    # Meeting Integration
    
    async def create_online_meeting(
        self,
        subject: str,
        start_datetime: datetime,
        end_datetime: datetime,
        attendees: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create online meeting."""
        if not self.teams_config.enable_meeting_integration:
            raise TeamsAPIError("Meeting integration is not enabled")
        
        meeting_data = {
            "subject": subject,
            "start": {
                "dateTime": start_datetime.isoformat(),
                "timeZone": "UTC"
            },
            "end": {
                "dateTime": end_datetime.isoformat(),
                "timeZone": "UTC"
            }
        }
        
        if attendees:
            meeting_data["attendees"] = [
                {"emailAddress": {"address": email}} for email in attendees
            ]
        
        return await self._graph_request("POST", "me/onlineMeetings", json_data=meeting_data)
    
    async def get_meeting_info(self, meeting_id: str) -> Dict[str, Any]:
        """Get meeting information."""
        return await self._graph_request("GET", f"me/onlineMeetings/{meeting_id}")
    
    # SSO and Authentication
    
    async def get_user_profile(self) -> Dict[str, Any]:
        """Get current user profile."""
        return await self._graph_request("GET", "me")
    
    async def get_user_photo(self, user_id: str) -> bytes:
        """Get user photo."""
        result = await self._graph_request("GET", f"users/{user_id}/photo/$value")
        return result if isinstance(result, bytes) else b""
    
    async def get_user_calendar(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get user calendar events."""
        params = {
            "startDateTime": start_date.isoformat(),
            "endDateTime": end_date.isoformat()
        }
        
        result = await self._graph_request("GET", "me/calendarview", params=params)
        return result.get("value", [])
    
    # Rate Limiting
    
    async def check_rate_limit(self) -> Dict[str, Any]:
        """Check current rate limit status."""
        # Graph API doesn't provide rate limit headers consistently
        # This is a placeholder for rate limit checking
        return {
            "remaining": self._rate_limit_info["remaining"],
            "reset_time": self._rate_limit_info["reset"],
            "retry_after": self._rate_limit_info["retry_after"]
        }
    
    # Event Registration
    
    def add_message_handler(self, handler: Callable[[TeamsMessage], None]) -> None:
        """Add message event handler."""
        self._message_handlers.append(handler)
    
    def remove_message_handler(self, handler: Callable) -> None:
        """Remove message event handler."""
        if handler in self._message_handlers:
            self._message_handlers.remove(handler)
    
    def _handle_message(self, message: TeamsMessage) -> None:
        """Handle incoming message."""
        # Skip bot messages
        if message.user and message.user == self.teams_config.app_id:
            return
        
        # Call registered message handlers
        for handler in self._message_handlers:
            try:
                handler(message)
            except Exception as e:
                self.logger.error(f"Error in message handler: {e}")
    
    # Verification and Security
    
    def verify_request_authorization(self, authorization_header: str) -> bool:
        """Verify Teams request authorization."""
        if not authorization_header.startswith("Bearer "):
            return False
        
        token = authorization_header[7:]  # Remove "Bearer "
        
        # Verify JWT token
        try:
            # This would validate the JWT token from Teams
            # For now, just check if token matches bot credentials
            return token == await self._get_bot_access_token()
        except Exception as e:
            self.logger.error(f"Authorization verification failed: {e}")
            return False
    
    # Health Check
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        try:
            # Test Graph API connectivity
            me = await self._graph_request("GET", "me")
            
            # Test bot info
            bot_info = await self._graph_request("GET", f"applications/{self.teams_config.app_id}")
            
            # Check connection state
            connected = self._connected and bool(self._bot_info)
            
            # Check rate limit status
            rate_limited = self.is_rate_limited()
            
            return {
                "status": "healthy",
                "graph_api_connectivity": True,
                "bot_authenticated": True,
                "connection_state": connected,
                "bot_display_name": bot_info.get("displayName", "Unknown"),
                "tenant_id": self.teams_config.tenant_id,
                "rate_limited": rate_limited,
                "rate_limit_remaining": self._rate_limit_info["remaining"],
                "last_check": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "graph_api_connectivity": False,
                "bot_authenticated": False,
                "connection_state": False,
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
    
    def is_rate_limited(self) -> bool:
        """Check if currently rate limited."""
        return (
            self._rate_limit_info["remaining"] <= 0 or
            self._rate_limit_info["retry_after"] is not None
        )
    
    async def close(self) -> None:
        """Close integration and cleanup resources."""
        self.logger.info("Closing Teams integration")
        
        # Close OAuth client
        if self.graph_oauth_client:
            await self.graph_oauth_client.close()
        
        await super().close()


# Export the integration
__all__ = ["TeamsIntegration", "TeamsMessage", "AdaptiveCard", "TeamsAPIError", "TeamsRateLimitError"]