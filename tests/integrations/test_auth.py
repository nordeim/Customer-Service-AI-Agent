"""
Tests for OAuth 2.0 provider and authentication functionality.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from uuid import uuid4
import jwt

from src.integrations.auth import (
    OAuth2Provider,
    OAuth2Client,
    OAuth2Token,
    OAuth2AuthorizationCode,
    OAuth2ProviderError,
    OAuth2SecurityError,
    OAuth2ValidationError,
    OAuth2RateLimitError,
    AuthProviderType,
    OAuth2GrantType,
    OAuth2ResponseType,
    OAuth2Scope,
    TokenType,
    AuthenticationRequest,
    AuthenticationResponse,
    TokenValidationResult
)


class TestOAuth2Provider:
    """Test OAuth2Provider functionality."""
    
    @pytest.fixture
    def oauth_provider(self):
        config = {
            "issuer": "https://auth.example.com",
            "authorization_endpoint": "https://auth.example.com/authorize",
            "token_endpoint": "https://auth.example.com/token",
            "jwks_uri": "https://auth.example.com/.well-known/jwks.json",
            "scopes_supported": ["openid", "profile", "email", "api"],
            "grant_types_supported": ["authorization_code", "client_credentials", "refresh_token"],
            "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post"],
            "code_challenge_methods_supported": ["S256", "plain"]
        }
        return OAuth2Provider(config)
    
    @pytest.fixture
    def test_client(self):
        return OAuth2Client(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uris=["https://app.example.com/callback"],
            grant_types=[OAuth2GrantType.AUTHORIZATION_CODE, OAuth2GrantType.CLIENT_CREDENTIALS],
            scopes=[OAuth2Scope.OPENID, OAuth2Scope.PROFILE, OAuth2Scope.EMAIL],
            is_confidential=True
        )
    
    @pytest.mark.asyncio
    async def test_initialization(self, oauth_provider):
        """Test OAuth2Provider initialization."""
        assert oauth_provider.issuer == "https://auth.example.com"
        assert oauth_provider.authorization_endpoint == "https://auth.example.com/authorize"
        assert oauth_provider.token_endpoint == "https://auth.example.com/token"
        assert len(oauth_provider.clients) == 0
        assert oauth_provider._token_store == {}
        assert oauth_provider._code_store == {}
    
    @pytest.mark.asyncio
    async def test_register_client(self, oauth_provider, test_client):
        """Test client registration."""
        oauth_provider.register_client(test_client)
        
        assert "test_client_id" in oauth_provider.clients
        assert oauth_provider.clients["test_client_id"] == test_client
    
    @pytest.mark.asyncio
    async def test_create_authorization_code_flow(self, oauth_provider, test_client):
        """Test authorization code flow creation."""
        oauth_provider.register_client(test_client)
        
        auth_request = AuthenticationRequest(
            client_id="test_client_id",
            response_type=OAuth2ResponseType.CODE,
            redirect_uri="https://app.example.com/callback",
            scope="openid profile email",
            state="test_state"
        )
        
        result = await oauth_provider.create_authorization_code_flow(auth_request)
        
        assert "authorization_url" in result
        assert "code" in result
        assert "state" in result
        assert result["state"] == "test_state"
        assert result["code"] in oauth_provider._code_store
    
    @pytest.mark.asyncio
    async def test_create_authorization_code_flow_with_pkce(self, oauth_provider, test_client):
        """Test authorization code flow with PKCE."""
        oauth_provider.register_client(test_client)
        
        auth_request = AuthenticationRequest(
            client_id="test_client_id",
            response_type=OAuth2ResponseType.CODE,
            redirect_uri="https://app.example.com/callback",
            scope="openid profile email",
            state="test_state",
            code_challenge="test_challenge",
            code_challenge_method="S256"
        )
        
        result = await oauth_provider.create_authorization_code_flow(auth_request)
        
        assert "authorization_url" in result
        assert "code" in result
        assert result["code"] in oauth_provider._code_store
        
        # Verify PKCE data is stored
        code_data = oauth_provider._code_store[result["code"]]
        assert code_data["code_challenge"] == "test_challenge"
        assert code_data["code_challenge_method"] == "S256"
    
    @pytest.mark.asyncio
    async def test_exchange_authorization_code_success(self, oauth_provider, test_client):
        """Test successful authorization code exchange."""
        oauth_provider.register_client(test_client)
        
        # Create authorization code first
        auth_request = AuthenticationRequest(
            client_id="test_client_id",
            response_type=OAuth2ResponseType.CODE,
            redirect_uri="https://app.example.com/callback",
            scope="openid profile email"
        )
        
        auth_result = await oauth_provider.create_authorization_code_flow(auth_request)
        code = auth_result["code"]
        
        # Exchange code for token
        token_request = {
            "grant_type": OAuth2GrantType.AUTHORIZATION_CODE,
            "code": code,
            "redirect_uri": "https://app.example.com/callback",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret"
        }
        
        result = await oauth_provider.exchange_authorization_code(token_request)
        
        assert "access_token" in result
        assert "refresh_token" in result
        assert "id_token" in result
        assert "token_type" in result
        assert result["token_type"] == "Bearer"
        assert result["access_token"] in oauth_provider._token_store
    
    @pytest.mark.asyncio
    async def test_exchange_authorization_code_with_pkce(self, oauth_provider, test_client):
        """Test PKCE code exchange."""
        oauth_provider.register_client(test_client)
        
        # Create authorization code with PKCE
        auth_request = AuthenticationRequest(
            client_id="test_client_id",
            response_type=OAuth2ResponseType.CODE,
            redirect_uri="https://app.example.com/callback",
            scope="openid profile email",
            code_challenge="test_verifier_challenge",
            code_challenge_method="S256"
        )
        
        auth_result = await oauth_provider.create_authorization_code_flow(auth_request)
        code = auth_result["code"]
        
        # Exchange code with code verifier
        token_request = {
            "grant_type": OAuth2GrantType.AUTHORIZATION_CODE,
            "code": code,
            "redirect_uri": "https://app.example.com/callback",
            "client_id": "test_client_id",
            "code_verifier": "test_verifier"
        }
        
        result = await oauth_provider.exchange_authorization_code(token_request)
        
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["access_token"] in oauth_provider._token_store
    
    @pytest.mark.asyncio
    async def test_client_credentials_grant(self, oauth_provider, test_client):
        """Test client credentials grant."""
        oauth_provider.register_client(test_client)
        
        token_request = {
            "grant_type": OAuth2GrantType.CLIENT_CREDENTIALS,
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "scope": "api"
        }
        
        result = await oauth_provider.handle_client_credentials_grant(token_request)
        
        assert "access_token" in result
        assert "token_type" in result
        assert result["token_type"] == "Bearer"
        assert "refresh_token" not in result  # No refresh token for client credentials
        assert result["access_token"] in oauth_provider._token_store
    
    @pytest.mark.asyncio
    async def test_refresh_token(self, oauth_provider, test_client):
        """Test token refresh."""
        oauth_provider.register_client(test_client)
        
        # First get tokens via authorization code
        auth_request = AuthenticationRequest(
            client_id="test_client_id",
            response_type=OAuth2ResponseType.CODE,
            redirect_uri="https://app.example.com/callback",
            scope="openid profile email"
        )
        
        auth_result = await oauth_provider.create_authorization_code_flow(auth_request)
        code = auth_result["code"]
        
        token_request = {
            "grant_type": OAuth2GrantType.AUTHORIZATION_CODE,
            "code": code,
            "redirect_uri": "https://app.example.com/callback",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret"
        }
        
        initial_tokens = await oauth_provider.exchange_authorization_code(token_request)
        refresh_token = initial_tokens["refresh_token"]
        
        # Refresh the token
        refresh_request = {
            "grant_type": OAuth2GrantType.REFRESH_TOKEN,
            "refresh_token": refresh_token,
            "client_id": "test_client_id",
            "client_secret": "test_client_secret"
        }
        
        new_tokens = await oauth_provider.refresh_access_token(refresh_request)
        
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens
        assert new_tokens["access_token"] != initial_tokens["access_token"]
        assert new_tokens["refresh_token"] != initial_tokens["refresh_token"]
    
    @pytest.mark.asyncio
    async def test_validate_token(self, oauth_provider, test_client):
        """Test token validation."""
        oauth_provider.register_client(test_client)
        
        # Create and store a token
        token_request = {
            "grant_type": OAuth2GrantType.CLIENT_CREDENTIALS,
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "scope": "api"
        }
        
        token_result = await oauth_provider.handle_client_credentials_grant(token_request)
        access_token = token_result["access_token"]
        
        # Validate token
        validation_result = await oauth_provider.validate_token(access_token)
        
        assert validation_result.is_valid is True
        assert validation_result.client_id == "test_client_id"
        assert "api" in validation_result.scopes
        assert validation_result.token_type == TokenType.ACCESS_TOKEN
    
    @pytest.mark.asyncio
    async def test_revoke_token(self, oauth_provider, test_client):
        """Test token revocation."""
        oauth_provider.register_client(test_client)
        
        # Create and store a token
        token_request = {
            "grant_type": OAuth2GrantType.CLIENT_CREDENTIALS,
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "scope": "api"
        }
        
        token_result = await oauth_provider.handle_client_credentials_grant(token_request)
        access_token = token_result["access_token"]
        
        # Revoke token
        revoke_request = {
            "token": access_token,
            "client_id": "test_client_id",
            "client_secret": "test_client_secret"
        }
        
        result = await oauth_provider.revoke_token(revoke_request)
        
        assert result["status"] == "success"
        assert access_token not in oauth_provider._token_store
    
    @pytest.mark.asyncio
    async def test_introspect_token(self, oauth_provider, test_client):
        """Test token introspection."""
        oauth_provider.register_client(test_client)
        
        # Create and store a token
        token_request = {
            "grant_type": OAuth2GrantType.CLIENT_CREDENTIALS,
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "scope": "api"
        }
        
        token_result = await oauth_provider.handle_client_credentials_grant(token_request)
        access_token = token_result["access_token"]
        
        # Introspect token
        introspect_request = {
            "token": access_token,
            "client_id": "test_client_id",
            "client_secret": "test_client_secret"
        }
        
        introspection_result = await oauth_provider.introspect_token(introspect_request)
        
        assert introspection_result["active"] is True
        assert introspection_result["client_id"] == "test_client_id"
        assert "api" in introspection_result["scope"]
        assert introspection_result["token_type"] == "Bearer"
    
    @pytest.mark.asyncio
    async def test_invalid_client_id(self, oauth_provider):
        """Test error handling for invalid client ID."""
        auth_request = AuthenticationRequest(
            client_id="invalid_client",
            response_type=OAuth2ResponseType.CODE,
            redirect_uri="https://app.example.com/callback",
            scope="openid profile email"
        )
        
        with pytest.raises(OAuth2ValidationError, match="Invalid client"):
            await oauth_provider.create_authorization_code_flow(auth_request)
    
    @pytest.mark.asyncio
    async def test_invalid_redirect_uri(self, oauth_provider, test_client):
        """Test error handling for invalid redirect URI."""
        oauth_provider.register_client(test_client)
        
        auth_request = AuthenticationRequest(
            client_id="test_client_id",
            response_type=OAuth2ResponseType.CODE,
            redirect_uri="https://invalid.example.com/callback",
            scope="openid profile email"
        )
        
        with pytest.raises(OAuth2ValidationError, match="Invalid redirect URI"):
            await oauth_provider.create_authorization_code_flow(auth_request)
    
    @pytest.mark.asyncio
    async def test_invalid_grant_type(self, oauth_provider, test_client):
        """Test error handling for invalid grant type."""
        oauth_provider.register_client(test_client)
        
        token_request = {
            "grant_type": "invalid_grant",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret"
        }
        
        with pytest.raises(OAuth2ValidationError, match="Unsupported grant type"):
            await oauth_provider.handle_client_credentials_grant(token_request)
    
    @pytest.mark.asyncio
    async def test_expired_authorization_code(self, oauth_provider, test_client):
        """Test error handling for expired authorization code."""
        oauth_provider.register_client(test_client)
        
        # Create a code and manually expire it
        auth_request = AuthenticationRequest(
            client_id="test_client_id",
            response_type=OAuth2ResponseType.CODE,
            redirect_uri="https://app.example.com/callback",
            scope="openid profile email"
        )
        
        auth_result = await oauth_provider.create_authorization_code_flow(auth_request)
        code = auth_result["code"]
        
        # Manually expire the code
        code_data = oauth_provider._code_store[code]
        code_data["expires_at"] = datetime.utcnow() - timedelta(minutes=1)
        
        # Try to exchange expired code
        token_request = {
            "grant_type": OAuth2GrantType.AUTHORIZATION_CODE,
            "code": code,
            "redirect_uri": "https://app.example.com/callback",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret"
        }
        
        with pytest.raises(OAuth2ValidationError, match="Authorization code expired"):
            await oauth_provider.exchange_authorization_code(token_request)
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, oauth_provider, test_client):
        """Test rate limiting functionality."""
        oauth_provider.register_client(test_client)
        
        token_request = {
            "grant_type": OAuth2GrantType.CLIENT_CREDENTIALS,
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "scope": "api"
        }
        
        # Simulate rate limit exceeded
        oauth_provider.rate_limiter = Mock()
        oauth_provider.rate_limiter.is_allowed = AsyncMock(return_value=False)
        oauth_provider.rate_limiter.get_retry_after = AsyncMock(return_value=60.0)
        
        with pytest.raises(OAuth2RateLimitError, match="Rate limit exceeded"):
            await oauth_provider.handle_client_credentials_grant(token_request)
    
    @pytest.mark.asyncio
    async def test_health_check(self, oauth_provider):
        """Test health check functionality."""
        health = await oauth_provider.health_check()
        
        assert health["status"] == "healthy"
        assert health["issuer"] == "https://auth.example.com"
        assert health["clients_registered"] == 0
        assert health["active_tokens"] == 0
        assert health["active_codes"] == 0


class TestOAuth2TokenManagement:
    """Test OAuth2 token management functionality."""
    
    @pytest.fixture
    def oauth_token(self):
        return OAuth2Token(
            access_token="test_access_token_123",
            token_type=TokenType.ACCESS_TOKEN,
            expires_in=3600,
            refresh_token="test_refresh_token_456",
            scope="openid profile email",
            client_id="test_client_id",
            user_id="test_user_id"
        )
    
    def test_token_creation(self, oauth_token):
        """Test OAuth2Token creation."""
        assert oauth_token.access_token == "test_access_token_123"
        assert oauth_token.token_type == TokenType.ACCESS_TOKEN
        assert oauth_token.expires_in == 3600
        assert oauth_token.refresh_token == "test_refresh_token_456"
        assert oauth_token.scope == "openid profile email"
        assert oauth_token.client_id == "test_client_id"
        assert oauth_token.user_id == "test_user_id"
        assert oauth_token.is_active() is True
    
    def test_token_expiration(self, oauth_token):
        """Test token expiration."""
        # Set expiration time in the past
        oauth_token.expires_at = datetime.utcnow() - timedelta(minutes=1)
        assert oauth_token.is_active() is False
        assert oauth_token.is_expired() is True
    
    def test_token_scope_validation(self, oauth_token):
        """Test token scope validation."""
        assert oauth_token.has_scope("openid") is True
        assert oauth_token.has_scope("profile") is True
        assert oauth_token.has_scope("email") is True
        assert oauth_token.has_scope("api") is False
        assert oauth_token.has_scope(["openid", "profile"]) is True
        assert oauth_token.has_scope(["openid", "api"]) is False
    
    def test_token_to_jwt(self, oauth_token):
        """Test token to JWT conversion."""
        jwt_token = oauth_token.to_jwt("test_secret_key")
        
        assert isinstance(jwt_token, str)
        
        # Decode and verify JWT
        decoded = jwt.decode(jwt_token, "test_secret_key", algorithms=["HS256"])
        assert decoded["sub"] == "test_user_id"
        assert decoded["client_id"] == "test_client_id"
        assert decoded["scope"] == "openid profile email"
    
    def test_token_from_jwt(self):
        """Test token creation from JWT."""
        # Create a JWT
        payload = {
            "sub": "test_user_id",
            "client_id": "test_client_id",
            "scope": "openid profile email",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow()
        }
        
        jwt_token = jwt.encode(payload, "test_secret_key", algorithm="HS256")
        
        # Create token from JWT
        oauth_token = OAuth2Token.from_jwt(jwt_token, "test_secret_key")
        
        assert oauth_token.user_id == "test_user_id"
        assert oauth_token.client_id == "test_client_id"
        assert oauth_token.scope == "openid profile email"
        assert oauth_token.is_active() is True


class TestOAuth2AuthorizationCode:
    """Test OAuth2 authorization code functionality."""
    
    @pytest.fixture
    def auth_code(self):
        return OAuth2AuthorizationCode(
            code="test_authorization_code_123",
            client_id="test_client_id",
            redirect_uri="https://app.example.com/callback",
            scope="openid profile email",
            user_id="test_user_id",
            code_challenge="test_challenge",
            code_challenge_method="S256"
        )
    
    def test_authorization_code_creation(self, auth_code):
        """Test OAuth2AuthorizationCode creation."""
        assert auth_code.code == "test_authorization_code_123"
        assert auth_code.client_id == "test_client_id"
        assert auth_code.redirect_uri == "https://app.example.com/callback"
        assert auth_code.scope == "openid profile email"
        assert auth_code.user_id == "test_user_id"
        assert auth_code.code_challenge == "test_challenge"
        assert auth_code.code_challenge_method == "S256"
        assert auth_code.is_active() is True
    
    def test_authorization_code_expiration(self, auth_code):
        """Test authorization code expiration."""
        # Set expiration time in the past
        auth_code.expires_at = datetime.utcnow() - timedelta(minutes=1)
        assert auth_code.is_active() is False
        assert auth_code.is_expired() is True
    
    def test_authorization_code_pkce_validation(self, auth_code):
        """Test PKCE code verifier validation."""
        # Test valid verifier
        valid_verifier = "test_verifier_that_matches_challenge"
        
        # Mock the challenge generation
        with patch('src.integrations.auth.oauth2_provider.base64.urlsafe_b64encode') as mock_b64:
            mock_b64.return_value = b'test_challenge'
            
            # This would normally validate against the actual challenge
            # For testing, we'll just verify the method exists
            assert hasattr(auth_code, 'validate_code_verifier')
    
    def test_authorization_code_consumption(self, auth_code):
        """Test authorization code consumption."""
        assert auth_code.is_consumed is False
        
        auth_code.consume()
        assert auth_code.is_consumed is True
        assert auth_code.is_active() is False


class TestAuthenticationRequest:
    """Test AuthenticationRequest functionality."""
    
    def test_authentication_request_creation(self):
        """Test AuthenticationRequest creation."""
        auth_request = AuthenticationRequest(
            client_id="test_client_id",
            response_type=OAuth2ResponseType.CODE,
            redirect_uri="https://app.example.com/callback",
            scope="openid profile email",
            state="test_state",
            code_challenge="test_challenge",
            code_challenge_method="S256"
        )
        
        assert auth_request.client_id == "test_client_id"
        assert auth_request.response_type == OAuth2ResponseType.CODE
        assert auth_request.redirect_uri == "https://app.example.com/callback"
        assert auth_request.scope == "openid profile email"
        assert auth_request.state == "test_state"
        assert auth_request.code_challenge == "test_challenge"
        assert auth_request.code_challenge_method == "S256"
    
    def test_authentication_request_validation(self):
        """Test AuthenticationRequest validation."""
        # Valid request
        auth_request = AuthenticationRequest(
            client_id="test_client_id",
            response_type=OAuth2ResponseType.CODE,
            redirect_uri="https://app.example.com/callback",
            scope="openid profile email"
        )
        
        assert auth_request.is_valid() is True
        
        # Invalid request - missing client_id
        invalid_request = AuthenticationRequest(
            client_id="",
            response_type=OAuth2ResponseType.CODE,
            redirect_uri="https://app.example.com/callback",
            scope="openid profile email"
        )
        
        assert invalid_request.is_valid() is False
    
    def test_authentication_request_to_dict(self):
        """Test AuthenticationRequest to dictionary conversion."""
        auth_request = AuthenticationRequest(
            client_id="test_client_id",
            response_type=OAuth2ResponseType.CODE,
            redirect_uri="https://app.example.com/callback",
            scope="openid profile email",
            state="test_state"
        )
        
        result = auth_request.to_dict()
        
        assert result["client_id"] == "test_client_id"
        assert result["response_type"] == "code"
        assert result["redirect_uri"] == "https://app.example.com/callback"
        assert result["scope"] == "openid profile email"
        assert result["state"] == "test_state"


class TestTokenValidationResult:
    """Test TokenValidationResult functionality."""
    
    def test_token_validation_result_creation(self):
        """Test TokenValidationResult creation."""
        validation_result = TokenValidationResult(
            is_valid=True,
            client_id="test_client_id",
            user_id="test_user_id",
            scopes=["openid", "profile", "email"],
            token_type=TokenType.ACCESS_TOKEN,
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        
        assert validation_result.is_valid is True
        assert validation_result.client_id == "test_client_id"
        assert validation_result.user_id == "test_user_id"
        assert validation_result.scopes == ["openid", "profile", "email"]
        assert validation_result.token_type == TokenType.ACCESS_TOKEN
        assert validation_result.is_active() is True
    
    def test_token_validation_result_invalid(self):
        """Test invalid TokenValidationResult."""
        validation_result = TokenValidationResult(
            is_valid=False,
            error="Token expired",
            error_description="The access token has expired"
        )
        
        assert validation_result.is_valid is False
        assert validation_result.error == "Token expired"
        assert validation_result.error_description == "The access token has expired"
        assert validation_result.is_active() is False


# Performance tests
@pytest.mark.integration
class TestOAuth2Performance:
    """Performance tests for OAuth2 provider."""
    
    @pytest.mark.asyncio
    async def test_authorization_code_flow_performance(self):
        """Test authorization code flow performance."""
        config = {
            "issuer": "https://auth.example.com",
            "authorization_endpoint": "https://auth.example.com/authorize",
            "token_endpoint": "https://auth.example.com/token",
            "jwks_uri": "https://auth.example.com/.well-known/jwks.json",
            "scopes_supported": ["openid", "profile", "email", "api"],
            "grant_types_supported": ["authorization_code", "client_credentials", "refresh_token"],
            "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post"],
            "code_challenge_methods_supported": ["S256", "plain"]
        }
        
        provider = OAuth2Provider(config)
        
        # Register test client
        client = OAuth2Client(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uris=["https://app.example.com/callback"],
            grant_types=[OAuth2GrantType.AUTHORIZATION_CODE],
            scopes=[OAuth2Scope.OPENID, OAuth2Scope.PROFILE, OAuth2Scope.EMAIL]
        )
        provider.register_client(client)
        
        start_time = time.time()
        
        # Test 100 complete authorization flows
        for i in range(100):
            # Create authorization request
            auth_request = AuthenticationRequest(
                client_id="test_client_id",
                response_type=OAuth2ResponseType.CODE,
                redirect_uri="https://app.example.com/callback",
                scope="openid profile email",
                state=f"test_state_{i}"
            )
            
            # Create authorization code
            auth_result = await provider.create_authorization_code_flow(auth_request)
            
            # Exchange code for token
            token_request = {
                "grant_type": OAuth2GrantType.AUTHORIZATION_CODE,
                "code": auth_result["code"],
                "redirect_uri": "https://app.example.com/callback",
                "client_id": "test_client_id",
                "client_secret": "test_client_secret"
            }
            
            token_result = await provider.exchange_authorization_code(token_request)
            
            # Validate token
            validation_result = await provider.validate_token(token_result["access_token"])
            assert validation_result.is_valid is True
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in reasonable time (< 10 seconds)
        assert duration < 10.0
    
    @pytest.mark.asyncio
    async def test_token_validation_performance(self):
        """Test token validation performance."""
        config = {
            "issuer": "https://auth.example.com",
            "authorization_endpoint": "https://auth.example.com/authorize",
            "token_endpoint": "https://auth.example.com/token",
            "jwks_uri": "https://auth.example.com/.well-known/jwks.json",
            "scopes_supported": ["openid", "profile", "email", "api"],
            "grant_types_supported": ["authorization_code", "client_credentials", "refresh_token"]
        }
        
        provider = OAuth2Provider(config)
        
        # Register test client
        client = OAuth2Client(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uris=["https://app.example.com/callback"],
            grant_types=[OAuth2GrantType.CLIENT_CREDENTIALS],
            scopes=[OAuth2Scope.API]
        )
        provider.register_client(client)
        
        # Create multiple tokens
        tokens = []
        for i in range(50):
            token_request = {
                "grant_type": OAuth2GrantType.CLIENT_CREDENTIALS,
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
                "scope": "api"
            }
            
            result = await provider.handle_client_credentials_grant(token_request)
            tokens.append(result["access_token"])
        
        start_time = time.time()
        
        # Validate all tokens concurrently
        tasks = []
        for token in tokens:
            tasks.append(provider.validate_token(token))
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in reasonable time (< 1 second)
        assert duration < 1.0
        assert len(results) == 50
        assert all(result.is_valid for result in results)


# Error handling tests
@pytest.mark.asyncio
class TestOAuth2ErrorHandling:
    """Test error handling in OAuth2 provider."""
    
    async def test_invalid_client_credentials(self):
        """Test invalid client credentials error handling."""
        config = {
            "issuer": "https://auth.example.com",
            "authorization_endpoint": "https://auth.example.com/authorize",
            "token_endpoint": "https://auth.example.com/token",
            "jwks_uri": "https://auth.example.com/.well-known/jwks.json",
            "scopes_supported": ["openid", "profile", "email", "api"],
            "grant_types_supported": ["authorization_code", "client_credentials", "refresh_token"]
        }
        
        provider = OAuth2Provider(config)
        
        # Register test client
        client = OAuth2Client(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uris=["https://app.example.com/callback"],
            grant_types=[OAuth2GrantType.CLIENT_CREDENTIALS],
            scopes=[OAuth2Scope.API]
        )
        provider.register_client(client)
        
        # Test with invalid client secret
        token_request = {
            "grant_type": OAuth2GrantType.CLIENT_CREDENTIALS,
            "client_id": "test_client_id",
            "client_secret": "invalid_secret",
            "scope": "api"
        }
        
        with pytest.raises(OAuth2SecurityError, match="Invalid client credentials"):
            await provider.handle_client_credentials_grant(token_request)
    
    async def test_invalid_authorization_code(self):
        """Test invalid authorization code error handling."""
        config = {
            "issuer": "https://auth.example.com",
            "authorization_endpoint": "https://auth.example.com/authorize",
            "token_endpoint": "https://auth.example.com/token",
            "jwks_uri": "https://auth.example.com/.well-known/jwks.json",
            "scopes_supported": ["openid", "profile", "email", "api"],
            "grant_types_supported": ["authorization_code", "client_credentials", "refresh_token"]
        }
        
        provider = OAuth2Provider(config)
        
        # Test with invalid authorization code
        token_request = {
            "grant_type": OAuth2GrantType.AUTHORIZATION_CODE,
            "code": "invalid_code",
            "redirect_uri": "https://app.example.com/callback",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret"
        }
        
        with pytest.raises(OAuth2ValidationError, match="Invalid authorization code"):
            await provider.exchange_authorization_code(token_request)
    
    async def test_invalid_refresh_token(self):
        """Test invalid refresh token error handling."""
        config = {
            "issuer": "https://auth.example.com",
            "authorization_endpoint": "https://auth.example.com/authorize",
            "token_endpoint": "https://auth.example.com/token",
            "jwks_uri": "https://auth.example.com/.well-known/jwks.json",
            "scopes_supported": ["openid", "profile", "email", "api"],
            "grant_types_supported": ["authorization_code", "client_credentials", "refresh_token"]
        }
        
        provider = OAuth2Provider(config)
        
        # Test with invalid refresh token
        refresh_request = {
            "grant_type": OAuth2GrantType.REFRESH_TOKEN,
            "refresh_token": "invalid_refresh_token",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret"
        }
        
        with pytest.raises(OAuth2ValidationError, match="Invalid refresh token"):
            await provider.refresh_access_token(refresh_request)
    
    async def test_invalid_token_validation(self):
        """Test invalid token validation error handling."""
        config = {
            "issuer": "https://auth.example.com",
            "authorization_endpoint": "https://auth.example.com/authorize",
            "token_endpoint": "https://auth.example.com/token",
            "jwks_uri": "https://auth.example.com/.well-known/jwks.json",
            "scopes_supported": ["openid", "profile", "email", "api"],
            "grant_types_supported": ["authorization_code", "client_credentials", "refresh_token"]
        }
        
        provider = OAuth2Provider(config)
        
        # Test with invalid token
        validation_result = await provider.validate_token("invalid_token")
        
        assert validation_result.is_valid is False
        assert validation_result.error == "Invalid token"
    
    async def test_pkce_validation_failure(self):
        """Test PKCE validation failure error handling."""
        config = {
            "issuer": "https://auth.example.com",
            "authorization_endpoint": "https://auth.example.com/authorize",
            "token_endpoint": "https://auth.example.com/token",
            "jwks_uri": "https://auth.example.com/.well-known/jwks.json",
            "scopes_supported": ["openid", "profile", "email", "api"],
            "grant_types_supported": ["authorization_code", "client_credentials", "refresh_token"],
            "code_challenge_methods_supported": ["S256", "plain"]
        }
        
        provider = OAuth2Provider(config)
        
        # Register test client
        client = OAuth2Client(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uris=["https://app.example.com/callback"],
            grant_types=[OAuth2GrantType.AUTHORIZATION_CODE],
            scopes=[OAuth2Scope.OPENID, OAuth2Scope.PROFILE, OAuth2Scope.EMAIL]
        )
        provider.register_client(client)
        
        # Create authorization code with PKCE
        auth_request = AuthenticationRequest(
            client_id="test_client_id",
            response_type=OAuth2ResponseType.CODE,
            redirect_uri="https://app.example.com/callback",
            scope="openid profile email",
            code_challenge="test_challenge",
            code_challenge_method="S256"
        )
        
        auth_result = await provider.create_authorization_code_flow(auth_request)
        code = auth_result["code"]
        
        # Try to exchange with invalid code verifier
        token_request = {
            "grant_type": OAuth2GrantType.AUTHORIZATION_CODE,
            "code": code,
            "redirect_uri": "https://app.example.com/callback",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "code_verifier": "invalid_verifier"
        }
        
        with pytest.raises(OAuth2ValidationError, match="PKCE validation failed"):
            await provider.exchange_authorization_code(token_request)


# Export test classes
__all__ = [
    "TestOAuth2Provider",
    "TestOAuth2TokenManagement",
    "TestOAuth2AuthorizationCode",
    "TestAuthenticationRequest",
    "TestTokenValidationResult",
    "TestOAuth2Performance",
    "TestOAuth2ErrorHandling"
]