"""
Authentication provider types and enumerations.

Defines the supported authentication providers and related types
for OAuth 2.0, OIDC, SAML, and other authentication mechanisms.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, Any, Optional


class AuthProviderType(str, Enum):
    """Supported authentication provider types."""
    
    # OAuth 2.0 / OIDC Providers
    OAUTH2 = "oauth2"
    OIDC = "oidc"
    
    # Enterprise SSO Providers
    SAML = "saml"
    LDAP = "ldap"
    ACTIVE_DIRECTORY = "active_directory"
    
    # Social Providers
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    FACEBOOK = "facebook"
    GITHUB = "github"
    LINKEDIN = "linkedin"
    
    # Enterprise Providers
    SALESFORCE = "salesforce"
    OKTA = "okta"
    AUTH0 = "auth0"
    ONelogin = "onelogin"
    PING = "ping"
    
    # Custom Providers
    CUSTOM = "custom"


class OAuth2GrantType(str, Enum):
    """OAuth 2.0 grant types."""
    
    AUTHORIZATION_CODE = "authorization_code"
    CLIENT_CREDENTIALS = "client_credentials"
    RESOURCE_OWNER_PASSWORD = "password"
    REFRESH_TOKEN = "refresh_token"
    IMPLICIT = "implicit"
    DEVICE_CODE = "urn:ietf:params:oauth:grant-type:device_code"


class OAuth2ResponseType(str, Enum):
    """OAuth 2.0 response types."""
    
    CODE = "code"
    TOKEN = "token"
    ID_TOKEN = "id_token"
    CODE_TOKEN = "code token"
    CODE_ID_TOKEN = "code id_token"
    ID_TOKEN_TOKEN = "id_token token"
    CODE_ID_TOKEN_TOKEN = "code id_token token"


class OAuth2Scope(str, Enum):
    """OAuth 2.0 standard scopes."""
    
    OPENID = "openid"
    PROFILE = "profile"
    EMAIL = "email"
    ADDRESS = "address"
    PHONE = "phone"
    OFFLINE_ACCESS = "offline_access"
    
    # Custom scopes for AI Customer Service Agent
    READ_CONVERSATIONS = "read:conversations"
    WRITE_CONVERSATIONS = "write:conversations"
    READ_ANALYTICS = "read:analytics"
    WRITE_ANALYTICS = "write:analytics"
    READ_INTEGRATIONS = "read:integrations"
    WRITE_INTEGRATIONS = "write:integrations"
    ADMIN = "admin"


class TokenType(str, Enum):
    """Token types."""
    
    ACCESS_TOKEN = "access_token"
    REFRESH_TOKEN = "refresh_token"
    ID_TOKEN = "id_token"
    AUTHORIZATION_CODE = "authorization_code"


class SAMLNameIDFormat(str, Enum):
    """SAML NameID formats."""
    
    EMAIL_ADDRESS = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
    TRANSIENT = "urn:oasis:names:tc:SAML:2.0:nameid-format:transient"
    PERSISTENT = "urn:oasis:names:tc:SAML:2.0:nameid-format:persistent"
    UNSPECIFIED = "urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified"


class SAMLBinding(str, Enum):
    """SAML binding types."""
    
    HTTP_POST = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
    HTTP_REDIRECT = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
    HTTP_ARTIFACT = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Artifact"
    SOAP = "urn:oasis:names:tc:SAML:2.0:bindings:SOAP"


class AuthenticationStatus(str, Enum):
    """Authentication status."""
    
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class MFAStatus(str, Enum):
    """Multi-factor authentication status."""
    
    DISABLED = "disabled"
    OPTIONAL = "optional"
    REQUIRED = "required"
    ENFORCED = "enforced"


class SecurityLevel(str, Enum):
    """Security assurance levels."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    MAXIMUM = "maximum"


