"""
Integration configuration schemas and management.

Provides Pydantic models for:
- Integration configurations
- OAuth 2.0 client settings
- Rate limiting configuration
- Sync schedules and frequencies
- Security settings and encryption
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field, validator, HttpUrl
from datetime import timedelta

from src.core.config import get_settings


class OAuth2Provider(str, Enum):
    """Supported OAuth 2.0 providers."""
    SALESFORCE = "salesforce"
    SLACK = "slack"
    TEAMS = "teams"
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    ZENDESK = "zendesk"
    CUSTOM = "custom"


class SyncFrequency(str, Enum):
    """Data synchronization frequencies."""
    REAL_TIME = "real_time"
    EVERY_30_SECONDS = "30_seconds"
    EVERY_1_MINUTE = "1_minute"
    EVERY_5_MINUTES = "5_minutes"
    EVERY_15_MINUTES = "15_minutes"
    EVERY_30_MINUTES = "30_minutes"
    EVERY_1_HOUR = "1_hour"
    EVERY_6_HOURS = "6_hours"
    EVERY_12_HOURS = "12_hours"
    EVERY_24_HOURS = "24_hours"


class ConflictResolution(str, Enum):
    """Conflict resolution strategies."""
    LAST_WRITE_WINS = "last_write_wins"
    MERGE = "merge"
    MANUAL = "manual"
    SOURCE_WINS = "source_wins"
    TARGET_WINS = "target_wins"


class TLSVersion(str, Enum):
    """Supported TLS versions."""
    TLS_1_2 = "1.2"
    TLS_1_3 = "1.3"


class EncryptionAlgorithm(str, Enum):
    """Supported encryption algorithms."""
    AES_256_GCM = "AES-256-GCM"
    CHACHA20_POLY1305 = "ChaCha20-Poly1305"


# Base Configuration Models

class BaseIntegrationConfig(BaseModel):
    """Base configuration for all integrations."""
    
    enabled: bool = Field(default=True, description="Whether integration is enabled")
    organization_id: str = Field(description="Organization ID for multi-tenancy")
    timeout_seconds: int = Field(default=30, ge=5, le=300, description="Request timeout")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    health_check_interval_seconds: int = Field(default=60, ge=10, le=3600, description="Health check frequency")
    
    @validator("timeout_seconds")
    def validate_timeout(cls, v: int) -> int:
        if v < 5 or v > 300:
            raise ValueError("Timeout must be between 5 and 300 seconds")
        return v


class OAuth2ClientConfig(BaseModel):
    """OAuth 2.0 client configuration."""
    
    client_id: str = Field(description="OAuth 2.0 client ID")
    client_secret: str = Field(description="OAuth 2.0 client secret")
    authorization_url: HttpUrl = Field(description="OAuth 2.0 authorization URL")
    token_url: HttpUrl = Field(description="OAuth 2.0 token URL")
    redirect_uri: str = Field(description="OAuth 2.0 redirect URI")
    scope: Optional[str] = Field(default=None, description="OAuth 2.0 scope")
    audience: Optional[str] = Field(default=None, description="OAuth 2.0 audience")
    use_pkce: bool = Field(default=True, description="Use PKCE for public clients")
    additional_params: Dict[str, Any] = Field(default_factory=dict, description="Additional OAuth parameters")


class RateLimitConfig(BaseModel):
    """Rate limiting configuration."""
    
    enabled: bool = Field(default=True, description="Whether rate limiting is enabled")
    max_requests: int = Field(default=100, ge=1, le=10000, description="Maximum requests per window")
    window_seconds: int = Field(default=3600, ge=1, le=86400, description="Rate limit window in seconds")
    burst_size: int = Field(default=10, ge=1, le=1000, description="Burst size for token bucket")
    identifier_field: str = Field(default="client_id", description="Field to use for rate limit identification")
    
    @validator("max_requests")
    def validate_max_requests(cls, v: int) -> int:
        if v < 1 or v > 10000:
            raise ValueError("Max requests must be between 1 and 10000")
        return v


class RetryConfig(BaseModel):
    """Retry configuration."""
    
    enabled: bool = Field(default=True, description="Whether retry is enabled")
    max_attempts: int = Field(default=5, ge=1, le=10, description="Maximum retry attempts")
    base_delay_seconds: float = Field(default=1.0, ge=0.1, le=60.0, description="Base delay for exponential backoff")
    max_delay_seconds: float = Field(default=60.0, ge=1.0, le=300.0, description="Maximum delay for exponential backoff")
    exponential_base: float = Field(default=2.0, ge=1.1, le=5.0, description="Exponential backoff multiplier")
    
    @validator("max_attempts")
    def validate_max_attempts(cls, v: int) -> int:
        if v < 1 or v > 10:
            raise ValueError("Max attempts must be between 1 and 10")
        return v


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration."""
    
    enabled: bool = Field(default=True, description="Whether circuit breaker is enabled")
    failure_threshold: int = Field(default=5, ge=1, le=20, description="Number of failures before opening circuit")
    recovery_timeout_seconds: int = Field(default=60, ge=10, le=3600, description="Recovery timeout in seconds")
    success_threshold: int = Field(default=3, ge=1, le=10, description="Number of successes before closing circuit")
    
    @validator("failure_threshold")
    def validate_failure_threshold(cls, v: int) -> int:
        if v < 1 or v > 20:
            raise ValueError("Failure threshold must be between 1 and 20")
        return v


