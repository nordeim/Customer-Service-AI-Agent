"""
WhatsApp Business API integration with message templates and media support.

Provides comprehensive WhatsApp Business integration including:
- WhatsApp Business API client
- Message template management
- Media message support (images, videos, documents)
- Business profile management
- Message status tracking
- Webhook verification and processing
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, AsyncGenerator
from urllib.parse import urlencode, quote
import httpx

from src.core.config import get_settings
from src.core.logging import get_logger
from src.core.exceptions import ExternalServiceError
from ..base import BaseIntegrationImpl, RateLimitError
from ..config import BaseIntegrationConfig
from . import IntegrationType

logger = get_logger(__name__)


class WhatsAppAPIError(ExternalServiceError):
    """WhatsApp Business API specific errors."""
    pass


class WhatsAppRateLimitError(RateLimitError):
    """WhatsApp rate limit exceeded error."""
    pass


class WhatsAppMessage:
    """Represents a WhatsApp message."""
    
    def __init__(
        self,
        message_id: str,
        phone_number: str,
        text: str,
        message_type: str = "text",
        timestamp: Optional[datetime] = None,
        status: str = "sent",
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.message_id = message_id
        self.phone_number = phone_number
        self.text = text
        self.message_type = message_type
        self.timestamp = timestamp or datetime.utcnow()
        self.status = status
        self.metadata = metadata or {}


class WhatsAppMedia:
    """Represents WhatsApp media (image, video, document, etc.)."""
    
    def __init__(
        self,
        media_id: str,
        media_type: str,
        mime_type: str,
        caption: Optional[str] = None,
        filename: Optional[str] = None,
        sha256: Optional[str] = None
    ):
        self.media_id = media_id
        self.media_type = media_type
        self.mime_type = mime_type
        self.caption = caption
        self.filename = filename
        self.sha256 = sha256


class WhatsAppTemplate:
    """WhatsApp message template."""
    
    def __init__(
        self,
        name: str,
        language: str,
        category: str,
        components: List[Dict[str, Any]]
    ):
        self.name = name
        self.language = language
        self.category = category
        self.components = components


class WhatsAppIntegration(BaseIntegrationImpl):
    """WhatsApp Business API integration."""
    
    def __init__(self, config: BaseIntegrationConfig):
        super().__init__(IntegrationType.WHATSAPP, config.dict())
        
        self.whatsapp_config = config
        self.logger = logger.getChild("whatsapp")
        
        # WhatsApp Business API configuration
        self.api_version = "v18.0"
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        
        # Business account info
        self.business_account_id = None  # Will be set after authentication
        self.phone_number_id = None  # Will be set after authentication
        
        # Rate limiting
        self._rate_limit_info = {
            "remaining": 1000,  # Default for WhatsApp Business API
            "reset": None,
            "retry_after": None
        }
        
        # Message tracking
        self._message_handlers: List[Callable] = []
        self._template_cache: Dict[str, WhatsAppTemplate] = {}
        
        # Connection state
        self._connected = False
        self._business_profile: Dict[str, Any] = {}
        self._phone_numbers: List[Dict[str, Any]] = []
    
    # Authentication and Setup
    
    async def authenticate(self) -> bool:
        """Authenticate with WhatsApp Business API."""
        try:
            # Get business account info
            business_info = await self._api_request("GET", "me")
            self.business_account_id = business_info.get("id")
            
            # Get phone numbers associated with the business account
            phone_numbers = await self._api_request(
                "GET",
                f"{self.business_account_id}/phone_numbers"
            )
            
            self._phone_numbers = phone_numbers.get("data", [])
            if self._phone_numbers:
                self.phone_number_id = self._phone_numbers[0]["id"]
            
            # Get business profile
            if self.phone_number_id:
                self._business_profile = await self._get_business_profile()
            
            self.logger.info(f"Authenticated with WhatsApp Business API. Account ID: {self.business_account_id}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"WhatsApp authentication failed: {e}")
            raise WhatsAppAPIError(f"Authentication failed: {e}")
    
    async def _api_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to WhatsApp Business API."""
        url = f"{self.base_url}/{endpoint}"
        
        # Add access token
        headers = {
            "Authorization": f"Bearer {self.whatsapp_config.bot_token}",
            "Content-Type": "application/json"
        }
        
        # Remove Content-Type header for file uploads
        if files:
            headers.pop("Content-Type", None)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method.upper() == "GET":
                    response = await client.get(url, params=params, headers=headers)
                elif method.upper() == "POST":
                    if files:
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
                    raise WhatsAppRateLimitError(
                        f"WhatsApp rate limit exceeded. Retry after {retry_after}s",
                        IntegrationType.WHATSAPP,
                        {"retry_after": retry_after}
                    )
                
                response.raise_for_status()
                
                # Update rate limit info
                self._update_rate_limit_info(response)
                
                return response.json() if response.content else {}
                
        except httpx.RequestError as e:
            self.logger.error(f"WhatsApp request error: {e}")
            raise WhatsAppAPIError(f"Request failed: {e}")
    
    def _update_rate_limit_info(self, response: httpx.Response) -> None:
        """Update rate limit information from response headers."""
        # Extract rate limit info from headers if available
        remaining = response.headers.get("X-RateLimit-Remaining")
        reset = response.headers.get("X-RateLimit-Reset")
        
        if remaining:
            self._rate_limit_info["remaining"] = int(remaining)
        
        if reset:
            self._rate_limit_info["reset"] = int(reset)
    
    # Business Profile Management
    
    async def _get_business_profile(self) -> Dict[str, Any]:
        """Get WhatsApp Business profile."""
        if not self.phone_number_id:
            raise WhatsAppAPIError("Phone number ID not available")
        
        return await self._api_request("GET", f"{self.phone_number_id}/whatsapp_business_profile")
    
    async def update_business_profile(
        self,
        about: Optional[str] = None,
        address: Optional[str] = None,
        description: Optional[str] = None,
        email: Optional[str] = None,
        profile_picture_handle: Optional[str] = None,
        websites: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Update WhatsApp Business profile."""
        if not self.phone_number_id:
            raise WhatsAppAPIError("Phone number ID not available")
        
        profile_data = {}
        
        if about:
            profile_data["about"] = about[:139]  # Max 139 characters
        
        if address:
            profile_data["address"] = address
        
        if description:
            profile_data["description"] = description
        
        if email:
            profile_data["email"] = email
        
        if profile_picture_handle:
            profile_data["profile_picture_handle"] = profile_picture_handle
        
        if websites:
            profile_data["websites"] = websites
        
        if not profile_data:
            raise ValueError("No profile fields to update")
        
        return await self._api_request(
            "POST",
            f"{self.phone_number_id}/whatsapp_business_profile",
            json_data={"messaging_product": "whatsapp", "fields": ["about", "address", "description", "email", "profile_picture_handle", "websites"]}
        )
    
    async def get_phone_numbers(self) -> List[Dict[str, Any]]:
        """Get all phone numbers associated with the business account."""
        if not self.business_account_id:
            raise WhatsAppAPIError("Business account ID not available")
        
        result = await self._api_request("GET", f"{self.business_account_id}/phone_numbers")
        return result.get("data", [])
    
    # Message Sending
    
    async def send_text_message(
        self,
        phone_number: str,
        text: str,
        preview_url: bool = False
    ) -> str:
        """Send text message."""
        if not self.phone_number_id:
            raise WhatsAppAPIError("Phone number ID not available")
        
        if len(text) > 4096:
            raise ValueError("Text message cannot exceed 4096 characters")
        
        message_data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone_number,
            "type": "text",
            "text": {
                "body": text,
                "preview_url": preview_url
            }
        }
        
        result = await self._api_request(
            "POST",
            f"{self.phone_number_id}/messages",
            json_data=message_data
        )
        
        message_id = result.get("messages", [{}])[0].get("id")
        self.logger.info(f"Sent text message to {phone_number}: {message_id}")
        
        return message_id
    
    async def send_media_message(
        self,
        phone_number: str,
        media_type: str,
        media_id: str,
        caption: Optional[str] = None,
        filename: Optional[str] = None
    ) -> str:
        """Send media message."""
        if not self.phone_number_id:
            raise WhatsAppAPIError("Phone number ID not available")
        
        if caption and len(caption) > 3000:
            raise ValueError("Caption cannot exceed 3000 characters")
        
        media_data = {
            "id": media_id
        }
        
        if caption:
            media_data["caption"] = caption
        
        if filename:
            media_data["filename"] = filename
        
        message_data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone_number,
            "type": media_type,
            media_type: media_data
        }
        
        result = await self._api_request(
            "POST",
            f"{self.phone_number_id}/messages",
            json_data=message_data
        )
        
        message_id = result.get("messages", [{}])[0].get("id")
        self.logger.info(f"Sent {media_type} message to {phone_number}: {message_id}")
        
        return message_id
    
    async def send_image_message(
        self,
        phone_number: str,
        image_id: str,
        caption: Optional[str] = None
    ) -> str:
        """Send image message."""
        return await self.send_media_message(phone_number, "image", image_id, caption)
    
    async def send_document_message(
        self,
        phone_number: str,
        document_id: str,
        caption: Optional[str] = None,
        filename: Optional[str] = None
    ) -> str:
        """Send document message."""
        return await self.send_media_message(phone_number, "document", document_id, caption, filename)
    
    async def send_video_message(
        self,
        phone_number: str,
        video_id: str,
        caption: Optional[str] = None
    ) -> str:
        """Send video message."""
        return await self.send_media_message(phone_number, "video", video_id, caption)
    
    # Template Messages
    
    async def send_template_message(
        self,
        phone_number: str,
        template_name: str,
        language_code: str = "en_US",
        components: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Send template message."""
        if not self.phone_number_id:
            raise WhatsAppAPIError("Phone number ID not available")
        
        template_data = {
            "name": template_name,
            "language": {
                "code": language_code
            }
        }
        
        if components:
            template_data["components"] = components
        
        message_data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone_number,
            "type": "template",
            "template": template_data
        }
        
        result = await self._api_request(
            "POST",
            f"{self.phone_number_id}/messages",
            json_data=message_data
        )
        
        message_id = result.get("messages", [{}])[0].get("id")
        self.logger.info(f"Sent template message to {phone_number}: {message_id}")
        
        return message_id
    
    async def get_templates(self) -> List[WhatsAppTemplate]:
        """Get available message templates."""
        if not self.phone_number_id:
            raise WhatsAppAPIError("Phone number ID not available")
        
        result = await self._api_request("GET", f"{self.phone_number_id}/message_templates")
        
        templates = []
        for template_data in result.get("data", []):
            template = WhatsAppTemplate(
                name=template_data["name"],
                language=template_data["language"],
                category=template_data["category"],
                components=template_data.get("components", [])
            )
            templates.append(template)
            self._template_cache[template.name] = template
        
        return templates
    
    async def create_template(
        self,
        name: str,
        language_code: str,
        category: str,
        components: List[Dict[str, Any]]
    ) -> str:
        """Create new message template."""
        if not self.phone_number_id:
            raise WhatsAppAPIError("Phone number ID not available")
        
        template_data = {
            "name": name,
            "language": language_code,
            "category": category,
            "components": components
        }
        
        result = await self._api_request(
            "POST",
            f"{self.phone_number_id}/message_templates",
            json_data=template_data
        )
        
        template_id = result.get("id")
        self.logger.info(f"Created template: {name} ({template_id})")
        
        return template_id
    
    # Media Management
    
    async def upload_media(self, file_path: str, mime_type: str) -> str:
        """Upload media file and return media ID."""
        if not self.phone_number_id:
            raise WhatsAppAPIError("Phone number ID not available")
        
        import os
        
        if not os.path.exists(file_path):
            raise WhatsAppAPIError(f"File not found: {file_path}")
        
        file_name = os.path.basename(file_path)
        
        with open(file_path, "rb") as file:
            files = {
                "file": (file_name, file, mime_type),
                "messaging_product": (None, "whatsapp")
            }
            
            result = await self._api_request(
                "POST",
                f"{self.phone_number_id}/media",
                files=files
            )
        
        media_id = result.get("id")
        self.logger.info(f"Uploaded media: {file_name} ({media_id})")
        
        return media_id
    
    async def get_media_info(self, media_id: str) -> WhatsAppMedia:
        """Get media information."""
        result = await self._api_request("GET", media_id)
        
        return WhatsAppMedia(
            media_id=result["id"],
            media_type=result.get("mime_type", "").split("/")[0],
            mime_type=result["mime_type"],
            sha256=result.get("sha256")
        )
    
    async def download_media(self, media_id: str) -> bytes:
        """Download media file."""
        media_info = await self.get_media_info(media_id)
        
        # Get download URL
        download_url = await self._api_request("GET", f"{media_id}/")
        
        # Download file
        async with httpx.AsyncClient() as client:
            response = await client.get(download_url["url"])
            response.raise_for_status()
            
            return response.content
    
    # Interactive Messages
    
    async def send_interactive_message(
        self,
        phone_number: str,
        interactive_type: str,
        interactive_data: Dict[str, Any]
    ) -> str:
        """Send interactive message (list, button, etc.)."""
        if not self.phone_number_id:
            raise WhatsAppAPIError("Phone number ID not available")
        
        message_data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone_number,
            "type": "interactive",
            "interactive": {
                "type": interactive_type,
                **interactive_data
            }
        }
        
        result = await self._api_request(
            "POST",
            f"{self.phone_number_id}/messages",
            json_data=message_data
        )
        
        message_id = result.get("messages", [{}])[0].get("id")
        self.logger.info(f"Sent interactive message to {phone_number}: {message_id}")
        
        return message_id
    
    async def send_list_message(
        self,
        phone_number: str,
        header: str,
        body: str,
        footer: str,
        button_text: str,
        sections: List[Dict[str, Any]]
    ) -> str:
        """Send list message."""
        interactive_data = {
            "type": "list",
            "header": {"type": "text", "text": header},
            "body": {"text": body},
            "footer": {"text": footer},
            "action": {
                "button": button_text,
                "sections": sections
            }
        }
        
        return await self.send_interactive_message(phone_number, "list", interactive_data)
    
    async def send_button_message(
        self,
        phone_number: str,
        header: str,
        body: str,
        footer: str,
        buttons: List[Dict[str, Any]]
    ) -> str:
        """Send button message."""
        interactive_data = {
            "type": "button",
            "header": {"type": "text", "text": header},
            "body": {"text": body},
            "footer": {"text": footer},
            "action": {
                "buttons": buttons
            }
        }
        
        return await self.send_interactive_message(phone_number, "button", interactive_data)
    
    # Message Status and Webhooks
    
    async def get_message_status(self, message_id: str) -> str:
        """Get message delivery status."""
        result = await self._api_request("GET", message_id)
        
        # Extract status from webhook events or message info
        # This would typically be handled by webhook events
        return result.get("status", "unknown")
    
    def verify_webhook_signature(self, request_body: str, signature: str) -> bool:
        """Verify WhatsApp webhook signature."""
        if not signature.startswith("sha256="):
            return False
        
        try:
            # Extract signature
            expected_signature = signature[7:]  # Remove "sha256="
            
            # Calculate signature
            calculated_signature = hmac.new(
                self.whatsapp_config.bot_token.encode(),
                request_body.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures
            return hmac.compare_digest(expected_signature, calculated_signature)
            
        except Exception as e:
            self.logger.error(f"Webhook signature verification failed: {e}")
            return False
    
    async def handle_webhook_event(self, event_data: Dict[str, Any]) -> None:
        """Handle incoming webhook event."""
        try:
            # Extract message data
            entry = event_data.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            
            # Process messages
            messages = value.get("messages", [])
            for message in messages:
                await self._process_incoming_message(message)
            
            # Process statuses
            statuses = value.get("statuses", [])
            for status in statuses:
                await self._process_message_status(status)
            
        except Exception as e:
            self.logger.error(f"Failed to process webhook event: {e}")
    
    async def _process_incoming_message(self, message_data: Dict[str, Any]) -> None:
        """Process incoming WhatsApp message."""
        try:
            message_id = message_data["id"]
            phone_number = message_data["from"]
            timestamp = int(message_data["timestamp"])
            message_type = message_data["type"]
            
            # Convert timestamp to datetime
            message_datetime = datetime.fromtimestamp(timestamp)
            
            # Extract message content based on type
            if message_type == "text":
                text = message_data["text"]["body"]
                whatsapp_message = WhatsAppMessage(
                    message_id=message_id,
                    phone_number=phone_number,
                    text=text,
                    message_type=message_type,
                    timestamp=message_datetime
                )
            elif message_type == "image":
                image_data = message_data["image"]
                whatsapp_message = WhatsAppMessage(
                    message_id=message_id,
                    phone_number=phone_number,
                    text=image_data.get("caption", ""),
                    message_type=message_type,
                    timestamp=message_datetime,
                    metadata={"media_id": image_data.get("id")}
                )
            elif message_type == "interactive":
                interactive_data = message_data["interactive"]
                whatsapp_message = WhatsAppMessage(
                    message_id=message_id,
                    phone_number=phone_number,
                    text=json.dumps(interactive_data),
                    message_type=message_type,
                    timestamp=message_datetime,
                    metadata={"interactive_data": interactive_data}
                )
            else:
                # Handle other message types
                whatsapp_message = WhatsAppMessage(
                    message_id=message_id,
                    phone_number=phone_number,
                    text=f"Received {message_type} message",
                    message_type=message_type,
                    timestamp=message_datetime
                )
            
            # Call registered message handlers
            for handler in self._message_handlers:
                try:
                    await handler(whatsapp_message)
                except Exception as e:
                    self.logger.error(f"Error in message handler: {e}")
            
        except Exception as e:
            self.logger.error(f"Failed to process incoming message: {e}")
    
    async def _process_message_status(self, status_data: Dict[str, Any]) -> None:
        """Process message status update."""
        try:
            message_id = status_data["id"]
            status = status_data["status"]
            timestamp = int(status_data["timestamp"])
            
            self.logger.info(f"Message {message_id} status updated to: {status}")
            
            # Handle different statuses
            if status == "delivered":
                self.logger.info(f"Message {message_id} delivered")
            elif status == "read":
                self.logger.info(f"Message {message_id} read")
            elif status == "failed":
                error = status_data.get("errors", [{}])[0]
                self.logger.error(f"Message {message_id} failed: {error}")
            
        except Exception as e:
            self.logger.error(f"Failed to process message status: {e}")
    
    # Rate Limiting
    
    async def check_rate_limit(self) -> Dict[str, Any]:
        """Check current rate limit status."""
        # WhatsApp Business API rate limits:
        # - 1000 messages per day to unique users
        # - 60 messages per minute
        # - 1 message per second to the same user
        
        return {
            "daily_limit": 1000,
            "per_minute_limit": 60,
            "per_user_per_second_limit": 1,
            "remaining": self._rate_limit_info["remaining"],
            "reset_time": self._rate_limit_info["reset"]
        }
    
    # Business Account Management
    
    async def get_business_account_info(self) -> Dict[str, Any]:
        """Get business account information."""
        if not self.business_account_id:
            raise WhatsAppAPIError("Business account ID not available")
        
        return await self._api_request("GET", self.business_account_id)
    
    async def get_account_review_status(self) -> str:
        """Get account review status."""
        info = await self.get_business_account_info()
        return info.get("account_review_status", "unknown")
    
    # Event Registration
    
    def add_message_handler(self, handler: Callable[[WhatsAppMessage], None]) -> None:
        """Add WhatsApp message event handler."""
        self._message_handlers.append(handler)
    
    def remove_message_handler(self, handler: Callable) -> None:
        """Remove WhatsApp message event handler."""
        if handler in self._message_handlers:
            self._message_handlers.remove(handler)
    
    # Health Check
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        try:
            # Test API connectivity
            account_info = await self.get_business_account_info()
            
            # Test phone number connectivity
            if self.phone_number_id:
                phone_info = await self._api_request("GET", self.phone_number_id)
                phone_status = phone_info.get("quality_score", {}).get("status", "unknown")
            else:
                phone_status = "no_phone_number"
            
            # Check account review status
            review_status = await self.get_account_review_status()
            
            # Overall health status
            is_healthy = (
                review_status == "APPROVED" and
                phone_status in ["GREEN", "unknown"] and
                self._connected
            )
            
            return {
                "status": "healthy" if is_healthy else "degraded",
                "api_connectivity": True,
                "account_id": self.business_account_id,
                "phone_number_id": self.phone_number_id,
                "account_review_status": review_status,
                "phone_quality_status": phone_status,
                "rate_limit_remaining": self._rate_limit_info["remaining"],
                "last_check": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "api_connectivity": False,
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
    
    async def close(self) -> None:
        """Close integration and cleanup resources."""
        self.logger.info("Closing WhatsApp integration")
        
        # Clear caches
        self._template_cache.clear()
        self._processed_messages.clear()
        
        await super().close()


# Export the integration
__all__ = ["WhatsAppIntegration", "WhatsAppMessage", "WhatsAppMedia", "WhatsAppTemplate", "WhatsAppAPIError", "WhatsAppRateLimitError"]