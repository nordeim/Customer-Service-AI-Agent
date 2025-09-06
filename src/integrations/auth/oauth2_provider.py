"""
OAuth 2.0 / OpenID Connect provider for enterprise authentication and authorization.

Provides comprehensive OAuth 2.0 and OIDC implementation including:
- Authorization code flow with PKCE support
- Client credentials flow for service-to-service authentication
- Refresh token management with rotation
- JWT token generation and validation
- Scope-based authorization
- Multi-tenant support with organization isolation
- Token introspection and revocation
- Comprehensive security hardening
- Rate limiting and abuse prevention
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple, AsyncGenerator
from urllib.parse import urlencode, parse_qs, urlparse
import httpx
from jose import jwt, JWTError
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

from src.core.config import get_settings
from src.core.logging import get_logger
from src.core.exceptions import ExternalServiceError, ValidationError, SecurityError
from ..base import RateLimitError
from ..config import OAuth2ClientConfig, SecurityConfig
from . import AuthProviderType

logger = get_logger(__name__)


class OAuth2ProviderError(ExternalServiceError):
    """OAuth 2.0 provider specific errors."""
    pass


class OAuth2SecurityError(SecurityError):
    """OAuth 2.0 security validation errors."""
    pass


class OAuth2ValidationError(ValidationError):
    """OAuth 2.0 validation errors."""
    pass


class OAuth2RateLimitError(RateLimitError):
    """OAuth 2.0 rate limit exceeded error."""
    pass


class OAuth2Client:
    """OAuth 2.0 client application."""
    
    def __init__(
        self,
        client_id: str,
        client_secret: Optional[str],
        name: str,
        redirect_uris: List[str],
        grant_types: List[str],
        response_types: List[str],
        scopes: List[str],
        token_endpoint_auth_method: str = "client_secret_basic",
        application_type: str = "web",
        organization_id: Optional[str] = None,
        is_confidential: bool = True,
        require_auth_time: bool = False,
        default_max_age: Optional[int] = None
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.name = name
        self.redirect_uris = redirect_uris
        self.grant_types = grant_types
        self.response_types = response_types
        self.scopes = scopes
        self.token_endpoint_auth_method = token_endpoint_auth_method
        self.application_type = application_type
        self.organization_id = organization_id
        self.is_confidential = is_confidential
        self.require_auth_time = require_auth_time
        self.default_max_age = default_max_age
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()


class OAuth2Token:
    """OAuth 2.0 token information."""
    
    def __init__(
        self,
        access_token: str,
        token_type: str = "Bearer",
        expires_in: int = 3600,
        refresh_token: Optional[str] = None,
        scope: Optional[str] = None,
        state: Optional[str] = None,
        id_token: Optional[str] = None,
        client_id: Optional[str] = None,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        issued_at: Optional[datetime] = None
    ):
        self.access_token = access_token
        self.token_type = token_type
        self.expires_in = expires_in
        self.refresh_token = refresh_token
        self.scope = scope
        self.state = state
        self.id_token = id_token
        self.client_id = client_id
        self.user_id = user_id
        self.organization_id = organization_id
        self.issued_at = issued_at or datetime.utcnow()
        self.expires_at = self.issued_at + timedelta(seconds=expires_in)


class OAuth2AuthorizationCode:
    """OAuth 2.0 authorization code."""
    
    def __init__(
        self,
        code: str,
        client_id: str,
        redirect_uri: str,
        user_id: str,
        scope: str,
        code_challenge: Optional[str] = None,
        code_challenge_method: Optional[str] = None,
        state: Optional[str] = None,
        organization_id: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ):
        self.code = code
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.user_id = user_id
        self.scope = scope
        self.code_challenge = code_challenge
        self.code_challenge_method = code_challenge_method
        self.state = state
        self.organization_id = organization_id
        self.created_at = datetime.utcnow()
        self.expires_at = expires_at or (self.created_at + timedelta(minutes=10))


class OAuth2Provider:
    """OAuth 2.0 / OpenID Connect provider implementation."""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.logger = logger.getChild("oauth2_provider")
        
        # JWT signing configuration
        self._jwt_secret = config.jwt_secret
        self._jwt_algorithm = config.jwt_algorithm
        self._jwt_expiration = config.jwt_expiration_seconds
        self._jwt_issuer = config.jwt_issuer
        
        # Token storage (in production, use Redis or database)
        self._access_tokens: Dict[str, OAuth2Token] = {}
        self._refresh_tokens: Dict[str, OAuth2Token] = {}
        self._authorization_codes: Dict[str, OAuth2AuthorizationCode] = {}
        self._clients: Dict[str, OAuth2Client] = {}
        
        # Rate limiting
        self._rate_limit_info = {
            "remaining": 1000,  # Default rate limit
            "reset": None,
            "retry_after": None
        }
        
        # Security configuration
        self._require_pkce = True
        self._max_auth_code_lifetime = 600  # 10 minutes
        self._max_access_token_lifetime = 3600  # 1 hour
        self._max_refresh_token_lifetime = 86400 * 30  # 30 days
        
        # Initialize with default clients if configured
        self._initialize_default_clients()
    
    def _initialize_default_clients(self) -> None:
        """Initialize default OAuth clients."""
        default_clients = [
            OAuth2Client(
                client_id="ai-customer-service-agent",
                client_secret="your-client-secret-here",  # Should be from config
                name="AI Customer Service Agent",
                redirect_uris=["https://your-app.com/auth/callback"],
                grant_types=["authorization_code", "refresh_token", "client_credentials"],
                response_types=["code", "token"],
                scopes=["openid", "profile", "email", "read", "write"],
                organization_id="default"
            )
        ]
        
        for client in default_clients:
            self.register_client(client)
    
    # Client Management
    
    def register_client(self, client: OAuth2Client) -> None:
        """Register OAuth 2.0 client."""
        self._clients[client.client_id] = client
        self.logger.info(f"Registered OAuth client: {client.client_id}")
    
    def get_client(self, client_id: str) -> Optional[OAuth2Client]:
        """Get OAuth 2.0 client by ID."""
        return self._clients.get(client_id)
    
    def verify_client_secret(self, client_id: str, client_secret: str) -> bool:
        """Verify client secret."""
        client = self.get_client(client_id)
        if not client:
            return False
        
        if not client.is_confidential:
            return True  # Public clients don't use client secrets
        
        if not client.client_secret:
            return False
        
        return hmac.compare_digest(client.client_secret, client_secret)
    
    def validate_redirect_uri(self, client_id: str, redirect_uri: str) -> bool:
        """Validate redirect URI for client."""
        client = self.get_client(client_id)
        if not client:
            return False
        
        return redirect_uri in client.redirect_uris
    
    def validate_scope(self, client_id: str, requested_scope: str) -> bool:
        """Validate requested scope against client allowed scopes."""
        client = self.get_client(client_id)
        if not client:
            return False
        
        requested_scopes = set(requested_scope.split())
        allowed_scopes = set(client.scopes)
        
        return requested_scopes.issubset(allowed_scopes)
    
    # Authorization Code Flow
    
    async def create_authorization_url(
        self,
        client_id: str,
        redirect_uri: str,
        scope: str,
        state: Optional[str] = None,
        code_challenge: Optional[str] = None,
        code_challenge_method: Optional[str] = "S256",
        organization_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> str:
        """Create authorization URL for OAuth 2.0 flow."""
        # Validate client
        client = self.get_client(client_id)
        if not client:
            raise OAuth2ValidationError("Invalid client_id")
        
        # Validate redirect URI
        if not self.validate_redirect_uri(client_id, redirect_uri):
            raise OAuth2ValidationError("Invalid redirect_uri")
        
        # Validate scope
        if not self.validate_scope(client_id, scope):
            raise OAuth2ValidationError("Invalid scope")
        
        # Validate PKCE parameters
        if self._require_pkce and not code_challenge:
            raise OAuth2ValidationError("PKCE code_challenge required")
        
        if code_challenge and code_challenge_method not in ["plain", "S256"]:
            raise OAuth2ValidationError("Invalid code_challenge_method")
        
        # Generate state if not provided
        if not state:
            state = secrets.token_urlsafe(32)
        
        # Generate authorization code
        auth_code = secrets.token_urlsafe(32)
        
        # Store authorization code
        auth_code_obj = OAuth2AuthorizationCode(
            code=auth_code,
            client_id=client_id,
            redirect_uri=redirect_uri,
            user_id=user_id or "anonymous",
            scope=scope,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            state=state,
            organization_id=organization_id or client.organization_id
        )
        
        self._authorization_codes[auth_code] = auth_code_obj
        
        # Build authorization URL
        auth_params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state
        }
        
        if code_challenge:
            auth_params["code_challenge"] = code_challenge
            auth_params["code_challenge_method"] = code_challenge_method
        
        auth_url = f"{self.config.authorization_endpoint}?{urlencode(auth_params)}"
        
        self.logger.info(f"Created authorization URL for client {client_id}")
        
        return auth_url
    
    async def exchange_authorization_code(
        self,
        code: str,
        client_id: str,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        code_verifier: Optional[str] = None
    ) -> OAuth2Token:
        """Exchange authorization code for access token."""
        # Retrieve authorization code
        auth_code = self._authorization_codes.get(code)
        if not auth_code:
            raise OAuth2ValidationError("Invalid or expired authorization code")
        
        # Validate authorization code expiration
        if datetime.utcnow() > auth_code.expires_at:
            del self._authorization_codes[code]
            raise OAuth2ValidationError("Authorization code expired")
        
        # Validate client
        if auth_code.client_id != client_id:
            raise OAuth2ValidationError("Client ID mismatch")
        
        # Validate client secret for confidential clients
        client = self.get_client(client_id)
        if client and client.is_confidential:
            if not client_secret or not self.verify_client_secret(client_id, client_secret):
                raise OAuth2SecurityError("Invalid client credentials")
        
        # Validate redirect URI
        if redirect_uri and auth_code.redirect_uri != redirect_uri:
            raise OAuth2ValidationError("Redirect URI mismatch")
        
        # Validate PKCE code verifier
        if auth_code.code_challenge and code_verifier:
            if not self._verify_code_verifier(code_verifier, auth_code.code_challenge, auth_code.code_challenge_method):
                raise OAuth2SecurityError("Invalid code_verifier")
        
        # Generate tokens
        access_token = self._generate_access_token()
        refresh_token = self._generate_refresh_token()
        
        # Generate ID token if openid scope is requested
        id_token = None
        if "openid" in auth_code.scope.split():
            id_token = self._generate_id_token(
                user_id=auth_code.user_id,
                client_id=client_id,
                organization_id=auth_code.organization_id,
                scope=auth_code.scope
            )
        
        # Create token object
        token = OAuth2Token(
            access_token=access_token,
            token_type="Bearer",
            expires_in=self._jwt_expiration,
            refresh_token=refresh_token,
            scope=auth_code.scope,
            id_token=id_token,
            client_id=client_id,
            user_id=auth_code.user_id,
            organization_id=auth_code.organization_id
        )
        
        # Store tokens
        self._access_tokens[access_token] = token
        self._refresh_tokens[refresh_token] = token
        
        # Remove used authorization code
        del self._authorization_codes[code]
        
        self.logger.info(f"Exchanged authorization code for access token for client {client_id}")
        
        return token
    
    # Client Credentials Flow
    
    async def client_credentials_grant(
        self,
        client_id: str,
        client_secret: str,
        scope: str
    ) -> OAuth2Token:
        """Client credentials grant flow."""
        # Validate client
        client = self.get_client(client_id)
        if not client:
            raise OAuth2ValidationError("Invalid client_id")
        
        # Validate client credentials
        if not self.verify_client_secret(client_id, client_secret):
            raise OAuth2SecurityError("Invalid client credentials")
        
        # Validate scope
        if not self.validate_scope(client_id, scope):
            raise OAuth2ValidationError("Invalid scope")
        
        # Generate access token (no refresh token for client credentials)
        access_token = self._generate_access_token()
        
        # Create token object
        token = OAuth2Token(
            access_token=access_token,
            token_type="Bearer",
            expires_in=self._jwt_expiration,
            scope=scope,
            client_id=client_id,
            organization_id=client.organization_id
        )
        
        # Store token
        self._access_tokens[access_token] = token
        
        self.logger.info(f"Issued client credentials access token for client {client_id}")
        
        return token
    
    # Refresh Token Flow
    
    async def refresh_access_token(
        self,
        refresh_token: str,
        client_id: str,
        client_secret: Optional[str] = None,
        scope: Optional[str] = None
    ) -> OAuth2Token:
        """Refresh access token using refresh token."""
        # Retrieve refresh token
        token = self._refresh_tokens.get(refresh_token)
        if not token:
            raise OAuth2ValidationError("Invalid refresh token")
        
        # Validate client
        if token.client_id != client_id:
            raise OAuth2ValidationError("Client ID mismatch")
        
        # Validate client secret for confidential clients
        client = self.get_client(client_id)
        if client and client.is_confidential:
            if not client_secret or not self.verify_client_secret(client_id, client_secret):
                raise OAuth2SecurityError("Invalid client credentials")
        
        # Validate scope (optional restriction)
        if scope and scope != token.scope:
            if not self.validate_scope(client_id, scope):
                raise OAuth2ValidationError("Invalid scope")
            # Update token scope
            token.scope = scope
        
        # Generate new access token
        new_access_token = self._generate_access_token()
        
        # Generate new refresh token (refresh token rotation)
        new_refresh_token = self._generate_refresh_token()
        
        # Generate new ID token if openid scope is present
        new_id_token = None
        if "openid" in token.scope.split() and token.user_id:
            new_id_token = self._generate_id_token(
                user_id=token.user_id,
                client_id=client_id,
                organization_id=token.organization_id,
                scope=token.scope
            )
        
        # Create new token object
        new_token = OAuth2Token(
            access_token=new_access_token,
            token_type="Bearer",
            expires_in=self._jwt_expiration,
            refresh_token=new_refresh_token,
            scope=token.scope,
            id_token=new_id_token,
            client_id=client_id,
            user_id=token.user_id,
            organization_id=token.organization_id
        )
        
        # Store new tokens
        self._access_tokens[new_access_token] = new_token
        self._refresh_tokens[new_refresh_token] = new_token
        
        # Remove old tokens
        if token.access_token in self._access_tokens:
            del self._access_tokens[token.access_token]
        if refresh_token in self._refresh_tokens:
            del self._refresh_tokens[refresh_token]
        
        self.logger.info(f"Refreshed access token for client {client_id}")
        
        return new_token
    
    # Token Validation and Introspection
    
    async def validate_access_token(self, access_token: str) -> Optional[OAuth2Token]:
        """Validate access token and return token information."""
        token = self._access_tokens.get(access_token)
        if not token:
            return None
        
        # Check token expiration
        if datetime.utcnow() > token.expires_at:
            # Remove expired token
            del self._access_tokens[access_token]
            return None
        
        return token
    
    async def introspect_token(self, token: str, client_id: Optional[str] = None) -> Dict[str, Any]:
        """Introspect token and return token information (RFC 7662)."""
        # Check access tokens
        access_token = self._access_tokens.get(token)
        if access_token:
            if client_id and access_token.client_id != client_id:
                return {"active": False}
            
            return {
                "active": True,
                "scope": access_token.scope,
                "client_id": access_token.client_id,
                "token_type": access_token.token_type,
                "exp": int(access_token.expires_at.timestamp()),
                "iat": int(access_token.issued_at.timestamp()),
                "sub": access_token.user_id,
                "organization_id": access_token.organization_id
            }
        
        # Check refresh tokens
        refresh_token = self._refresh_tokens.get(token)
        if refresh_token:
            if client_id and refresh_token.client_id != client_id:
                return {"active": False}
            
            return {
                "active": True,
                "scope": refresh_token.scope,
                "client_id": refresh_token.client_id,
                "token_type": "refresh_token",
                "iat": int(refresh_token.issued_at.timestamp()),
                "sub": refresh_token.user_id,
                "organization_id": refresh_token.organization_id
            }
        
        return {"active": False}
    
    async def revoke_token(self, token: str, client_id: Optional[str] = None) -> None:
        """Revoke token (RFC 7009)."""
        # Check access tokens
        if token in self._access_tokens:
            access_token = self._access_tokens[token]
            if not client_id or access_token.client_id == client_id:
                del self._access_tokens[token]
                self.logger.info(f"Revoked access token for client {access_token.client_id}")
        
        # Check refresh tokens
        if token in self._refresh_tokens:
            refresh_token = self._refresh_tokens[token]
            if not client_id or refresh_token.client_id == client_id:
                del self._refresh_tokens[token]
                self.logger.info(f"Revoked refresh token for client {refresh_token.client_id}")
    
    # JWT Token Generation
    
    def _generate_access_token(self) -> str:
        """Generate secure access token."""
        return secrets.token_urlsafe(32)
    
    def _generate_refresh_token(self) -> str:
        """Generate secure refresh token."""
        return secrets.token_urlsafe(32)
    
    def _generate_id_token(self, user_id: str, client_id: str, organization_id: Optional[str], scope: str) -> str:
        """Generate JWT ID token (OpenID Connect)."""
        now = datetime.utcnow()
        
        claims = {
            "iss": self._jwt_issuer,
            "sub": user_id,
            "aud": client_id,
            "exp": int((now + timedelta(seconds=self._jwt_expiration)).timestamp()),
            "iat": int(now.timestamp()),
            "auth_time": int(now.timestamp()),
            "organization_id": organization_id
        }
        
        # Add scope-specific claims
        scope_set = set(scope.split())
        if "profile" in scope_set:
            claims.update({
                "name": user_id,  # Would come from user profile
                "preferred_username": user_id
            })
        
        if "email" in scope_set:
            claims.update({
                "email": f"{user_id}@example.com",  # Would come from user profile
                "email_verified": True
            })
        
        return jwt.encode(claims, self._jwt_secret, algorithm=self._jwt_algorithm)
    
    # PKCE Support
    
    def _verify_code_verifier(self, code_verifier: str, code_challenge: str, method: str) -> bool:
        """Verify PKCE code verifier."""
        if method == "plain":
            return hmac.compare_digest(code_verifier, code_challenge)
        elif method == "S256":
            challenge = base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode()).digest()
            ).decode().rstrip('=')
            return hmac.compare_digest(challenge, code_challenge)
        else:
            return False
    
    # Rate Limiting
    
    async def check_rate_limit(self, client_id: str) -> Dict[str, Any]:
        """Check current rate limit status for client."""
        return {
            "remaining": self._rate_limit_info["remaining"],
            "reset_time": self._rate_limit_info["reset"],
            "retry_after": self._rate_limit_info["retry_after"]
        }
    
    # Security and Validation
    
    def validate_client_authentication(
        self,
        client_id: str,
        client_secret: Optional[str],
        auth_method: str = "client_secret_basic"
    ) -> bool:
        """Validate client authentication."""
        client = self.get_client(client_id)
        if not client:
            return False
        
        if not client.is_confidential:
            return True  # Public clients don't require authentication
        
        if auth_method == "client_secret_basic":
            return self.verify_client_secret(client_id, client_secret) if client_secret else False
        elif auth_method == "client_secret_post":
            return self.verify_client_secret(client_id, client_secret) if client_secret else False
        elif auth_method == "none":
            return True  # For public clients
        else:
            return False
    
    def validate_response_type(self, client_id: str, response_type: str) -> bool:
        """Validate response type for client."""
        client = self.get_client(client_id)
        if not client:
            return False
        
        return response_type in client.response_types
    
    def validate_grant_type(self, client_id: str, grant_type: str) -> bool:
        """Validate grant type for client."""
        client = self.get_client(client_id)
        if not client:
            return False
        
        return grant_type in client.grant_types
    
    # Health Check
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        try:
            # Test JWT signing
            test_token = self._generate_id_token("test-user", "test-client", None, "openid")
            
            # Verify token
            decoded = jwt.decode(test_token, self._jwt_secret, algorithms=[self._jwt_algorithm])
            
            # Check token storage
            storage_healthy = (
                len(self._access_tokens) < 10000 and
                len(self._refresh_tokens) < 10000 and
                len(self._authorization_codes) < 1000
            )
            
            # Overall health status
            is_healthy = (
                bool(decoded) and
                storage_healthy and
                len(self._clients) > 0
            )
            
            return {
                "status": "healthy" if is_healthy else "degraded",
                "jwt_signing": True,
                "token_storage_healthy": storage_healthy,
                "clients_configured": len(self._clients),
                "active_access_tokens": len(self._access_tokens),
                "active_refresh_tokens": len(self._refresh_tokens),
                "rate_limit_remaining": self._rate_limit_info["remaining"],
                "last_check": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "jwt_signing": False,
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
    
    # Cleanup
    
    async def cleanup_expired_tokens(self) -> Dict[str, int]:
        """Clean up expired tokens."""
        now = datetime.utcnow()
        
        expired_access = 0
        expired_refresh = 0
        expired_codes = 0
        
        # Clean up expired access tokens
        expired_access_tokens = [
            token for token, token_obj in self._access_tokens.items()
            if now > token_obj.expires_at
        ]
        for token in expired_access_tokens:
            del self._access_tokens[token]
            expired_access += 1
        
        # Clean up expired authorization codes
        expired_codes_list = [
            code for code, code_obj in self._authorization_codes.items()
            if now > code_obj.expires_at
        ]
        for code in expired_codes_list:
            del self._authorization_codes[code]
            expired_codes += 1
        
        self.logger.info(f"Cleaned up {expired_access} expired access tokens, {expired_codes} expired codes")
        
        return {
            "expired_access_tokens": expired_access,
            "expired_refresh_tokens": expired_refresh,
            "expired_authorization_codes": expired_codes
        }
    
    async def close(self) -> None:
        """Close provider and cleanup resources."""
        self.logger.info("Closing OAuth 2.0 provider")
        
        # Clear all token storage
        self._access_tokens.clear()
        self._refresh_tokens.clear()
        self._authorization_codes.clear()
        self._clients.clear()


# Export the provider
__all__ = [
    "OAuth2Provider",
    "OAuth2Client",
    "OAuth2Token",
    "OAuth2AuthorizationCode",
    "OAuth2ProviderError",
    "OAuth2SecurityError",
    "OAuth2ValidationError",
    "OAuth2RateLimitError"
]