class SyncConfig(BaseModel):
    """Synchronization configuration."""
    
    enabled: bool = Field(default=True, description="Whether synchronization is enabled")
    frequency: SyncFrequency = Field(default=SyncFrequency.EVERY_15_MINUTES, description="Sync frequency")
    direction: ConflictResolution = Field(default=ConflictResolution.LAST_WRITE_WINS, description="Conflict resolution strategy")
    lag_threshold_seconds: int = Field(default=5, ge=1, le=300, description="Maximum acceptable sync lag in seconds")
    batch_size: int = Field(default=100, ge=1, le=1000, description="Batch size for bulk operations")
    enable_real_time: bool = Field(default=False, description="Enable real-time synchronization")
    
    @validator("lag_threshold_seconds")
    def validate_lag_threshold(cls, v: int) -> int:
        if v < 1 or v > 300:
            raise ValueError("Lag threshold must be between 1 and 300 seconds")
        return v


class SecurityConfig(BaseModel):
    """Security configuration."""
    
    tls_version: TLSVersion = Field(default=TLSVersion.TLS_1_3, description="Minimum TLS version")
    encryption_algorithm: EncryptionAlgorithm = Field(default=EncryptionAlgorithm.AES_256_GCM, description="Encryption algorithm")
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")
    ssl_cert_path: Optional[str] = Field(default=None, description="Path to SSL certificate")
    ssl_key_path: Optional[str] = Field(default=None, description="Path to SSL private key")
    cipher_suites: List[str] = Field(default_factory=list, description="Allowed cipher suites")
    
    @validator("cipher_suites")
    def validate_cipher_suites(cls, v: List[str]) -> List[str]:
        allowed_suites = [
            "ECDHE+AESGCM", "ECDHE+CHACHA20", "DHE+AESGCM", "DHE+CHACHA20",
            "ECDHE+AES", "DHE+AES", "RSA+AESGCM", "RSA+AES"
        ]
        if v and not all(suite in allowed_suites for suite in v):
            raise ValueError("Invalid cipher suite specified")
        return v


class MonitoringConfig(BaseModel):
    """Monitoring and alerting configuration."""
    
    enabled: bool = Field(default=True, description="Whether monitoring is enabled")
    health_check_interval_seconds: int = Field(default=60, ge=10, le=3600, description="Health check interval")
    metrics_enabled: bool = Field(default=True, description="Whether metrics collection is enabled")
    alerting_enabled: bool = Field(default=True, description="Whether alerting is enabled")
    alert_thresholds: Dict[str, float] = Field(default_factory=lambda: {
        "error_rate": 0.1,
        "response_time_ms": 5000.0,
        "sync_lag_seconds": 10.0
    }, description="Alert thresholds")
    notification_channels: List[str] = Field(default_factory=lambda: ["email"], description="Notification channels")


