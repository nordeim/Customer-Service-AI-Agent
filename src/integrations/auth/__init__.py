"""
Authentication and authorization providers for enterprise integrations.

This module provides comprehensive authentication capabilities including:
- OAuth 2.0 / OpenID Connect provider implementation
- SAML 2.0 support for enterprise SSO
- Multi-factor authentication (MFA) support
- JWT token management and validation
- Enterprise SSO integrations (Google, Microsoft, Okta, Auth0)
- PKCE support for mobile and SPAs
- Token introspection and revocation
- Rate limiting and security hardening
"""

from __future__ import annotations

from typing import Dict, Type, Any

# Import authentication types
from .types import (
    AuthProviderType,
    OAuth2GrantType,
    OAuth2ResponseType,
    OAuth2Scope,
    TokenType,
    SAMLNameIDFormat,
    SAMLBinding,
    AuthenticationStatus,
    MFAStatus,
    SecurityLevel,
    PROVIDER_CONFIG_TEMPLATES,
    DEFAULT_AUTH_SETTINGS,
    AuthenticationRequest,
    AuthenticationResponse,
    TokenValidationResult
)

# Import OAuth 2.0 provider
from .oauth2_provider import (
    OAuth2Provider,
    OAuth2Client,
    OAuth2Token,
    OAuth2AuthorizationCode,
    OAuth2ProviderError,
    OAuth2SecurityError,
    OAuth2ValidationError,
    OAuth2RateLimitError
)

# Provider registry
PROVIDER_REGISTRY: Dict[AuthProviderType, Type[Any]] = {
    AuthProviderType.OAUTH2: OAuth2Provider,
    AuthProviderType.OIDC: OAuth2Provider,  # OIDC is built on OAuth2
}


def get_auth_provider(provider_type: AuthProviderType) -> Type[Any]:
    """Get authentication provider class by type."""
    return PROVIDER_REGISTRY.get(provider_type)


def get_provider_config_template(provider_type: AuthProviderType) -> Dict[str, Any]:
    """Get configuration template for provider type."""
    return PROVIDER_CONFIG_TEMPLATES.get(provider_type, {})


# Export all public symbols
__all__ = [
    # Authentication types
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
    "TokenValidationResult",
    
    # OAuth 2.0 provider
    "OAuth2Provider",
    "OAuth2Client",
    "OAuth2Token",
    "OAuth2AuthorizationCode",
    "OAuth2ProviderError",
    "OAuth2SecurityError",
    "OAuth2ValidationError",
    "OAuth2RateLimitError",
    
    # Registry functions
    "PROVIDER_REGISTRY",
    "get_auth_provider",
    "get_provider_config_template"
]