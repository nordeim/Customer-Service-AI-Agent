"""
Tests for multi-channel communication adapters.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from src.integrations.channels import (
    SlackIntegration,
    TeamsIntegration,
    EmailIntegration,
    WhatsAppIntegration,
    WebhookIntegration
)
from src.integrations.channels.slack import SlackEventType
from src.integrations.channels.teams import TeamsEventType
from src.integrations.channels.email import EmailMessage
from src.integrations.channels.whatsapp import WhatsAppMessageType
from src.integrations.channels.webhook import WebhookEvent


class TestSlackIntegration:
    """Test Slack integration functionality."""
    
    @pytest.fixture
    def slack_integration(self):
        config = {
            "bot_token": "xoxb-test-token",
            "signing_secret": "test-signing-secret",
            "app_token": "xapp-test-token",
            "rate_limit": {"requests_per_second": 10}
        }
        return SlackIntegration(config)
    
    @pytest.mark.asyncio
    async def test_initialization(self, slack_integration):
        """Test Slack integration initialization."""
        assert slack_integration.bot_token == "xoxb-test-token"
        assert slack_integration.signing_secret == "test-signing-secret"
        assert slack_integration.app_token == "xapp-test-token"
        assert slack_integration._websocket_task is None
    
    @pytest.mark.asyncio
    async def test_send_message_success(self, slack_integration):
        """Test successful message sending."""
        mock_response = {
            "ok": True,
            "channel": "C12345",
            "ts": "1234567890.123456",
            "message": {
                "text": "Test message",
                "user": "U12345"
            }
        }
        
        with patch.object(slack_integration, '_make_api_request', return_value=mock_response):
            result = await slack_integration.send_message("C12345", "Test message")
            
            assert result["ok"] is True
            assert result["channel"] == "C12345"
            assert result["message"]["text"] == "Test message"
    
    @pytest.mark.asyncio
    async def test_send_message_with_blocks(self, slack_integration):
        """Test message sending with blocks."""
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Test Message*"
                }
            }
        ]
        
        mock_response = {
            "ok": True,
            "channel": "C12345",
            "ts": "1234567890.123456",
            "message": {
                "text": "Test message",
                "blocks": blocks
            }
        }
        
        with patch.object(slack_integration, '_make_api_request', return_value=mock_response):
            result = await slack_integration.send_message("C12345", "Test message", blocks=blocks)
            
            assert result["ok"] is True
            assert result["message"]["blocks"] == blocks
    
    @pytest.mark.asyncio
    async def test_send_direct_message(self, slack_integration):
        """Test direct message sending."""
        mock_response = {
            "ok": True,
            "channel": "D12345",
            "ts": "1234567890.123456",
            "message": {
                "text": "DM test",
                "user": "U12345"
            }
        }
        
        with patch.object(slack_integration, '_make_api_request', return_value=mock_response):
            result = await slack_integration.send_direct_message("U12345", "DM test")
            
            assert result["ok"] is True
            assert result["channel"] == "D12345"
            assert result["message"]["text"] == "DM test"
    
    @pytest.mark.asyncio
    async def test_handle_message_event(self, slack_integration):
        """Test message event handling."""
        event = {
            "type": "message",
            "user": "U12345",
            "text": "Hello bot",
            "channel": "C12345",
            "ts": "1234567890.123456"
        }
        
        # Mock the event handler
        slack_integration.event_handlers[SlackEventType.MESSAGE] = AsyncMock()
        
        await slack_integration._handle_event(event)
        
        # Verify handler was called
        slack_integration.event_handlers[SlackEventType.MESSAGE].assert_called_once_with(event)
    
    @pytest.mark.asyncio
    async def test_handle_app_mention_event(self, slack_integration):
        """Test app mention event handling."""
        event = {
            "type": "app_mention",
            "user": "U12345",
            "text": "<@U12345> help me",
            "channel": "C12345",
            "ts": "1234567890.123456"
        }
        
        # Mock the event handler
        slack_integration.event_handlers[SlackEventType.APP_MENTION] = AsyncMock()
        
        await slack_integration._handle_event(event)
        
        # Verify handler was called
        slack_integration.event_handlers[SlackEventType.APP_MENTION].assert_called_once_with(event)
    
    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, slack_integration):
        """Test rate limit handling."""
        # Simulate rate limit error
        rate_limit_error = Exception("rate_limited")
        
        with patch.object(slack_integration, '_make_api_request', side_effect=rate_limit_error):
            with pytest.raises(Exception, match="rate_limited"):
                await slack_integration.send_message("C12345", "Test message")
    
    @pytest.mark.asyncio
    async def test_webhook_verification(self, slack_integration):
        """Test webhook signature verification."""
        timestamp = "1234567890"
        body = b'{"type":"url_verification","challenge":"test_challenge"}'
        signature = "v0=test_signature"
        
        with patch.object(slack_integration, '_verify_signature', return_value=True):
            is_valid = await slack_integration.verify_webhook_signature(timestamp, body, signature)
            assert is_valid is True
    
    @pytest.mark.asyncio
    async def test_health_check(self, slack_integration):
        """Test health check functionality."""
        mock_response = {
            "ok": True,
            "url": "https://test.slack.com/",
            "team": "Test Team",
            "user": "test_bot",
            "team_id": "T12345",
            "user_id": "U12345"
        }
        
        with patch.object(slack_integration, '_make_api_request', return_value=mock_response):
            health = await slack_integration.health_check()
            
            assert health["status"] == "healthy"
            assert health["team"] == "Test Team"
            assert health["user"] == "test_bot"


class TestTeamsIntegration:
    """Test Microsoft Teams integration functionality."""
    
    @pytest.fixture
    def teams_integration(self):
        config = {
            "app_id": "test-app-id",
            "app_password": "test-app-password",
            "tenant_id": "test-tenant-id",
            "rate_limit": {"requests_per_second": 10}
        }
        return TeamsIntegration(config)
    
    @pytest.mark.asyncio
    async def test_initialization(self, teams_integration):
        """Test Teams integration initialization."""
        assert teams_integration.app_id == "test-app-id"
        assert teams_integration.app_password == "test-app-password"
        assert teams_integration.tenant_id == "test-tenant-id"
        assert teams_integration._access_token is None
    
    @pytest.mark.asyncio
    async def test_get_access_token(self, teams_integration):
        """Test access token retrieval."""
        mock_token_response = {
            "access_token": "test_access_token",
            "token_type": "Bearer",
            "expires_in": 3600
        }
        
        with patch.object(teams_integration, '_make_token_request', return_value=mock_token_response):
            token = await teams_integration._get_access_token()
            
            assert token == "test_access_token"
            assert teams_integration._access_token == "test_access_token"
    
    @pytest.mark.asyncio
    async def test_send_message_to_channel(self, teams_integration):
        """Test message sending to channel."""
        teams_integration._access_token = "test_token"
        
        mock_response = {
            "id": "1234567890",
            "body": {
                "content": "Test message",
                "contentType": "text"
            }
        }
        
        with patch.object(teams_integration, '_make_graph_request', return_value=mock_response):
            result = await teams_integration.send_message_to_channel("team123", "channel123", "Test message")
            
            assert result["id"] == "1234567890"
            assert result["body"]["content"] == "Test message"
    
    @pytest.mark.asyncio
    async def test_send_adaptive_card(self, teams_integration):
        """Test adaptive card sending."""
        teams_integration._access_token = "test_token"
        
        card = {
            "type": "AdaptiveCard",
            "body": [{
                "type": "TextBlock",
                "text": "Hello World!"
            }],
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.0"
        }
        
        mock_response = {
            "id": "1234567890",
            "attachments": [{
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": card
            }]
        }
        
        with patch.object(teams_integration, '_make_graph_request', return_value=mock_response):
            result = await teams_integration.send_adaptive_card("team123", "channel123", card)
            
            assert result["id"] == "1234567890"
            assert len(result["attachments"]) == 1
            assert result["attachments"][0]["contentType"] == "application/vnd.microsoft.card.adaptive"
    
    @pytest.mark.asyncio
    async def test_create_meeting(self, teams_integration):
        """Test meeting creation."""
        teams_integration._access_token = "test_token"
        
        meeting_data = {
            "subject": "Test Meeting",
            "start": {
                "dateTime": "2024-01-01T10:00:00",
                "timeZone": "UTC"
            },
            "end": {
                "dateTime": "2024-01-01T11:00:00",
                "timeZone": "UTC"
            }
        }
        
        mock_response = {
            "id": "meeting123",
            "subject": "Test Meeting",
            "start": meeting_data["start"],
            "end": meeting_data["end"]
        }
        
        with patch.object(teams_integration, '_make_graph_request', return_value=mock_response):
            result = await teams_integration.create_meeting(meeting_data)
            
            assert result["id"] == "meeting123"
            assert result["subject"] == "Test Meeting"
    
    @pytest.mark.asyncio
    async def test_handle_message_activity(self, teams_integration):
        """Test message activity handling."""
        activity = {
            "type": "message",
            "text": "Hello bot",
            "from": {
                "id": "user123",
                "name": "Test User"
            },
            "conversation": {
                "id": "conv123"
            },
            "recipient": {
                "id": "bot123"
            }
        }
        
        # Mock the activity handler
        teams_integration.activity_handlers[TeamsEventType.MESSAGE] = AsyncMock()
        
        await teams_integration._handle_activity(activity)
        
        # Verify handler was called
        teams_integration.activity_handlers[TeamsEventType.MESSAGE].assert_called_once_with(activity)
    
    @pytest.mark.asyncio
    async def test_bot_framework_authentication(self, teams_integration):
        """Test Bot Framework authentication."""
        auth_header = "Bearer test_token"
        
        with patch.object(teams_integration, '_validate_jwt_token', return_value=True):
            is_valid = await teams_integration.validate_bot_framework_auth(auth_header)
            assert is_valid is True
    
    @pytest.mark.asyncio
    async def test_health_check(self, teams_integration):
        """Test health check functionality."""
        teams_integration._access_token = "test_token"
        
        mock_response = {
            "value": [{
                "id": "team123",
                "displayName": "Test Team"
            }]
        }
        
        with patch.object(teams_integration, '_make_graph_request', return_value=mock_response):
            health = await teams_integration.health_check()
            
            assert health["status"] == "healthy"
            assert health["teams_count"] == 1
            assert health["teams"][0]["displayName"] == "Test Team"


class TestEmailIntegration:
    """Test email integration functionality."""
    
    @pytest.fixture
    def email_integration(self):
        config = {
            "imap_server": "imap.gmail.com",
            "imap_port": 993,
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "username": "test@example.com",
            "password": "test-password",
            "use_ssl": True,
            "rate_limit": {"requests_per_second": 5}
        }
        return EmailIntegration(config)
    
    @pytest.mark.asyncio
    async def test_initialization(self, email_integration):
        """Test email integration initialization."""
        assert email_integration.imap_server == "imap.gmail.com"
        assert email_integration.imap_port == 993
        assert email_integration.smtp_server == "smtp.gmail.com"
        assert email_integration.smtp_port == 587
        assert email_integration.username == "test@example.com"
        assert email_integration.use_ssl is True
    
    @pytest.mark.asyncio
    async def test_send_email(self, email_integration):
        """Test email sending."""
        message = EmailMessage(
            to=["recipient@example.com"],
            subject="Test Subject",
            body="Test body",
            html_body="<p>Test body</p>"
        )
        
        with patch.object(email_integration, '_send_smtp_message', return_value=True):
            result = await email_integration.send_email(message)
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_send_email_with_attachments(self, email_integration):
        """Test email sending with attachments."""
        message = EmailMessage(
            to=["recipient@example.com"],
            subject="Test Subject",
            body="Test body with attachments",
            attachments=[
                {
                    "filename": "test.txt",
                    "content": b"Test file content",
                    "content_type": "text/plain"
                }
            ]
        )
        
        with patch.object(email_integration, '_send_smtp_message', return_value=True):
            result = await email_integration.send_email(message)
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_fetch_emails(self, email_integration):
        """Test email fetching."""
        mock_emails = [
            {
                "id": "1",
                "subject": "Test Email 1",
                "from": "sender1@example.com",
                "date": datetime.utcnow(),
                "body": "Test body 1"
            },
            {
                "id": "2",
                "subject": "Test Email 2",
                "from": "sender2@example.com",
                "date": datetime.utcnow(),
                "body": "Test body 2"
            }
        ]
        
        with patch.object(email_integration, '_fetch_imap_emails', return_value=mock_emails):
            emails = await email_integration.fetch_emails(folder="INBOX", limit=10)
            
            assert len(emails) == 2
            assert emails[0]["subject"] == "Test Email 1"
            assert emails[1]["subject"] == "Test Email 2"
    
    @pytest.mark.asyncio
    async def test_parse_email_content(self, email_integration):
        """Test email content parsing."""
        email_content = """From: sender@example.com