# Integration-Specific Configuration Models

class SalesforceIntegrationConfig(BaseIntegrationConfig):
    """Salesforce integration configuration."""
    
    instance_url: HttpUrl = Field(description="Salesforce instance URL")
    api_version: str = Field(default="58.0", description="Salesforce API version")
    oauth: OAuth2ClientConfig = Field(description="OAuth 2.0 configuration")
    username: Optional[str] = Field(default=None, description="Salesforce username for JWT flow")
    private_key_path: Optional[str] = Field(default=None, description="Path to private key for JWT flow")
    consumer_key: Optional[str] = Field(default=None, description="Connected app consumer key")
    
    # Salesforce-specific settings
    enable_bulk_api: bool = Field(default=True, description="Enable Bulk API 2.0")
    enable_platform_events: bool = Field(default=True, description="Enable Platform Events")
    enable_omni_channel: bool = Field(default=True, description="Enable Omni-Channel integration")
    sync_objects: List[str] = Field(default_factory=lambda: ["Case", "Contact", "Account"], description="Objects to sync")
    
    # Nested configurations
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig, description="Rate limiting configuration")
    retry: RetryConfig = Field(default_factory=RetryConfig, description="Retry configuration")
    circuit_breaker: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig, description="Circuit breaker configuration")
    sync: SyncConfig = Field(default_factory=SyncConfig, description="Synchronization configuration")
    security: SecurityConfig = Field(default_factory=SecurityConfig, description="Security configuration")
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig, description="Monitoring configuration")


class SlackIntegrationConfig(BaseIntegrationConfig):
    """Slack integration configuration."""
    
    bot_token: str = Field(description="Slack bot token")
    signing_secret: str = Field(description="Slack signing secret for webhook verification")
    app_token: Optional[str] = Field(default=None, description="Slack app token for socket mode")
    
    # Slack-specific settings
    enable_socket_mode: bool = Field(default=True, description="Enable Socket Mode for real-time events")
    enable_interactive_components: bool = Field(default=True, description="Enable interactive components")
    enable_file_sharing: bool = Field(default=True, description="Enable file sharing")
    default_channel: Optional[str] = Field(default=None, description="Default channel for messages")
    
    # Nested configurations
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig, description="Rate limiting configuration")
    retry: RetryConfig = Field(default_factory=RetryConfig, description="Retry configuration")
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig, description="Monitoring configuration")


class TeamsIntegrationConfig(BaseIntegrationConfig):
    """Microsoft Teams integration configuration."""
    
    app_id: str = Field(description="Teams app ID")
    app_password: str = Field(description="Teams app password")
    tenant_id: str = Field(description="Azure AD tenant ID")
    
    # Teams-specific settings
    enable_message_reactions: bool = Field(default=True, description="Enable message reactions")
    enable_file_sharing: bool = Field(default=True, description="Enable file sharing")
    enable_meeting_integration: bool = Field(default=False, description="Enable meeting integration")
    default_team_id: Optional[str] = Field(default=None, description="Default team ID")
    
    # Nested configurations
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig, description="Rate limiting configuration")
    retry: RetryConfig = Field(default_factory=RetryConfig, description="Retry configuration")
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig, description="Monitoring configuration")


class EmailIntegrationConfig(BaseIntegrationConfig):
    """Email integration configuration."""
    
    # IMAP settings
    imap_server: str = Field(description="IMAP server hostname")
    imap_port: int = Field(default=993, ge=1, le=65535, description="IMAP server port")
    imap_username: str = Field(description="IMAP username")
    imap_password: str = Field(description="IMAP password")
    imap_use_ssl: bool = Field(default=True, description="Use SSL for IMAP connection")
    
    # SMTP settings
    smtp_server: str = Field(description="SMTP server hostname")
    smtp_port: int = Field(default=587, ge=1, le=65535, description="SMTP server port")
    smtp_username: str = Field(description="SMTP username")
    smtp_password: str = Field(description="SMTP password")
    smtp_use_tls: bool = Field(default=True, description="Use TLS for SMTP connection")
    
    # Email-specific settings
    from_address: str = Field(description="From email address")
    from_name: Optional[str] = Field(default=None, description="From display name")
    enable_auto_responder: bool = Field(default=True, description="Enable auto-responder")
    enable_spf_check: bool = Field(default=True, description="Enable SPF validation")
    enable_dkim_check: bool = Field(default=True, description="Enable DKIM validation")
    
    # Nested configurations
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig, description="Rate limiting configuration")
    retry: RetryConfig = Field(default_factory=RetryConfig, description="Retry configuration")
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig, description="Monitoring configuration")


