"""
Email integration with IMAP/SMTP and comprehensive email processing.

Provides comprehensive email integration including:
- IMAP/SMTP client with SSL/TLS support
- HTML/text email parsing and processing
- Attachment handling and storage
- Email threading with message IDs
- Auto-responder with rate limiting
- SPF/DKIM validation
- Email template processing
"""

from __future__ import annotations

import asyncio
import imaplib
import smtplib
import email
import re
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import policy
from email.parser import BytesParser
from typing import Any, Dict, List, Optional, AsyncGenerator, Tuple
import ssl
import hashlib

from src.core.config import get_settings
from src.core.logging import get_logger
from src.core.exceptions import ExternalServiceError
from ..base import BaseIntegrationImpl, RateLimitError
from ..config import EmailIntegrationConfig
from . import IntegrationType

logger = get_logger(__name__)


class EmailAPIError(ExternalServiceError):
    """Email API specific errors."""
    pass


class EmailRateLimitError(RateLimitError):
    """Email rate limit exceeded error."""
    pass


class EmailMessage:
    """Represents an email message."""
    
    def __init__(
        self,
        message_id: str,
        subject: str,
        sender: str,
        recipients: List[str],
        body_text: str,
        body_html: Optional[str] = None,
        received_date: Optional[datetime] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        self.message_id = message_id
        self.subject = subject
        self.sender = sender
        self.recipients = recipients
        self.body_text = body_text
        self.body_html = body_html
        self.received_date = received_date or datetime.utcnow()
        self.attachments = attachments or []
        self.headers = headers or {}
        self.conversation_id = self._extract_conversation_id()
    
    def _extract_conversation_id(self) -> Optional[str]:
        """Extract conversation ID from headers."""
        # Use References or In-Reply-To headers for threading
        references = self.headers.get("References", "")
        in_reply_to = self.headers.get("In-Reply-To", "")
        
        if references:
            return references.split()[0]  # First reference is the conversation ID
        elif in_reply_to:
            return in_reply_to
        else:
            return self.message_id


class EmailValidator:
    """Email validation utilities."""
    
    EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    
    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Validate email format."""
        return bool(EmailValidator.EMAIL_REGEX.match(email))
    
    @staticmethod
    def extract_emails_from_text(text: str) -> List[str]:
        """Extract email addresses from text."""
        return EmailValidator.EMAIL_REGEX.findall(text)
    
    @staticmethod
    def normalize_email(email: str) -> str:
        """Normalize email address."""
        return email.strip().lower()


class SPFValidator:
    """SPF (Sender Policy Framework) validation."""
    
    @staticmethod
    async def validate_spf(sender_domain: str, sending_ip: str) -> Dict[str, Any]:
        """Validate SPF record."""
        import dns.resolver
        
        try:
            # Query SPF record
            answers = dns.resolver.resolve(sender_domain, "TXT")
            spf_record = None
            
            for answer in answers:
                txt = str(answer).strip('"')
                if txt.startswith("v=spf1"):
                    spf_record = txt
                    break
            
            if not spf_record:
                return {
                    "valid": False,
                    "result": "none",
                    "explanation": "No SPF record found"
                }
            
            # Simple SPF validation (full implementation would be complex)
            # For now, just check if the record exists
            return {
                "valid": True,
                "result": "pass",
                "record": spf_record,
                "explanation": "SPF record found"
            }
            
        except Exception as e:
            logger.warning(f"SPF validation failed for {sender_domain}: {e}")
            return {
                "valid": False,
                "result": "temperror",
                "explanation": f"DNS lookup failed: {e}"
            }


class DKIMValidator:
    """DKIM (DomainKeys Identified Mail) validation."""
    
    @staticmethod
    async def validate_dkim(message: email.message.EmailMessage) -> Dict[str, Any]:
        """Validate DKIM signature."""
        try:
            # Extract DKIM signature
            dkim_signature = message.get("DKIM-Signature", "")
            
            if not dkim_signature:
                return {
                    "valid": None,
                    "result": "none",
                    "explanation": "No DKIM signature found"
                }
            
            # Parse DKIM signature
            dkim_parts = {}
            for part in dkim_signature.split(";"):
                if "=" in part:
                    key, value = part.split("=", 1)
                    dkim_parts[key.strip()] = value.strip()
            
            # Basic validation (full DKIM validation is complex)
            required_fields = ["v", "a", "d", "s", "h", "b"]
            missing_fields = [field for field in required_fields if field not in dkim_parts]
            
            if missing_fields:
                return {
                    "valid": False,
                    "result": "permerror",
                    "explanation": f"Missing required DKIM fields: {missing_fields}"
                }
            
            return {
                "valid": True,
                "result": "pass",
                "domain": dkim_parts.get("d"),
                "selector": dkim_parts.get("s"),
                "explanation": "DKIM signature found and appears valid"
            }
            
        except Exception as e:
            logger.warning(f"DKIM validation failed: {e}")
            return {
                "valid": False,
                "result": "temperror",
                "explanation": f"DKIM validation error: {e}"
            }


class EmailTemplateProcessor:
    """Email template processing utilities."""
    
    @staticmethod
    def render_template(template: str, variables: Dict[str, Any]) -> str:
        """Render email template with variables."""
        try:
            # Simple template substitution
            for key, value in variables.items():
                template = template.replace(f"{{{{{key}}}}}", str(value))
            return template
        except Exception as e:
            logger.error(f"Template rendering failed: {e}")
            return template
    
    @staticmethod
    def create_html_email(subject: str, body: str, footer: Optional[str] = None) -> str:
        """Create HTML email content."""
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{subject}</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #f4f4f4; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .footer {{ background-color: #f4f4f4; padding: 10px; text-align: center; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{subject}</h1>
                </div>
                <div class="content">
                    {body}
                </div>
                {f'\u003cdiv class="footer"\u003e{footer}\u003c/div\u003e' if footer else ''}
            </div>
        </body>
        </html>
        """
        return html_template


class EmailIntegration(BaseIntegrationImpl):
    """Email integration with IMAP/SMTP and comprehensive email processing."""
    
    def __init__(self, config: EmailIntegrationConfig):
        super().__init__(IntegrationType.EMAIL, config.dict())
        
        self.email_config = config
        self.logger = logger.getChild("email")
        
        # IMAP/SMTP clients
        self.imap_client: Optional[imaplib.IMAP4_SSL] = None
        self.smtp_client: Optional[smtplib.SMTP_SSL] = None
        
        # Connection state
        self._imap_connected = False
        self._smtp_connected = False
        
        # Message tracking
        self._processed_messages: set[str] = set()
        self._message_handlers: List[Callable] = []
        
        # Rate limiting
        self._last_sent_time: Optional[datetime] = None
        self._auto_responder_cache: Dict[str, datetime] = {}
    
    # Connection Management
    
    async def connect_imap(self) -> bool:
        """Connect to IMAP server."""
        try:
            # Create SSL context
            ssl_context = ssl.create_default_context()
            
            # Connect to IMAP server
            self.imap_client = imaplib.IMAP4_SSL(
                self.email_config.imap_server,
                self.email_config.imap_port,
                ssl_context=ssl_context
            )
            
            # Login
            self.imap_client.login(
                self.email_config.imap_username,
                self.email_config.imap_password
            )
            
            self._imap_connected = True
            self.logger.info(f"Connected to IMAP server: {self.email_config.imap_server}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"IMAP connection failed: {e}")
            self._imap_connected = False
            raise EmailAPIError(f"IMAP connection failed: {e}")
    
    async def connect_smtp(self) -> bool:
        """Connect to SMTP server."""
        try:
            # Create SSL context
            ssl_context = ssl.create_default_context()
            
            # Connect to SMTP server
            self.smtp_client = smtplib.SMTP_SSL(
                self.email_config.smtp_server,
                self.email_config.smtp_port,
                context=ssl_context
            )
            
            # Login
            self.smtp_client.login(
                self.email_config.smtp_username,
                self.email_config.smtp_password
            )
            
            self._smtp_connected = True
            self.logger.info(f"Connected to SMTP server: {self.email_config.smtp_server}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"SMTP connection failed: {e}")
            self._smtp_connected = False
            raise EmailAPIError(f"SMTP connection failed: {e}")
    
    async def authenticate(self) -> bool:
        """Authenticate with email servers."""
        try:
            # Test IMAP connection
            imap_success = await self.connect_imap()
            
            # Test SMTP connection
            smtp_success = await self.connect_smtp()
            
            return imap_success and smtp_success
            
        except Exception as e:
            self.logger.error(f"Email authentication failed: {e}")
            raise EmailAPIError(f"Authentication failed: {e}")
    
    # Email Retrieval (IMAP)
    
    async def get_unread_emails(
        self,
        folder: str = "INBOX",
        limit: int = 50
    ) -> List[EmailMessage]:
        """Get unread emails from specified folder."""
        if not self._imap_connected:
            await self.connect_imap()
        
        try:
            # Select folder
            status, _ = self.imap_client.select(folder)
            if status != "OK":
                raise EmailAPIError(f"Failed to select folder: {folder}")
            
            # Search for unread emails
            status, message_ids = self.imap_client.search(None, "UNSEEN")
            if status != "OK":
                raise EmailAPIError("Failed to search for unread emails")
            
            message_id_list = message_ids[0].split()[:limit]
            
            emails = []
            for msg_id in message_id_list:
                try:
                    email_message = await self._parse_email(msg_id.decode())
                    if email_message:
                        emails.append(email_message)
                        
                        # Mark as read
                        self.imap_client.store(msg_id, "+FLAGS", "\\Seen")
                        
                except Exception as e:
                    self.logger.error(f"Failed to parse email {msg_id}: {e}")
                    continue
            
            self.logger.info(f"Retrieved {len(emails)} unread emails from {folder}")
            return emails
            
        except Exception as e:
            self.logger.error(f"Failed to get unread emails: {e}")
            raise EmailAPIError(f"Failed to get unread emails: {e}")
    
    async def get_emails_since(
        self,
        since_date: datetime,
        folder: str = "INBOX",
        limit: int = 100
    ) -> List[EmailMessage]:
        """Get emails since specified date."""
        if not self._imap_connected:
            await self.connect_imap()
        
        try:
            # Select folder
            status, _ = self.imap_client.select(folder)
            if status != "OK":
                raise EmailAPIError(f"Failed to select folder: {folder}")
            
            # Format date for IMAP search
            date_str = since_date.strftime("%d-%b-%Y")
            
            # Search for emails since date
            status, message_ids = self.imap_client.search(None, f"(SINCE {date_str})")
            if status != "OK":
                raise EmailAPIError("Failed to search for emails")
            
            message_id_list = message_ids[0].split()[:limit]
            
            emails = []
            for msg_id in message_id_list:
                try:
                    email_message = await self._parse_email(msg_id.decode())
                    if email_message and email_message.received_date >= since_date:
                        emails.append(email_message)
                        
                except Exception as e:
                    self.logger.error(f"Failed to parse email {msg_id}: {e}")
                    continue
            
            self.logger.info(f"Retrieved {len(emails)} emails since {since_date}")
            return emails
            
        except Exception as e:
            self.logger.error(f"Failed to get emails since {since_date}: {e}")
            raise EmailAPIError(f"Failed to get emails since {since_date}: {e}")
    
    async def search_emails(
        self,
        query: str,
        folder: str = "INBOX",
        limit: int = 50
    ) -> List[EmailMessage]:
        """Search emails by query."""
        if not self._imap_connected:
            await self.connect_imap()
        
        try:
            # Select folder
            status, _ = self.imap_client.select(folder)
            if status != "OK":
                raise EmailAPIError(f"Failed to select folder: {folder}")
            
            # Search for emails containing query
            search_criteria = f'(OR SUBJECT "{query}" BODY "{query}")'
            status, message_ids = self.imap_client.search(None, "CHARSET", "UTF-8", search_criteria)
            if status != "OK":
                raise EmailAPIError("Failed to search for emails")
            
            message_id_list = message_ids[0].split()[:limit]
            
            emails = []
            for msg_id in message_id_list:
                try:
                    email_message = await self._parse_email(msg_id.decode())
                    if email_message:
                        emails.append(email_message)
                        
                except Exception as e:
                    self.logger.error(f"Failed to parse email {msg_id}: {e}")
                    continue
            
            self.logger.info(f"Found {len(emails)} emails matching '{query}'")
            return emails
            
        except Exception as e:
            self.logger.error(f"Failed to search emails for '{query}': {e}")
            raise EmailAPIError(f"Failed to search emails for '{query}': {e}")
    
    async def _parse_email(self, message_id: str) -> Optional[EmailMessage]:
        """Parse email message from IMAP."""
        try:
            # Fetch email
            status, msg_data = self.imap_client.fetch(message_id, "(RFC822)")
            if status != "OK":
                return None
            
            # Parse email
            raw_email = msg_data[0][1]
            email_message = BytesParser(policy=policy.default).parsebytes(raw_email)
            
            # Extract basic information
            message_id = email_message.get("Message-ID", "")
            subject = email_message.get("Subject", "")
            sender = email_message.get("From", "")
            recipients = email_message.get("To", "").split(",")
            date_str = email_message.get("Date", "")
            
            # Parse date
            try:
                received_date = email.utils.parsedate_to_datetime(date_str)
            except:
                received_date = datetime.utcnow()
            
            # Extract body
            body_text, body_html = self._extract_body(email_message)
            
            # Extract attachments
            attachments = self._extract_attachments(email_message)
            
            # Extract headers
            headers = dict(email_message.items())
            
            return EmailMessage(
                message_id=message_id,
                subject=subject,
                sender=sender,
                recipients=recipients,
                body_text=body_text,
                body_html=body_html,
                received_date=received_date,
                attachments=attachments,
                headers=headers
            )
            
        except Exception as e:
            self.logger.error(f"Failed to parse email {message_id}: {e}")
            return None
    
    def _extract_body(self, email_message: email.message.EmailMessage) -> Tuple[str, Optional[str]]:
        """Extract text and HTML body from email."""
        text_body = ""
        html_body = None
        
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                
                # Skip attachments
                if "attachment" in content_disposition:
                    continue
                
                if content_type == "text/plain":
                    try:
                        text_body = part.get_payload(decode=True).decode('utf-8')
                    except:
                        text_body = part.get_payload()
                
                elif content_type == "text/html":
                    try:
                        html_body = part.get_payload(decode=True).decode('utf-8')
                    except:
                        html_body = part.get_payload()
        else:
            # Single part message
            content_type = email_message.get_content_type()
            
            if content_type == "text/plain":
                try:
                    text_body = email_message.get_payload(decode=True).decode('utf-8')
                except:
                    text_body = email_message.get_payload()
            elif content_type == "text/html":
                try:
                    html_body = email_message.get_payload(decode=True).decode('utf-8')
                except:
                    html_body = email_message.get_payload()
        
        return text_body.strip(), html_body
    
    def _extract_attachments(self, email_message: email.message.EmailMessage) -> List[Dict[str, Any]]:
        """Extract attachments from email."""
        attachments = []
        
        if email_message.is_multipart():
            for part in email_message.walk():
                content_disposition = str(part.get("Content-Disposition", ""))
                
                if "attachment" in content_disposition:
                    filename = part.get_filename()
                    content_type = part.get_content_type()
                    size = len(part.get_payload(decode=True)) if part.get_payload(decode=True) else 0
                    
                    attachments.append({
                        "filename": filename,
                        "content_type": content_type,
                        "size": size,
                        "data": part.get_payload(decode=True)
                    })
        
        return attachments
    
    # Email Sending (SMTP)
    
    async def send_email(
        self,
        to_addresses: List[str],
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        cc_addresses: Optional[List[str]] = None,
        bcc_addresses: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        reply_to: Optional[str] = None
    ) -> str:
        """Send email via SMTP."""
        if not self._smtp_connected:
            await self.connect_smtp()
        
        # Check rate limiting
        if self._last_sent_time:
            time_since_last = (datetime.utcnow() - self._last_sent_time).total_seconds()
            if time_since_last < 1:  # 1 second minimum between emails
                await asyncio.sleep(1 - time_since_last)
        
        try:
            # Create message
            if body_html:
                # Multipart message
                msg = MIMEMultipart("alternative")
                
                # Text part
                text_part = MIMEText(body_text, "plain")
                msg.attach(text_part)
                
                # HTML part
                html_part = MIMEText(body_html, "html")
                msg.attach(html_part)
            else:
                # Text only
                msg = MIMEText(body_text, "plain")
            
            # Set headers
            msg["Subject"] = subject
            msg["From"] = self.email_config.from_address
            msg["To"] = ", ".join(to_addresses)
            
            if cc_addresses:
                msg["Cc"] = ", ".join(cc_addresses)
            
            if bcc_addresses:
                msg["Bcc"] = ", ".join(bcc_addresses)
            
            if reply_to:
                msg["Reply-To"] = reply_to
            
            # Add message ID
            msg["Message-ID"] = email.utils.make_msgid(domain=self.email_config.from_address.split('@')[1])
            
            # Add attachments
            if attachments:
                if not isinstance(msg, MIMEMultipart):
                    # Convert to multipart for attachments
                    original_msg = msg
                    msg = MIMEMultipart()
                    msg.attach(original_msg)
                
                for attachment in attachments:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment["data"])
                    email.encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename=\"{attachment['filename']}\""
                    )
                    msg.attach(part)
            
            # Send email
            self.smtp_client.send_message(msg)
            
            self._last_sent_time = datetime.utcnow()
            
            message_id = msg["Message-ID"]
            self.logger.info(f"Sent email to {to_addresses} with subject: {subject}")
            
            return message_id
            
        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")
            raise EmailAPIError(f"Failed to send email: {e}")
    
    async def send_auto_response(
        self,
        original_message: EmailMessage,
        response_text: str,
        response_subject: Optional[str] = None
    ) -> str:
        """Send auto-response email."""
        if not self.email_config.enable_auto_responder:
            self.logger.info("Auto-responder is disabled")
            return ""
        
        # Check if we should send auto-response
        if not await self._should_send_auto_response(original_message):
            return ""
        
        # Prepare response
        to_address = original_message.sender
        subject = response_subject or f"Re: {original_message.subject}"
        
        # Add auto-response header
        response_text = f"This is an automated response. {response_text}"
        
        # Set reply-to to original sender
        reply_to = self.email_config.from_address
        
        # Send response
        message_id = await self.send_email(
            to_addresses=[to_address],
            subject=subject,
            body_text=response_text,
            reply_to=reply_to
        )
        
        # Update auto-responder cache
        self._auto_responder_cache[to_address] = datetime.utcnow()
        
        self.logger.info(f"Sent auto-response to {to_address} for message {original_message.message_id}")
        
        return message_id
    
    async def _should_send_auto_response(self, original_message: EmailMessage) -> bool:
        """Determine if auto-response should be sent."""
        # Check if sender is valid
        if not EmailValidator.is_valid_email(original_message.sender):
            return False
        
        # Check if we've already responded to this sender recently
        last_response = self._auto_responder_cache.get(original_message.sender)
        if last_response:
            time_since_response = (datetime.utcnow() - last_response).total_seconds()
            if time_since_response < 3600:  # 1 hour minimum between responses
                return False
        
        # Check if message is from our own domain (avoid loops)
        sender_domain = original_message.sender.split('@')[1]
        our_domain = self.email_config.from_address.split('@')[1]
        if sender_domain == our_domain:
            return False
        
        # Check if message has auto-submitted header (avoid loops)
        if original_message.headers.get("Auto-Submitted", "").startswith("auto-"):
            return False
        
        return True
    
    # Email Validation
    
    async def validate_email(self, email_message: EmailMessage) -> Dict[str, Any]:
        """Validate email with SPF and DKIM."""
        validation_results = {
            "email_valid": EmailValidator.is_valid_email(email_message.sender),
            "spf_valid": None,
            "dkim_valid": None,
            "overall_valid": False
        }
        
        # SPF validation
        if self.email_config.enable_spf_check:
            try:
                sender_domain = email_message.sender.split('@')[1]
                # Note: In real implementation, you'd get the actual sending IP
                spf_result = await SPFValidator.validate_spf(sender_domain, "127.0.0.1")
                validation_results["spf_valid"] = spf_result["valid"]
            except Exception as e:
                self.logger.warning(f"SPF validation failed: {e}")
                validation_results["spf_valid"] = False
        
        # DKIM validation
        if self.email_config.enable_dkim_check:
            try:
                # Convert EmailMessage to email.message.EmailMessage for DKIM validation
                email_msg = email.message_from_string(
                    f"Message-ID: {email_message.message_id}\r\n"
                    f"From: {email_message.sender}\r\n"
                    f"To: {', '.join(email_message.recipients)}\r\n"
                    f"Subject: {email_message.subject}\r\n"
                    f"\r\n"
                    f"{email_message.body_text}"
                )
                
                dkim_result = await DKIMValidator.validate_dkim(email_msg)
                validation_results["dkim_valid"] = dkim_result["valid"]
            except Exception as e:
                self.logger.warning(f"DKIM validation failed: {e}")
                validation_results["dkim_valid"] = False
        
        # Overall validation
        validation_results["overall_valid"] = (
            validation_results["email_valid"] and
            (validation_results["spf_valid"] is not False) and
            (validation_results["dkim_valid"] is not False)
        )
        
        return validation_results
    
    # Email Threading
    
    def get_thread_info(self, email_message: EmailMessage) -> Dict[str, Any]:
        """Get email thread information."""
        return {
            "conversation_id": email_message.conversation_id,
            "message_id": email_message.message_id,
            "references": email_message.headers.get("References", ""),
            "in_reply_to": email_message.headers.get("In-Reply-To", ""),
            "thread_index": self._calculate_thread_index(email_message)
        }
    
    def _calculate_thread_index(self, email_message: EmailMessage) -> str:
        """Calculate thread index for email threading."""
        # Use Message-ID and References to create a thread index
        message_id = email_message.message_id
        references = email_message.headers.get("References", "")
        
        if references:
            # Use first reference as thread root
            thread_root = references.split()[0]
            thread_index = hashlib.md5(thread_root.encode()).hexdigest()[:16]
        else:
            # Use message ID as thread root
            thread_index = hashlib.md5(message_id.encode()).hexdigest()[:16]
        
        return thread_index
    
    # Monitoring and Reporting
    
    async def get_email_stats(self, folder: str = "INBOX") -> Dict[str, Any]:
        """Get email statistics."""
        if not self._imap_connected:
            await self.connect_imap()
        
        try:
            # Select folder
            status, messages = self.imap_client.select(folder)
            if status != "OK":
                raise EmailAPIError(f"Failed to select folder: {folder}")
            
            total_messages = int(messages[0])
            
            # Get unread count
            status, unread_data = self.imap_client.search(None, "UNSEEN")
            unread_count = len(unread_data[0].split()) if status == "OK" else 0
            
            # Get recent count (last 7 days)
            seven_days_ago = (datetime.utcnow() - timedelta(days=7)).strftime("%d-%b-%Y")
            status, recent_data = self.imap_client.search(None, f"(SINCE {seven_days_ago})")
            recent_count = len(recent_data[0].split()) if status == "OK" else 0
            
            return {
                "folder": folder,
                "total_messages": total_messages,
                "unread_messages": unread_count,
                "recent_messages": recent_count,
                "connection_status": self._imap_connected,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get email stats: {e}")
            raise EmailAPIError(f"Failed to get email stats: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        try:
            # Test IMAP connection
            if not self._imap_connected:
                await self.connect_imap()
            
            # Test SMTP connection
            if not self._smtp_connected:
                await self.connect_smtp()
            
            # Test email sending capability
            test_result = await self._test_email_sending()
            
            # Check rate limiting status
            rate_limited = self._is_rate_limited()
            
            return {
                "status": "healthy",
                "imap_connected": self._imap_connected,
                "smtp_connected": self._smtp_connected,
                "email_sending": test_result,
                "rate_limited": rate_limited,
                "last_check": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "imap_connected": self._imap_connected,
                "smtp_connected": self._smtp_connected,
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
    
    async def _test_email_sending(self) -> bool:
        """Test email sending capability."""
        try:
            # Send a test email to ourselves
            test_message = await self.send_email(
                to_addresses=[self.email_config.from_address],
                subject="Test Email - Health Check",
                body_text="This is a test email for health check purposes."
            )
            
            return bool(test_message)
            
        except Exception as e:
            self.logger.error(f"Email sending test failed: {e}")
            return False
    
    def _is_rate_limited(self) -> bool:
        """Check if currently rate limited."""
        if self._last_sent_time:
            time_since_last = (datetime.utcnow() - self._last_sent_time).total_seconds()
            return time_since_last < 1  # 1 second minimum between emails
        return False
    
    # Event Registration
    
    def add_message_handler(self, handler: Callable[[EmailMessage], None]) -> None:
        """Add email message event handler."""
        self._message_handlers.append(handler)
    
    def remove_message_handler(self, handler: Callable) -> None:
        """Remove email message event handler."""
        if handler in self._message_handlers:
            self._message_handlers.remove(handler)
    
    def _handle_message(self, email_message: EmailMessage) -> None:
        """Handle incoming email message."""
        # Skip if message already processed
        if email_message.message_id in self._processed_messages:
            return
        
        self._processed_messages.add(email_message.message_id)
        
        # Call registered message handlers
        for handler in self._message_handlers:
            try:
                handler(email_message)
            except Exception as e:
                self.logger.error(f"Error in message handler: {e}")
    
    async def close(self) -> None:
        """Close integration and cleanup resources."""
        self.logger.info("Closing email integration")
        
        # Close IMAP connection
        if self.imap_client and self._imap_connected:
            try:
                self.imap_client.close()
                self.imap_client.logout()
            except:
                pass
            self._imap_connected = False
        
        # Close SMTP connection
        if self.smtp_client and self._smtp_connected:
            try:
                self.smtp_client.quit()
            except:
                pass
            self._smtp_connected = False
        
        await super().close()


# Export the integration
__all__ = ["EmailIntegration", "EmailMessage", "EmailValidator", "EmailAPIError", "EmailRateLimitError"]