To: recipient@example.com
Subject: Test Email
Content-Type: multipart/alternative; boundary="boundary123"

--boundary123
Content-Type: text/plain

This is plain text content.

--boundary123
Content-Type: text/html

<html><body><p>This is HTML content.</p></body></html>

--boundary123--"""
        
        with patch.object(email_integration, '_parse_mime_message') as mock_parse:
            mock_parse.return_value = {
                "subject": "Test Email",
                "from": "sender@example.com",
                "to": "recipient@example.com",
                "body": "This is plain text content.",
                "html_body": "<p>This is HTML content.</p>"
            }
            
            parsed = await email_integration._parse_email_content(email_content)
            
            assert parsed["subject"] == "Test Email"
            assert parsed["from"] == "sender@example.com"
            assert parsed["body"] == "This is plain text content."
            assert parsed["html_body"] == "<p>This is HTML content.</p>"
    
    @pytest.mark.asyncio
    async def test_email_threading(self, email_integration):
        """Test email threading."""
        mock_emails = [
            {
                "id": "1",
                "subject": "Re: Original Subject",
                "from": "sender1@example.com",
                "in_reply_to": "original@example.com",
                "references": "original@example.com"
            },
            {
                "id": "2",
                "subject": "Original Subject",
                "from": "sender2@example.com",
                "message_id": "original@example.com"
            }
        ]
        
        with patch.object(email_integration, '_fetch_imap_emails', return_value=mock_emails):
            threads = await email_integration.get_email_threads()
            
            assert len(threads) == 1  # Should group into one thread
            assert len(threads[0]["emails"]) == 2
    
    @pytest.mark.asyncio
    async def test_auto_responder(self, email_integration):
        """Test auto-responder functionality."""
        incoming_email = {
            "id": "1",
            "from": "sender@example.com",
            "subject": "Test Email",
            "body": "Please help me"
        }
        
        # Mock auto-response generation
        with patch.object(email_integration, '_generate_auto_response', return_value="Thank you for your email. We will respond shortly."):
            with patch.object(email_integration, 'send_email', return_value=True) as mock_send:
                result = await email_integration.send_auto_response(incoming_email)
                
                assert result is True
                mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check(self, email_integration):
        """Test health check functionality."""
        with patch.object(email_integration, '_test_imap_connection', return_value=True):
            with patch.object(email_integration, '_test_smtp_connection', return_value=True):
                health = await email_integration.health_check()
                
                assert health["status"] == "healthy"
                assert health["imap_connected"] is True
                assert health["smtp_connected"] is True


class TestWhatsAppIntegration:
    """Test WhatsApp integration functionality."""
    
    @pytest.fixture
    def whatsapp_integration(self):
        config = {
            "access_token": "test-access-token",
            "phone_number_id": "1234567890",
            "business_account_id": "0987654321",
            "webhook_verify_token": "test-verify-token",
            "rate_limit": {"requests_per_second": 20}
        }
        return WhatsAppIntegration(config)
    
    @pytest.mark.asyncio
    async def test_initialization(self, whatsapp_integration):
        """Test WhatsApp integration initialization."""
        assert whatsapp_integration.access_token == "test-access-token"
        assert whatsapp_integration.phone_number_id == "1234567890"
        assert whatsapp_integration.business_account_id == "0987654321"
        assert whatsapp_integration.webhook_verify_token == "test-verify-token"
    
    @pytest.mark.asyncio
    async def test_send_text_message(self, whatsapp_integration):
        """Test text message sending."""
        mock_response = {
            "messaging_product": "whatsapp",
            "contacts": [{"input": "1234567890", "wa_id": "1234567890"}],
            "messages": [{"id": "wamid.test123"}]
        }
        
        with patch.object(whatsapp_integration, '_make_api_request', return_value=mock_response):
            result = await whatsapp_integration.send_text_message("1234567890", "Hello World!")
            
            assert result["messaging_product"] == "whatsapp"
            assert len(result["messages"]) == 1
            assert result["messages"][0]["id"] == "wamid.test123"
    
    @pytest.mark.asyncio
    async def test_send_template_message(self, whatsapp_integration):
        """Test template message sending."""
        mock_response = {
            "messaging_product": "whatsapp",
            "contacts": [{"input": "1234567890", "wa_id": "1234567890"}],
            "messages": [{"id": "wamid.template123"}]
        }
        
        template_data = {
            "name": "hello_world",
            "language": {"code": "en_US"},
            "components": [{
                "type": "body",
                "parameters": [{"type": "text", "text": "John"}]
            }]
        }
        
        with patch.object(whatsapp_integration, '_make_api_request', return_value=mock_response):
            result = await whatsapp_integration.send_template_message("1234567890", template_data)
            
            assert result["messaging_product"] == "whatsapp"
            assert len(result["messages"]) == 1
    
    @pytest.mark.asyncio
    async def test_send_media_message(self, whatsapp_integration):
        """Test media message sending."""
        mock_response = {
            "messaging_product": "whatsapp",
            "contacts": [{"input": "1234567890", "wa_id": "1234567890"}],
            "messages": [{"id": "wamid.media123"}]
        }
        
        media_data = {
            "type": "image",
            "media_id": "media123",
            "caption": "Test image"
        }
        
        with patch.object(whatsapp_integration, '_make_api_request', return_value=mock_response):
            result = await whatsapp_integration.send_media_message("1234567890", media_data)
            
            assert result["messaging_product"] == "whatsapp"
            assert len(result["messages"]) == 1
    
    @pytest.mark.asyncio
    async def test_handle_message_webhook(self, whatsapp_integration):
        """Test message webhook handling."""
        webhook_data = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "0987654321",
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": "1234567890",
                            "id": "wamid.incoming123",
                            "timestamp": "1234567890",
                            "text": {"body": "Hello from user"},
                            "type": "text"
                        }]
                    }
                }]
            }]
        }
        
        # Mock the message handler
        whatsapp_integration.message_handlers[WhatsAppMessageType.TEXT] = AsyncMock()
        
        await whatsapp_integration.process_webhook_request(webhook_data)
        
        # Verify handler was called
        whatsapp_integration.message_handlers[WhatsAppMessageType.TEXT].assert_called_once()
    
    @pytest.mark.asyncio
    async def test_webhook_verification(self, whatsapp_integration):
        """Test webhook verification."""
        mode = "subscribe"
        token = "test-verify-token"
        challenge = "test_challenge"
        
        result = await whatsapp_integration.verify_webhook(mode, token, challenge)
        
        assert result["status"] == "success"
        assert result["challenge"] == challenge
    
    @pytest.mark.asyncio
    async def test_get_business_profile(self, whatsapp_integration):
        """Test business profile retrieval."""
        mock_response = {
            "data": [{
                "about": "Test Business",
                "address": "123 Test St",
                "description": "Test description",
                "email": "test@example.com",
                "profile_picture_url": "https://example.com/picture.jpg"
            }]
        }
        
        with patch.object(whatsapp_integration, '_make_api_request', return_value=mock_response):
            profile = await whatsapp_integration.get_business_profile()
            
            assert profile["about"] == "Test Business"
            assert profile["email"] == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_health_check(self, whatsapp_integration):
        """Test health check functionality."""
        mock_response = {
            "data": [{
                "verified_name": "Test Business",
                "display_phone_number": "+1234567890",
                "quality_rating": "HIGH"
            }]
        }
        
        with patch.object(whatsapp_integration, '_make_api_request', return_value=mock_response):
            health = await whatsapp_integration.health_check()
            
            assert health["status"] == "healthy"
            assert health["verified_name"] == "Test Business"
            assert health["quality_rating"] == "HIGH"


class TestWebhookIntegration:
    """Test generic webhook integration functionality."""
    
    @pytest.fixture
    def webhook_integration(self):
        config = {
            "webhook_url": "https://example.com/webhook",
            "secret_key": "test-secret-key",
            "signature_header": "X-Hub-Signature-256",
            "algorithm": "sha256",
            "rate_limit": {"requests_per_second": 100}
        }
        return WebhookIntegration(config)
    
    @pytest.mark.asyncio
    async def test_initialization(self, webhook_integration):
        """Test webhook integration initialization."""
        assert webhook_integration.webhook_url == "https://example.com/webhook"
        assert webhook_integration.secret_key == "test-secret-key"
        assert webhook_integration.signature_header == "X-Hub-Signature-256"
        assert webhook_integration.algorithm == "sha256"
    
    @pytest.mark.asyncio
    async def test_send_webhook_event(self, webhook_integration):
        """Test webhook event sending."""
        event = WebhookEvent(
            event_type="test_event",
            payload={"key": "value"},
            timestamp=datetime.utcnow()
        )
        
        mock_response = {"status": "received", "id": "evt123"}
        
        with patch.object(webhook_integration, '_make_http_request', return_value=mock_response):
            result = await webhook_integration.send_webhook_event(event)
            
            assert result["status"] == "received"
            assert result["id"] == "evt123"
    
    @pytest.mark.asyncio
    async def test_verify_webhook_signature(self, webhook_integration):
        """Test webhook signature verification."""
        payload = b'{"test": "data"}'
        signature = "sha256=test_signature"
        
        with patch.object(webhook_integration, '_verify_signature', return_value=True):
            is_valid = await webhook_integration.verify_webhook_signature(payload, signature)
            assert is_valid is True
    
    @pytest.mark.asyncio
    async def test_process_incoming_webhook(self, webhook_integration):
        """Test incoming webhook processing."""
        webhook_data = {
            "event_type": "user.created",
            "data": {
                "id": "user123",
                "name": "Test User"
            },
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        # Mock the event handler
        webhook_integration.event_handlers["user.created"] = AsyncMock()
        
        await webhook_integration.process_incoming_webhook(webhook_data)
        
        # Verify handler was called
        webhook_integration.event_handlers["user.created"].assert_called_once_with(webhook_data)
    
    @pytest.mark.asyncio
    async def test_retry_mechanism(self, webhook_integration):
        """Test webhook retry mechanism."""
        event = WebhookEvent(
            event_type="test_event",
            payload={"key": "value"},
            timestamp=datetime.utcnow()
        )
        
        # First call fails, second succeeds
        mock_responses = [
            Exception("Network error"),
            {"status": "received", "id": "evt123"}
        ]
        
        with patch.object(webhook_integration, '_make_http_request', side_effect=mock_responses):
            result = await webhook_integration.send_webhook_event_with_retry(event)
            
            assert result["status"] == "received"
            assert result["id"] == "evt123"
    
    @pytest.mark.asyncio
    async def test_dead_letter_queue(self, webhook_integration):
        """Test dead letter queue functionality."""
        failed_event = WebhookEvent(
            event_type="test_event",
            payload={"key": "value"},
            timestamp=datetime.utcnow(),
            retry_count=3
        )
        
        with patch.object(webhook_integration, '_add_to_dead_letter_queue', return_value=True):
            result = await webhook_integration._handle_failed_event(failed_event)
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_health_check(self, webhook_integration):
        """Test health check functionality."""
        health = await webhook_integration.health_check()
        
        assert health["status"] == "healthy"
        assert health["webhook_url"] == "https://example.com/webhook"
        assert health["algorithm"] == "sha256"


# Performance tests
@pytest.mark.integration
class TestChannelsPerformance:
    """Performance tests for channel integrations."""
    
    @pytest.mark.asyncio
    async def test_slack_message_performance(self):
        """Test Slack message sending performance."""
        config = {
            "bot_token": "xoxb-test-token",
            "signing_secret": "test-signing-secret",
            "rate_limit": {"requests_per_second": 100}
        }
        
        slack = SlackIntegration(config)
        
        # Mock API request
        mock_response = {"ok": True, "ts": "1234567890.123456"}
        slack._make_api_request = AsyncMock(return_value=mock_response)
        
        start_time = time.time()
        
        # Test 100 consecutive messages
        tasks = []
        for i in range(100):
            tasks.append(slack.send_message("C12345", f"Test message {i}"))
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in reasonable time (< 5 seconds)
        assert duration < 5.0
        assert len(results) == 100
        assert all(result["ok"] is True for result in results)
    
    @pytest.mark.asyncio
    async def test_teams_adaptive_card_performance(self):
        """Test Teams adaptive card sending performance."""
        config = {
            "app_id": "test-app-id",
            "app_password": "test-app-password",
            "tenant_id": "test-tenant-id",
            "rate_limit": {"requests_per_second": 50}
        }
        
        teams = TeamsIntegration(config)
        teams._access_token = "test_token"
        
        # Mock API request
        mock_response = {"id": "1234567890"}
        teams._make_graph_request = AsyncMock(return_value=mock_response)
        
        card = {
            "type": "AdaptiveCard",
            "body": [{"type": "TextBlock", "text": "Performance test"}],
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.0"
        }
        
        start_time = time.time()
        
        # Test 50 concurrent adaptive cards
        tasks = []
        for i in range(50):
            tasks.append(teams.send_adaptive_card("team123", "channel123", card))
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in reasonable time (< 3 seconds)
        assert duration < 3.0
        assert len(results) == 50
        assert all(result["id"] == "1234567890" for result in results)
    
    @pytest.mark.asyncio
    async def test_webhook_processing_performance(self):
        """Test webhook processing performance."""
        config = {
            "webhook_url": "https://example.com/webhook",
            "secret_key": "test-secret-key",
            "signature_header": "X-Hub-Signature-256",
            "algorithm": "sha256",
            "rate_limit": {"requests_per_second": 200}
        }
        
        webhook = WebhookIntegration(config)
        
        # Mock event handler
        webhook.event_handlers["test_event"] = AsyncMock(return_value={"status": "processed"})
        
        start_time = time.time()
        
        # Test 200 concurrent webhook events
        tasks = []
        for i in range(200):
            event_data = {
                "event_type": "test_event",
                "data": {"id": f"item{i}", "value": i},
                "timestamp": datetime.utcnow().isoformat()
            }
            tasks.append(webhook.process_incoming_webhook(event_data))
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in reasonable time (< 2 seconds)
        assert duration < 2.0
        assert len(results) == 200
        assert webhook.event_handlers["test_event"].call_count == 200


# Error handling tests
@pytest.mark.asyncio
class TestChannelsErrorHandling:
    """Test error handling in channel integrations."""
    
    async def test_slack_error_handling(self):
        """Test Slack error handling."""
        config = {
            "bot_token": "xoxb-test-token",
            "signing_secret": "test-signing-secret",
            "rate_limit": {"requests_per_second": 10}
        }
        
        slack = SlackIntegration(config)
        
        # Test API error
        with patch.object(slack, '_make_api_request', side_effect=Exception("API Error")):
            with pytest.raises(Exception, match="API Error"):
                await slack.send_message("C12345", "Test message")
    
    async def test_teams_error_handling(self):
        """Test Teams error handling."""
        config = {
            "app_id": "test-app-id",
            "app_password": "test-app-password",
            "tenant_id": "test-tenant-id",
            "rate_limit": {"requests_per_second": 10}
        }
        
        teams = TeamsIntegration(config)
        teams._access_token = "test_token"
        
        # Test Graph API error
        with patch.object(teams, '_make_graph_request', side_effect=Exception("Graph API Error")):
            with pytest.raises(Exception, match="Graph API Error"):
                await teams.send_message_to_channel("team123", "channel123", "Test message")
    
    async def test_email_error_handling(self):
        """Test email error handling."""
        config = {
            "imap_server": "imap.gmail.com",
            "imap_port": 993,
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "username": "test@example.com",
            "password": "test-password",
            "use_ssl": True,
            "rate_limit": {"requests_per_second": 5}
        }
        
        email = EmailIntegration(config)
        
        message = EmailMessage(
            to=["recipient@example.com"],
            subject="Test Subject",
            body="Test body"
        )
        
        # Test SMTP error
        with patch.object(email, '_send_smtp_message', side_effect=Exception("SMTP Error")):
            with pytest.raises(Exception, match="SMTP Error"):
                await email.send_email(message)
    
    async def test_whatsapp_error_handling(self):
        """Test WhatsApp error handling."""
        config = {
            "access_token": "test-access-token",
            "phone_number_id": "1234567890",
            "business_account_id": "0987654321",
            "webhook_verify_token": "test-verify-token",
            "rate_limit": {"requests_per_second": 20}
        }
        
        whatsapp = WhatsAppIntegration(config)
        
        # Test API error
        with patch.object(whatsapp, '_make_api_request', side_effect=Exception("WhatsApp API Error")):
            with pytest.raises(Exception, match="WhatsApp API Error"):
                await whatsapp.send_text_message("1234567890", "Test message")
    
    async def test_webhook_error_handling(self):
        """Test webhook error handling."""
        config = {
            "webhook_url": "https://example.com/webhook",
            "secret_key": "test-secret-key",
            "signature_header": "X-Hub-Signature-256",
            "algorithm": "sha256",
            "rate_limit": {"requests_per_second": 100}
        }
        
        webhook = WebhookIntegration(config)
        
        event = WebhookEvent(
            event_type="test_event",
            payload={"key": "value"},
            timestamp=datetime.utcnow()
        )
        
        # Test HTTP request error
        with patch.object(webhook, '_make_http_request', side_effect=Exception("HTTP Error")):
            with pytest.raises(Exception, match="HTTP Error"):
                await webhook.send_webhook_event(event)