# Configuration Management

class IntegrationConfigManager:
    """Manages integration configurations."""
    
    def __init__(self):
        self.settings = get_settings()
    
    def get_salesforce_config(self, organization_id: str) -> SalesforceIntegrationConfig:
        """Get Salesforce integration configuration."""
        # This would typically load from database or environment
        # For now, return a default configuration
        return SalesforceIntegrationConfig(
            organization_id=organization_id,
            instance_url="https://example.salesforce.com",
            oauth=OAuth2ClientConfig(
                client_id="salesforce_client_id",
                client_secret="salesforce_client_secret",
                authorization_url="https://login.salesforce.com/services/oauth2/authorize",
                token_url="https://login.salesforce.com/services/oauth2/token",
                redirect_uri="https://your-app.com/auth/salesforce/callback",
                scope="api refresh_token"
            )
        )
    
    def get_slack_config(self, organization_id: str) -> SlackIntegrationConfig:
        """Get Slack integration configuration."""
        return SlackIntegrationConfig(
            organization_id=organization_id,
            bot_token="xoxb-your-bot-token",
            signing_secret="your-signing-secret"
        )
    
    def get_teams_config(self, organization_id: str) -> TeamsIntegrationConfig:
        """Get Teams integration configuration."""
        return TeamsIntegrationConfig(
            organization_id=organization_id,
            app_id="your-app-id",
            app_password="your-app-password",
            tenant_id="your-tenant-id"
        )
    
    def get_email_config(self, organization_id: str) -> EmailIntegrationConfig:
        """Get email integration configuration."""
        return EmailIntegrationConfig(
            organization_id=organization_id,
            imap_server="imap.example.com",
            imap_username="user@example.com",
            imap_password="password",
            smtp_server="smtp.example.com",
            smtp_username="user@example.com",
            smtp_password="password",
            from_address="noreply@example.com",
            from_name="AI Customer Service"
        )
    
    def validate_config(self, config: BaseIntegrationConfig) -> bool:
        """Validate integration configuration."""
        try:
            # Basic validation already done by Pydantic
            # Additional business logic validation can be added here
            
            # Check if integration is enabled at organization level
            if not config.enabled:
                return True
            
            # Validate OAuth configuration if present
            if hasattr(config, 'oauth') and config.oauth:
                oauth_config = config.oauth
                if not oauth_config.client_id or not oauth_config.client_secret:
                    raise ValueError("OAuth client ID and secret are required")
            
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False


# Default configurations
DEFAULT_INTEGRATION_CONFIGS = {
    "salesforce": SalesforceIntegrationConfig,
    "slack": SlackIntegrationConfig,
    "teams": TeamsIntegrationConfig,
    "email": EmailIntegrationConfig,
}

# Export configuration models
__all__ = [
    "OAuth2Provider",
    "SyncFrequency",
    "ConflictResolution",
    "TLSVersion",
    "EncryptionAlgorithm",
    "BaseIntegrationConfig",
    "OAuth2ClientConfig",
    "RateLimitConfig",
    "RetryConfig",
    "CircuitBreakerConfig",
    "SyncConfig",
    "SecurityConfig",
    "MonitoringConfig",
    "SalesforceIntegrationConfig",
    "SlackIntegrationConfig",
    "TeamsIntegrationConfig",
    "EmailIntegrationConfig",
    "IntegrationConfigManager",
    "DEFAULT_INTEGRATION_CONFIGS",
]