# Provider-specific configuration templates
PROVIDER_CONFIG_TEMPLATES: Dict[AuthProviderType, Dict[str, Any]] = {
    AuthProviderType.GOOGLE: {
        "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_endpoint": "https://oauth2.googleapis.com/token",
        "userinfo_endpoint": "https://openidconnect.googleapis.com/v1/userinfo",
        "jwks_uri": "https://www.googleapis.com/oauth2/v3/certs",
        "scopes": ["openid", "profile", "email"],
        "additional_params": {"access_type": "offline", "prompt": "consent"}
    },
    AuthProviderType.MICROSOFT: {
        "authorization_endpoint": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_endpoint": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "userinfo_endpoint": "https://graph.microsoft.com/v1.0/me",
        "jwks_uri": "https://login.microsoftonline.com/common/discovery/v2.0/keys",
        "scopes": ["openid", "profile", "email", "User.Read"],
        "additional_params": {"response_mode": "query"}
    },
    AuthProviderType.OKTA: {
        "authorization_endpoint": "https://{domain}/oauth2/v1/authorize",
        "token_endpoint": "https://{domain}/oauth2/v1/token",
        "userinfo_endpoint": "https://{domain}/oauth2/v1/userinfo",
        "jwks_uri": "https://{domain}/oauth2/v1/keys",
        "scopes": ["openid", "profile", "email"],
        "additional_params": {}
    },
    AuthProviderType.AUTH0: {
        "authorization_endpoint": "https://{domain}/authorize",
        "token_endpoint": "https://{domain}/oauth/token",
        "userinfo_endpoint": "https://{domain}/userinfo",
        "jwks_uri": "https://{domain}/.well-known/jwks.json",
        "scopes": ["openid", "profile", "email"],
        "additional_params": {}
    }
}


# Default authentication settings
DEFAULT_AUTH_SETTINGS = {
    "token_expiry_seconds": {
        "access_token": 3600,      # 1 hour
        "refresh_token": 2592000,  # 30 days
        "id_token": 3600,          # 1 hour
        "authorization_code": 600  # 10 minutes
    },
    "security_settings": {
        "require_pkce": True,
        "require_state": True,
        "allow_implicit_flow": False,
        "max_auth_attempts": 5,
        "lockout_duration_seconds": 300,  # 5 minutes
        "session_timeout_seconds": 86400    # 24 hours
    },
    "rate_limits": {
        "authorization_requests_per_minute": 60,
        "token_requests_per_minute": 120,
        "failed_auth_attempts_per_hour": 30
    }
}


class AuthenticationRequest:
    """Represents an authentication request."""
    
    def __init__(
        self,
        provider_type: AuthProviderType,
        client_id: str,
        redirect_uri: str,
        scope: str,
        state: Optional[str] = None,
        nonce: Optional[str] = None,
        response_type: str = "code",
        response_mode: str = "query",
        prompt: Optional[str] = None,
        max_age: Optional[int] = None,
        login_hint: Optional[str] = None,
        organization_id: Optional[str] = None,
        additional_params: Optional[Dict[str, Any]] = None
    ):
        self.provider_type = provider_type
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.scope = scope
        self.state = state
        self.nonce = nonce
        self.response_type = response_type
        self.response_mode = response_mode
        self.prompt = prompt
        self.max_age = max_age
        self.login_hint = login_hint
        self.organization_id = organization_id
        self.additional_params = additional_params or {}
        self.created_at = datetime.utcnow()
        self.request_id = self._generate_request_id()
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID."""
        import uuid
        return str(uuid.uuid4())


class AuthenticationResponse:
    """Represents an authentication response."""
    
    def __init__(
        self,
        success: bool,
        provider_type: AuthProviderType,
        user_info: Optional[Dict[str, Any]] = None,
        tokens: Optional[Dict[str, str]] = None,
        error: Optional[str] = None,
        error_description: Optional[str] = None,
        state: Optional[str] = None,
        organization_id: Optional[str] = None
    ):
        self.success = success
        self.provider_type = provider_type
        self.user_info = user_info or {}
        self.tokens = tokens or {}
        self.error = error
        self.error_description = error_description
        self.state = state
        self.organization_id = organization_id
        self.created_at = datetime.utcnow()


class TokenValidationResult:
    """Result of token validation."""
    
    def __init__(
        self,
        valid: bool,
        user_id: Optional[str] = None,
        client_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        scope: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        error: Optional[str] = None,
        claims: Optional[Dict[str, Any]] = None
    ):
        self.valid = valid
        self.user_id = user_id
        self.client_id = client_id
        self.organization_id = organization_id
        self.scope = scope
        self.expires_at = expires_at
        self.error = error
        self.claims = claims or {}


# Export types
__all__ = [
    "AuthProviderType",
    "OAuth2GrantType",
    "OAuth2ResponseType",
    "OAuth2Scope",
    "TokenType",
    "SAMLNameIDFormat",
    "SAMLBinding",
    "AuthenticationStatus",
    "MFAStatus",
    "SecurityLevel",
    "PROVIDER_CONFIG_TEMPLATES",
    "DEFAULT_AUTH_SETTINGS",
    "AuthenticationRequest",
    "AuthenticationResponse",
    "TokenValidationResult"
]