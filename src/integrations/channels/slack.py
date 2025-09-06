"""
Slack integration with real-time messaging and interactive components.

Provides comprehensive Slack Bot integration including:
- OAuth 2.0 authentication with bot tokens
- Real-time messaging via RTM/WebSocket
- Interactive message components (buttons, menus)
- File upload and download support
- User presence and typing indicators
- Channel management and slash commands
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, AsyncGenerator, Callable
from urllib.parse import urlencode, quote
import httpx
import websocket

from src.core.config import get_settings
from src.core.logging import get_logger
from src.core.exceptions import ExternalServiceError
from ..base import BaseIntegrationImpl, RateLimitError
from ..config import SlackIntegrationConfig
from . import IntegrationType

logger = get_logger(__name__)


class SlackAPIError(ExternalServiceError):
    """Slack API specific errors."""
    pass


class SlackRateLimitError(RateLimitError):
    """Slack rate limit exceeded error."""
    pass


class SlackMessage:
    """Represents a Slack message."""
    
    def __init__(
        self,
        channel: str,
        text: str,
        user: Optional[str] = None,
        timestamp: Optional[str] = None,
        thread_ts: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        blocks: Optional[List[Dict[str, Any]]] = None
    ):
        self.channel = channel
        self.text = text
        self.user = user
        self.timestamp = timestamp
        self.thread_ts = thread_ts
        self.attachments = attachments or []
        self.blocks = blocks or []
        self.created_at = datetime.utcnow()


class SlackIntegration(BaseIntegrationImpl):
    """Slack Bot integration with comprehensive functionality."""
    
    def __init__(self, config: SlackIntegrationConfig):
        super().__init__(IntegrationType.SLACK, config.dict())
        
        self.slack_config = config
        self.logger = logger.getChild("slack")
        
        # Slack API configuration
        self.api_base_url = "https://slack.com/api"
        self.rtm_url: Optional[str] = None
        self.ws_client: Optional[websocket.WebSocket] = None
        self._ws_task: Optional[asyncio.Task] = None
        self._message_handlers: List[Callable] = []
        self._event_handlers: Dict[str, List[Callable]] = {}
        
        # Rate limiting
        self._rate_limit_info = {
            "remaining": 50,  # Default for most methods
            "reset": None,
            "retry_after": None
        }
        
        # Connection state
        self._connected = False
        self._connection_info: Dict[str, Any] = {}
        self._bot_user_id: Optional[str] = None
        self._bot_user_name: Optional[str] = None
        
        # Message queue for rate limiting
        self._message_queue = asyncio.Queue()
        self._message_processor_task: Optional[asyncio.Task] = None
    
    # Authentication and Connection
    
    async def authenticate(self) -> bool:
        """Authenticate with Slack API."""
        try:
            # Test API connectivity
            auth_test = await self._api_request("GET", "auth.test")
            
            self._bot_user_id = auth_test["user_id"]
            self._bot_user_name = auth_test["user"]
            self._connection_info = auth_test
            
            self.logger.info(f"Authenticated as {self._bot_user_name} ({self._bot_user_id})")
            
            # Get bot info
            bot_info = await self._api_request("GET", "bots.info", params={"bot": self._bot_user_id})
            self.logger.info(f"Bot info: {bot_info}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Slack authentication failed: {e}")
            raise SlackAPIError(f"Authentication failed: {e}")
    
    async def _api_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to Slack API."""
        url = f"{self.api_base_url}/{endpoint}"
        
        # Add authentication token
        headers = {
            "Authorization": f"Bearer {self.slack_config.bot_token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method.upper() == "GET":
                    response = await client.get(url, params=params, headers=headers)
                elif method.upper() == "POST":
                    if files:
                        # For file uploads, don't set Content-Type header
                        headers.pop("Content-Type", None)
                        response = await client.post(url, data=json_data, files=files, headers=headers)
                    else:
                        response = await client.post(url, json=json_data, headers=headers)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                # Check for rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    self._rate_limit_info["retry_after"] = retry_after
                    raise SlackRateLimitError(
                        f"Slack rate limit exceeded. Retry after {retry_after}s",
                        IntegrationType.SLACK,
                        {"retry_after": retry_after}
                    )
                
                response.raise_for_status()
                
                # Update rate limit info
                self._update_rate_limit_info(response)
                
                result = response.json()
                
                # Check Slack API response
                if not result.get("ok", False):
                    error = result.get("error", "Unknown error")
                    self.logger.error(f"Slack API error: {error}")
                    raise SlackAPIError(f"Slack API error: {error}")
                
                return result
                
        except httpx.RequestError as e:
            self.logger.error(f"Slack request error: {e}")
            raise SlackAPIError(f"Request failed: {e}")
    
    def _update_rate_limit_info(self, response: httpx.Response) -> None:
        """Update rate limit information from response headers."""
        # Extract rate limit info from headers if available
        remaining = response.headers.get("X-RateLimit-Remaining")
        reset = response.headers.get("X-RateLimit-Reset")
        
        if remaining:
            self._rate_limit_info["remaining"] = int(remaining)
        
        if reset:
            self._rate_limit_info["reset"] = int(reset)
    
    # Real-time Messaging (RTM/WebSocket)
    
    async def connect_rtm(self) -> bool:
        """Connect to Slack RTM API for real-time messaging."""
        if not self.slack_config.enable_socket_mode:
            self.logger.info("Socket mode not enabled, using HTTP-based events")
            return True
        
        try:
            # Get RTM connection info
            rtm_response = await self._api_request("GET", "rtm.connect")
            
            self.rtm_url = rtm_response["url"]
            self._connection_info = rtm_response
            
            self.logger.info(f"RTM connection established: {self.rtm_url}")
            
            # Start WebSocket connection
            await self._start_websocket()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect RTM: {e}")
            return False
    
    async def _start_websocket(self) -> None:
        """Start WebSocket connection for RTM."""
        if not self.rtm_url:
            raise SlackAPIError("No RTM URL available")
        
        try:
            # Connect to WebSocket
            self.ws_client = websocket.create_connection(self.rtm_url)
            self._connected = True
            
            self.logger.info("WebSocket connection established")
            
            # Start message processing task
            if self._ws_task:
                self._ws_task.cancel()
            
            self._ws_task = asyncio.create_task(self._process_websocket_messages())
            
        except Exception as e:
            self.logger.error(f"Failed to start WebSocket: {e}")
            raise SlackAPIError(f"WebSocket connection failed: {e}")
    
    async def _process_websocket_messages(self) -> None:
        """Process incoming WebSocket messages."""
        while self._connected and self.ws_client:
            try:
                # Receive message with timeout
                message = self.ws_client.recv()
                
                if message:
                    event_data = json.loads(message)
                    await self._handle_rtm_event(event_data)
                
            except websocket.WebSocketTimeoutException:
                # Timeout is normal, continue
                continue
            except websocket.WebSocketConnectionClosedException:
                self.logger.warning("WebSocket connection closed")
                break
            except Exception as e:
                self.logger.error(f"Error processing WebSocket message: {e}")
                await asyncio.sleep(1)  # Brief pause before retry
    
    async def _handle_rtm_event(self, event_data: Dict[str, Any]) -> None:
        """Handle real-time messaging event."""
        event_type = event_data.get("type", "")
        
        self.logger.debug(f"Received RTM event: {event_type}")
        
        if event_type == "message":
            await self._handle_message_event(event_data)
        elif event_type == "user_typing":
            await self._handle_typing_event(event_data)
        elif event_type == "presence_change":
            await self._handle_presence_event(event_data)
        elif event_type == "reaction_added":
            await self._handle_reaction_event(event_data)
        
        # Call registered event handlers
        if event_type in self._event_handlers:
            for handler in self._event_handlers[event_type]:
                try:
                    await handler(event_data)
                except Exception as e:
                    self.logger.error(f"Error in event handler {handler.__name__}: {e}")
    
    # Message Handling
    
    async def send_message(
        self,
        channel: str,
        text: str,
        thread_ts: Optional[str] = None,
        blocks: Optional[List[Dict[str, Any]]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send message to Slack channel."""
        message_data = {
            "channel": channel,
            "text": text,
            "as_user": True
        }
        
        if thread_ts:
            message_data["thread_ts"] = thread_ts
        
        if blocks:
            message_data["blocks"] = blocks
        
        if attachments:
            message_data["attachments"] = attachments
        
        if metadata:
            message_data["metadata"] = metadata
        
        # Add to message queue for rate limiting
        return await self._queue_message("chat.postMessage", message_data)
    
    async def _queue_message(self, method: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Queue message for rate-limited sending."""
        await self._message_queue.put({
            "method": method,
            "data": data,
            "timestamp": datetime.utcnow()
        })
        
        # Return a promise-like response
        return {"queued": True, "timestamp": datetime.utcnow().isoformat()}
    
    async def _process_message_queue(self) -> None:
        """Process queued messages with rate limiting."""
        while True:
            try:
                message = await self._message_queue.get()
                
                # Check rate limit
                if self.rate_limiter:
                    allowed = await self.rate_limiter.is_allowed("slack_messages")
                    if not allowed:
                        retry_after = await self.rate_limiter.get_retry_after("slack_messages")
                        self.logger.warning(f"Rate limited, retrying after {retry_after}s")
                        await asyncio.sleep(retry_after)
                        continue
                
                # Send message
                result = await self._api_request(
                    "POST",
                    message["method"],
                    json_data=message["data"]
                )
                
                self.logger.debug(f"Message sent: {result}")
                
                # Brief pause to respect rate limits
                await asyncio.sleep(1)  # Slack rate limit: 1 message per second
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error processing message queue: {e}")
                await asyncio.sleep(1)
    
    async def _handle_message_event(self, event_data: Dict[str, Any]) -> None:
        """Handle incoming message event."""
        # Skip bot messages
        if event_data.get("bot_id") or event_data.get("user") == self._bot_user_id:
            return
        
        # Create SlackMessage object
        message = SlackMessage(
            channel=event_data["channel"],
            text=event_data.get("text", ""),
            user=event_data.get("user"),
            timestamp=event_data.get("ts"),
            thread_ts=event_data.get("thread_ts"),
            attachments=event_data.get("attachments"),
            blocks=event_data.get("blocks")
        )
        
        # Call registered message handlers
        for handler in self._message_handlers:
            try:
                await handler(message)
            except Exception as e:
                self.logger.error(f"Error in message handler: {e}")
    
    async def _handle_typing_event(self, event_data: Dict[str, Any]) -> None:
        """Handle typing indicator event."""
        self.logger.debug(f"User {event_data.get('user')} is typing in channel {event_data.get('channel')}")
    
    async def _handle_presence_event(self, event_data: Dict[str, Any]) -> None:
        """Handle presence change event."""
        self.logger.debug(f"Presence change: {event_data.get('user')} is now {event_data.get('presence')}")
    
    async def _handle_reaction_event(self, event_data: Dict[str, Any]) -> None:
        """Handle reaction event."""
        self.logger.debug(f"Reaction {event_data.get('reaction')} added by {event_data.get('user')}")
    
    # Interactive Components
    
    async def send_interactive_message(
        self,
        channel: str,
        text: str,
        blocks: List[Dict[str, Any]],
        thread_ts: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send interactive message with blocks."""
        if not self.slack_config.enable_interactive_components:
            raise SlackAPIError("Interactive components are not enabled")
        
        message_data = {
            "channel": channel,
            "text": text,
            "blocks": blocks,
            "as_user": True
        }
        
        if thread_ts:
            message_data["thread_ts"] = thread_ts
        
        return await self._api_request("POST", "chat.postMessage", json_data=message_data)
    
    async def update_message(
        self,
        channel: str,
        timestamp: str,
        text: Optional[str] = None,
        blocks: Optional[List[Dict[str, Any]]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Update existing message."""
        update_data = {
            "channel": channel,
            "ts": timestamp
        }
        
        if text:
            update_data["text"] = text
        
        if blocks:
            update_data["blocks"] = blocks
        
        if attachments:
            update_data["attachments"] = attachments
        
        return await self._api_request("POST", "chat.update", json_data=update_data)
    
    async def add_reaction(self, channel: str, timestamp: str, reaction: str) -> Dict[str, Any]:
        """Add reaction to message."""
        reaction_data = {
            "channel": channel,
            "timestamp": timestamp,
            "name": reaction
        }
        
        return await self._api_request("POST", "reactions.add", json_data=reaction_data)
    
    # Channel Management
    
    async def get_channel_info(self, channel: str) -> Dict[str, Any]:
        """Get channel information."""
        return await self._api_request("GET", "conversations.info", params={"channel": channel})
    
    async def get_channel_members(self, channel: str) -> List[str]:
        """Get channel members list."""
        members = []
        cursor = None
        
        while True:
            params = {"channel": channel, "limit": 200}
            if cursor:
                params["cursor"] = cursor
            
            result = await self._api_request("GET", "conversations.members", params=params)
            members.extend(result.get("members", []))
            
            cursor = result.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break
        
        return members
    
    async def join_channel(self, channel: str) -> Dict[str, Any]:
        """Join channel."""
        return await self._api_request("POST", "conversations.join", json_data={"channel": channel})
    
    async def leave_channel(self, channel: str) -> Dict[str, Any]:
        """Leave channel."""
        return await self._api_request("POST", "conversations.leave", json_data={"channel": channel})
    
    async def create_channel(
        self,
        name: str,
        is_private: bool = False,
        team_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create new channel."""
        channel_data = {
            "name": name,
            "is_private": is_private
        }
        
        if team_id:
            channel_data["team_id"] = team_id
        
        return await self._api_request("POST", "conversations.create", json_data=channel_data)
    
    # File Operations
    
    async def upload_file(
        self,
        file_path: str,
        channels: List[str],
        title: Optional[str] = None,
        comment: Optional[str] = None,
        thread_ts: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upload file to Slack."""
        if not self.slack_config.enable_file_sharing:
            raise SlackAPIError("File sharing is not enabled")
        
        import os
        
        if not os.path.exists(file_path):
            raise SlackAPIError(f"File not found: {file_path}")
        
        upload_data = {
            "channels": ",".join(channels)
        }
        
        if title:
            upload_data["title"] = title
        
        if comment:
            upload_data["initial_comment"] = comment
        
        if thread_ts:
            upload_data["thread_ts"] = thread_ts
        
        files = {
            "file": open(file_path, "rb")
        }
        
        try:
            result = await self._api_request("POST", "files.upload", json_data=upload_data, files=files)
            return result
        finally:
            files["file"].close()
    
    async def get_file_info(self, file_id: str) -> Dict[str, Any]:
        """Get file information."""
        return await self._api_request("GET", "files.info", params={"file": file_id})
    
    # User Management
    
    async def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """Get user information."""
        return await self._api_request("GET", "users.info", params={"user": user_id})
    
    async def get_user_presence(self, user_id: str) -> Dict[str, Any]:
        """Get user presence status."""
        return await self._api_request("GET", "users.getPresence", params={"user": user_id})
    
    async def set_user_presence(self, presence: str) -> Dict[str, Any]:
        """Set user presence status."""
        return await self._api_request("POST", "users.setPresence", json_data={"presence": presence})
    
    # Slash Commands
    
    async def respond_to_slash_command(
        self,
        response_url: str,
        text: str,
        blocks: Optional[List[Dict[str, Any]]] = None,
        ephemeral: bool = False
    ) -> Dict[str, Any]:
        """Respond to slash command."""
        response_data = {
            "text": text,
            "response_type": "ephemeral" if ephemeral else "in_channel"
        }
        
        if blocks:
            response_data["blocks"] = blocks
        
        # Use direct HTTP client for response URL
        async with httpx.AsyncClient() as client:
            response = await client.post(response_url, json=response_data)
            response.raise_for_status()
            
            return response.json()
    
    # Event Registration
    
    def add_message_handler(self, handler: Callable[[SlackMessage], None]) -> None:
        """Add message event handler."""
        self._message_handlers.append(handler)
    
    def add_event_handler(self, event_type: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Add event handler for specific event type."""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
    
    def remove_event_handler(self, event_type: str, handler: Callable) -> None:
        """Remove event handler."""
        if event_type in self._event_handlers:
            self._event_handlers[event_type].remove(handler)
    
    # Verification and Security
    
    def verify_request_signature(self, request_body: str, timestamp: str, signature: str) -> bool:
        """Verify Slack request signature."""
        try:
            # Create base string
            basestring = f"v0:{timestamp}:{request_body}"
            
            # Create signature
            expected_signature = "v0=" + hmac.new(
                self.slack_config.signing_secret.encode(),
                basestring.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures
            return hmac.compare_digest(expected_signature, signature)
            
        except Exception as e:
            self.logger.error(f"Signature verification failed: {e}")
            return False
    
    def is_rate_limited(self) -> bool:
        """Check if currently rate limited."""
        return (
            self._rate_limit_info["remaining"] <= 0 or
            self._rate_limit_info["retry_after"] is not None
        )
    
    async def wait_for_rate_limit_reset(self) -> None:
        """Wait for rate limit to reset."""
        if self._rate_limit_info["retry_after"]:
            await asyncio.sleep(self._rate_limit_info["retry_after"])
            self._rate_limit_info["retry_after"] = None
    
    # Health Check
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        try:
            # Test API connectivity
            auth_test = await self._api_request("GET", "auth.test")
            
            # Test chat functionality
            test_message = await self._api_request("GET", "conversations.list", params={"limit": 1})
            
            # Check connection state
            ws_connected = self._connected and self.ws_client is not None
            
            # Check rate limit status
            rate_limited = self.is_rate_limited()
            
            return {
                "status": "healthy",
                "api_connectivity": True,
                "websocket_connected": ws_connected,
                "bot_user": self._bot_user_name,
                "rate_limited": rate_limited,
                "rate_limit_remaining": self._rate_limit_info["remaining"],
                "connection_info": self._connection_info,
                "last_check": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "api_connectivity": False,
                "websocket_connected": False,
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
    
    async def close(self) -> None:
        """Close integration and cleanup resources."""
        self.logger.info("Closing Slack integration")
        
        # Stop WebSocket processing
        if self._ws_task:
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass
        
        # Close WebSocket connection
        if self.ws_client:
            self.ws_client.close()
            self._connected = False
        
        # Stop message processor
        if self._message_processor_task:
            self._message_processor_task.cancel()
            try:
                await self._message_processor_task
            except asyncio.CancelledError:
                pass
        
        await super().close()


# Export the integration
__all__ = ["SlackIntegration", "SlackMessage", "SlackAPIError", "SlackRateLimitError"]