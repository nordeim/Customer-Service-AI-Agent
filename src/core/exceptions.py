from __future__ import annotations

class AppError(Exception):
    """Base application error."""

    def __init__(self, message: str, *, code: str | None = None):
        super().__init__(message)
        self.code = code or self.__class__.__name__


# Configuration & Security
class ConfigurationError(AppError):
    """Raised when configuration is invalid or missing."""


class AuthenticationError(AppError):
    """Raised for authentication failures."""


class AuthorizationError(AppError):
    """Raised for authorization/permission failures."""


class SecurityError(AppError):
    """Raised for security-related failures (e.g., crypto)."""


# Domain Errors
class ConversationError(AppError):
    """Conversation lifecycle failures."""


class AIProcessingError(AppError):
    """AI pipeline processing failures."""


class AIServiceError(AppError):
    """AI service failures (e.g., model errors, API failures)."""


class IntegrationError(AppError):
    """Third-party integration error (e.g., Salesforce)."""


# Data & Infrastructure
class RepositoryError(AppError):
    """Repository/data access layer error."""


class ValidationError(AppError):
    """Input validation error."""


class RateLimitError(AppError):
    """Rate limit exceeded."""


class IntentHandlingError(AppError):
    """Intent processing and handling failures."""
