# 🚀 Comprehensive Coding Execution Plan for AI Customer Service Agent

## Executive Summary

This document provides an exhaustive, phase-by-phase execution plan for building the complete AI Customer Service Agent codebase. Each phase is meticulously designed for independent execution by AI coding agents, with unambiguous specifications, precise interfaces, and comprehensive validation criteria.

---

## 🎯 Strategic Execution Framework

### Core Principles
1. **True Phase Independence**: Each phase produces complete, testable functionality
2. **Contract-First Design**: All interfaces defined before implementation
3. **Zero Ambiguity**: Every file has exact specifications and examples
4. **Incremental Value**: Each phase delivers working features
5. **Quality Gates**: Measurable validation at every checkpoint
6. **Parallel Execution**: Multiple phases can run simultaneously

### Technical Standards
- **Python**: 3.11.6+ with full type hints and async/await
- **TypeScript**: 5.3+ with strict mode enabled
- **Testing**: Minimum 85% coverage with TDD approach
- **Documentation**: Every public API fully documented
- **Security**: OWASP compliance at every layer

---

## 📊 Master Phase Matrix

| Phase | Name | Duration | True Dependencies | Parallel Compatible | Priority |
|-------|------|----------|-------------------|---------------------|----------|
| 1 | Core Infrastructure | 4 days | None | - | CRITICAL |
| 2 | Database Layer | 5 days | None | 3,4,5 | CRITICAL |
| 3 | API Framework | 5 days | None | 2,4,5 | CRITICAL |
| 4 | Business Logic | 6 days | None | 2,3,5 | HIGH |
| 5 | AI/ML Services | 7 days | None | 2,3,4 | HIGH |
| 6 | Conversation Engine | 6 days | 1 only | 7,8 | HIGH |
| 7 | Integration Layer | 5 days | 1 only | 6,8 | MEDIUM |
| 8 | Frontend Application | 7 days | 1 only | 6,7 | MEDIUM |
| 9 | Testing Suite | 4 days | All | - | CRITICAL |
| 10 | DevOps & Deployment | 4 days | 1 only | - | CRITICAL |

---

## 📁 PHASE 1: Core Infrastructure Foundation

### Overview
Establish the foundational infrastructure that all other components will use. This phase creates the core utilities, configuration management, logging, security, and error handling systems.

### Step 1.1: Project Initialization

#### Files to Create:

##### 1.1.1 - pyproject.toml
```toml
# Purpose: Python project configuration with all dependencies
# Location: /pyproject.toml
# Dependencies: None
# Interface: Standard Python packaging

[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "ai-customer-service-agent"
version = "1.0.0"
description = "Enterprise AI-powered customer service agent"
readme = "README.md"
requires-python = ">=3.11"
license = {text = "MIT"}
authors = [{name = "AI Agent Team", email = "team@aiagent.com"}]

dependencies = [
    "fastapi==0.104.1",
    "uvicorn[standard]==0.24.0",
    "pydantic==2.5.0",
    "pydantic-settings==2.1.0",
    "sqlalchemy==2.0.23",
    "asyncpg==0.29.0",
    "alembic==1.12.1",
    "redis==5.0.1",
    "httpx==0.25.2",
    "python-jose[cryptography]==3.3.0",
    "passlib[bcrypt]==1.7.4",
    "python-multipart==0.0.6",
    "email-validator==2.1.0",
    "python-dotenv==1.0.0",
    "openai==1.3.7",
    "anthropic==0.7.7",
    "transformers==4.36.0",
    "torch==2.1.1",
    "numpy==1.24.3",
    "pandas==2.1.3",
    "scikit-learn==1.3.2",
    "spacy==3.7.2",
    "langchain==0.0.340",
    "pinecone-client==2.2.4",
    "boto3==1.33.7",
    "celery==5.3.4",
    "flower==2.0.1",
    "prometheus-client==0.19.0",
    "opentelemetry-api==1.21.0",
    "opentelemetry-sdk==1.21.0",
    "loguru==0.7.2",
    "python-json-logger==2.0.7",
]

[project.optional-dependencies]
dev = [
    "pytest==7.4.3",
    "pytest-asyncio==0.21.1",
    "pytest-cov==4.1.0",
    "pytest-mock==3.12.0",
    "black==23.11.0",
    "isort==5.12.0",
    "flake8==6.1.0",
    "mypy==1.7.1",
    "bandit==1.7.5",
    "pre-commit==3.5.0",
    "ipython==8.17.2",
    "rich==13.7.0",
]

[tool.black]
line-length = 100
target-version = ['py311']

[tool.isort]
profile = "black"
line_length = 100

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

##### 1.1.2 - Makefile
```makefile
# Purpose: Build automation and task management
# Location: /Makefile
# Dependencies: Unix-like system
# Interface: Make commands

.PHONY: help install install-dev test test-cov lint format security run build clean

help:
	@echo "Available commands:"
	@echo "  make install      Install production dependencies"
	@echo "  make install-dev  Install development dependencies"
	@echo "  make test         Run tests"
	@echo "  make test-cov     Run tests with coverage"
	@echo "  make lint         Run linters"
	@echo "  make format       Format code"
	@echo "  make security     Run security checks"
	@echo "  make run          Run application"
	@echo "  make build        Build Docker image"
	@echo "  make clean        Clean cache and build files"

install:
	pip install --upgrade pip
	pip install -e .

install-dev:
	pip install --upgrade pip
	pip install -e ".[dev]"
	pre-commit install

test:
	pytest tests/ -v

test-cov:
	pytest tests/ --cov=src --cov-report=term-missing --cov-report=html

lint:
	black --check src/ tests/
	isort --check-only src/ tests/
	flake8 src/ tests/
	mypy src/

format:
	black src/ tests/
	isort src/ tests/

security:
	bandit -r src/
	safety check

run:
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

build:
	docker build -t ai-agent:latest .

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .coverage htmlcov .pytest_cache .mypy_cache
```

#### Validation Checklist for Step 1.1:
- [ ] pyproject.toml has all required dependencies with exact versions
- [ ] Makefile commands execute without errors
- [ ] Python version 3.11+ is enforced
- [ ] All development tools are configured
- [ ] License is properly specified
- [ ] Project metadata is complete

### Step 1.2: Core Configuration Module

#### Files to Create:

##### 1.2.1 - src/core/config.py
```python
# Purpose: Centralized configuration management with validation
# Location: /src/core/config.py
# Dependencies: pydantic, python-dotenv
# Interface: Settings class with all app configuration

from typing import Optional, List, Dict, Any
from functools import lru_cache
from enum import Enum
from pydantic import BaseSettings, Field, validator, PostgresDsn, RedisDsn, HttpUrl
from pydantic.types import SecretStr
import os
from pathlib import Path

class Environment(str, Enum):
    """Application environment types"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"

class LogLevel(str, Enum):
    """Logging level options"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class Settings(BaseSettings):
    """
    Application settings with validation and type checking.
    All settings can be overridden via environment variables.
    """
    
    # Application
    app_name: str = Field(default="AI Customer Service Agent", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    environment: Environment = Field(default=Environment.DEVELOPMENT, description="Environment")
    debug: bool = Field(default=False, description="Debug mode")
    
    # API Configuration
    api_v1_prefix: str = Field(default="/api/v1", description="API v1 prefix")
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port", ge=1, le=65535)
    api_workers: int = Field(default=4, description="Number of API workers", ge=1)
    
    # Security
    secret_key: SecretStr = Field(..., description="Secret key for JWT encoding")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration_minutes: int = Field(default=30, description="JWT expiration in minutes")
    jwt_refresh_expiration_days: int = Field(default=7, description="Refresh token expiration")
    
    # Database
    postgres_host: str = Field(..., description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_user: str = Field(..., description="PostgreSQL user")
    postgres_password: SecretStr = Field(..., description="PostgreSQL password")
    postgres_db: str = Field(..., description="PostgreSQL database name")
    postgres_echo: bool = Field(default=False, description="Echo SQL statements")
    postgres_pool_size: int = Field(default=20, description="Connection pool size")
    postgres_max_overflow: int = Field(default=40, description="Max overflow connections")
    
    # Redis
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_password: Optional[SecretStr] = Field(default=None, description="Redis password")
    redis_db: int = Field(default=0, description="Redis database number")
    redis_decode_responses: bool = Field(default=True, description="Decode Redis responses")
    
    # AI/ML Configuration
    openai_api_key: SecretStr = Field(..., description="OpenAI API key")
    openai_model: str = Field(default="gpt-4-turbo-preview", description="OpenAI model")
    openai_temperature: float = Field(default=0.7, description="Temperature", ge=0, le=2)
    openai_max_tokens: int = Field(default=2000, description="Max tokens", ge=1)
    
    anthropic_api_key: Optional[SecretStr] = Field(default=None, description="Anthropic API key")
    anthropic_model: str = Field(default="claude-3-sonnet-20240229", description="Claude model")
    
    # Pinecone Vector DB
    pinecone_api_key: Optional[SecretStr] = Field(default=None, description="Pinecone API key")
    pinecone_environment: Optional[str] = Field(default=None, description="Pinecone environment")
    pinecone_index_name: str = Field(default="knowledge-base", description="Pinecone index")
    
    # Salesforce Integration
    salesforce_username: Optional[str] = Field(default=None, description="Salesforce username")
    salesforce_password: Optional[SecretStr] = Field(default=None, description="SF password")
    salesforce_security_token: Optional[SecretStr] = Field(default=None, description="SF token")
    salesforce_domain: str = Field(default="login", description="Salesforce domain")
    
    # Logging
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Logging level")
    log_format: str = Field(default="json", description="Log format (json or text)")
    log_file: Optional[Path] = Field(default=None, description="Log file path")
    
    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins"
    )
    cors_allow_credentials: bool = Field(default=True, description="Allow credentials")
    cors_allow_methods: List[str] = Field(default=["*"], description="Allowed methods")
    cors_allow_headers: List[str] = Field(default=["*"], description="Allowed headers")
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests: int = Field(default=100, description="Requests per window")
    rate_limit_window: int = Field(default=60, description="Time window in seconds")
    
    # WebSocket
    ws_heartbeat_interval: int = Field(default=30, description="WebSocket heartbeat interval")
    ws_connection_timeout: int = Field(default=60, description="WebSocket connection timeout")
    
    # Performance
    request_timeout: int = Field(default=30, description="Request timeout in seconds")
    cache_ttl: int = Field(default=300, description="Default cache TTL in seconds")
    max_connections_per_client: int = Field(default=10, description="Max connections per client")
    
    @property
    def database_url(self) -> str:
        """Construct PostgreSQL connection URL"""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:"
            f"{self.postgres_password.get_secret_value()}@"
            f"{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
    
    @property
    def redis_url(self) -> str:
        """Construct Redis connection URL"""
        if self.redis_password:
            return (
                f"redis://:{self.redis_password.get_secret_value()}@"
                f"{self.redis_host}:{self.redis_port}/{self.redis_db}"
            )
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    @validator("environment", pre=True)
    def validate_environment(cls, v: str) -> str:
        """Validate and normalize environment"""
        if isinstance(v, str):
            v = v.lower()
        return v
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v: Any) -> List[str]:
        """Parse CORS origins from string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    class Config:
        """Pydantic configuration"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
        # Allow extra fields for forward compatibility
        extra = "allow"

@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses LRU cache to ensure single instance.
    
    Returns:
        Settings: Application settings
    """
    return Settings()

# Create global settings instance
settings = get_settings()
```

##### 1.2.2 - src/core/constants.py
```python
# Purpose: Application-wide constants and enums
# Location: /src/core/constants.py
# Dependencies: enum, typing
# Interface: Constants and Enums for use throughout application

from enum import Enum, IntEnum
from typing import Final

# API Version
API_VERSION: Final[str] = "1.0.0"
API_TITLE: Final[str] = "AI Customer Service Agent API"
API_DESCRIPTION: Final[str] = "Enterprise-grade AI-powered customer service platform"

# Request/Response
DEFAULT_PAGE_SIZE: Final[int] = 20
MAX_PAGE_SIZE: Final[int] = 100
REQUEST_ID_HEADER: Final[str] = "X-Request-ID"
API_KEY_HEADER: Final[str] = "X-API-Key"

# Timeouts (seconds)
DEFAULT_TIMEOUT: Final[int] = 30
DATABASE_TIMEOUT: Final[int] = 10
REDIS_TIMEOUT: Final[int] = 5
AI_MODEL_TIMEOUT: Final[int] = 60
EXTERNAL_API_TIMEOUT: Final[int] = 30

# Retry Configuration
MAX_RETRIES: Final[int] = 3
RETRY_DELAY: Final[int] = 1
RETRY_MULTIPLIER: Final[float] = 2.0
MAX_RETRY_DELAY: Final[int] = 60

# Cache Keys
CACHE_PREFIX: Final[str] = "acs:"  # AI Customer Service
USER_CACHE_PREFIX: Final[str] = f"{CACHE_PREFIX}user:"
CONVERSATION_CACHE_PREFIX: Final[str] = f"{CACHE_PREFIX}conv:"
SESSION_CACHE_PREFIX: Final[str] = f"{CACHE_PREFIX}session:"

# Content Limits
MAX_MESSAGE_LENGTH: Final[int] = 5000
MAX_ATTACHMENT_SIZE: Final[int] = 10 * 1024 * 1024  # 10MB
MAX_ATTACHMENTS_PER_MESSAGE: Final[int] = 5
MAX_CONVERSATION_MESSAGES: Final[int] = 1000

# AI Model Limits
MAX_TOKENS_PER_REQUEST: Final[int] = 4096
MAX_CONTEXT_MESSAGES: Final[int] = 50
EMBEDDING_DIMENSION: Final[int] = 1536

# Business Rules
ESCALATION_CONFIDENCE_THRESHOLD: Final[float] = 0.3
SENTIMENT_NEGATIVE_THRESHOLD: Final[float] = -0.5
INACTIVE_CONVERSATION_HOURS: Final[int] = 24
MAX_ESCALATION_ATTEMPTS: Final[int] = 3

class UserRole(str, Enum):
    """User role definitions"""
    ADMIN = "admin"
    AGENT = "agent"
    SUPERVISOR = "supervisor"
    CUSTOMER = "customer"
    SYSTEM = "system"

class ConversationStatus(str, Enum):
    """Conversation status states"""
    INITIALIZED = "initialized"
    ACTIVE = "active"
    WAITING_FOR_USER = "waiting_for_user"
    WAITING_FOR_AGENT = "waiting_for_agent"
    PROCESSING = "processing"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    ABANDONED = "abandoned"
    ARCHIVED = "archived"

class MessageSenderType(str, Enum):
    """Message sender types"""
    USER = "user"
    AI_AGENT = "ai_agent"
    HUMAN_AGENT = "human_agent"
    SYSTEM = "system"

class ConversationChannel(str, Enum):
    """Supported conversation channels"""
    WEB = "web"
    MOBILE = "mobile"
    EMAIL = "email"
    SLACK = "slack"
    TEAMS = "teams"
    API = "api"

class Priority(IntEnum):
    """Priority levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5

class ErrorCode(str, Enum):
    """Application error codes"""
    # Authentication/Authorization (1xxx)
    UNAUTHORIZED = "1001"
    FORBIDDEN = "1002"
    TOKEN_EXPIRED = "1003"
    INVALID_CREDENTIALS = "1004"
    
    # Validation (2xxx)
    VALIDATION_ERROR = "2001"
    INVALID_INPUT = "2002"
    MISSING_REQUIRED_FIELD = "2003"
    
    # Business Logic (3xxx)
    CONVERSATION_NOT_FOUND = "3001"
    USER_NOT_FOUND = "3002"
    ORGANIZATION_LIMIT_EXCEEDED = "3003"
    
    # External Services (4xxx)
    AI_SERVICE_ERROR = "4001"
    DATABASE_ERROR = "4002"
    CACHE_ERROR = "4003"
    EXTERNAL_API_ERROR = "4004"
    
    # System (5xxx)
    INTERNAL_ERROR = "5001"
    SERVICE_UNAVAILABLE = "5002"
    TIMEOUT_ERROR = "5003"

class WebSocketEvent(str, Enum):
    """WebSocket event types"""
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    MESSAGE = "message"
    TYPING = "typing"
    PRESENCE = "presence"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
```

##### 1.2.3 - src/core/exceptions.py
```python
# Purpose: Custom exception hierarchy for proper error handling
# Location: /src/core/exceptions.py
# Dependencies: typing
# Interface: Exception classes for different error scenarios

from typing import Optional, Dict, Any
from src.core.constants import ErrorCode

class BaseError(Exception):
    """
    Base exception class for all application errors.
    
    Attributes:
        message: Human-readable error message
        error_code: Machine-readable error code
        details: Additional error details
        status_code: HTTP status code
    """
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.status_code = status_code
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API response"""
        return {
            "error": {
                "code": self.error_code.value,
                "message": self.message,
                "details": self.details
            }
        }

class ValidationError(BaseError):
    """Raised when input validation fails"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            details=details,
            status_code=400
        )

class AuthenticationError(BaseError):
    """Raised when authentication fails"""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            error_code=ErrorCode.UNAUTHORIZED,
            status_code=401
        )

class AuthorizationError(BaseError):
    """Raised when user lacks required permissions"""
    
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message,
            error_code=ErrorCode.FORBIDDEN,
            status_code=403
        )

class NotFoundError(BaseError):
    """Raised when requested resource is not found"""
    
    def __init__(self, resource: str, identifier: Any):
        super().__init__(
            message=f"{resource} not found: {identifier}",
            error_code=ErrorCode.CONVERSATION_NOT_FOUND,
            details={"resource": resource, "identifier": str(identifier)},
            status_code=404
        )

class ConflictError(BaseError):
    """Raised when operation conflicts with current state"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            details=details,
            status_code=409
        )

class RateLimitError(BaseError):
    """Raised when rate limit is exceeded"""
    
    def __init__(self, limit: int, window: int):
        super().__init__(
            message=f"Rate limit exceeded: {limit} requests per {window} seconds",
            error_code=ErrorCode.VALIDATION_ERROR,
            details={"limit": limit, "window": window},
            status_code=429
        )

class DatabaseError(BaseError):
    """Raised when database operation fails"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Database error: {message}",
            error_code=ErrorCode.DATABASE_ERROR,
            details=details,
            status_code=500
        )

class ExternalServiceError(BaseError):
    """Raised when external service call fails"""
    
    def __init__(self, service: str, message: str):
        super().__init__(
            message=f"External service error ({service}): {message}",
            error_code=ErrorCode.EXTERNAL_API_ERROR,
            details={"service": service},
            status_code=502
        )

class AIServiceError(BaseError):
    """Raised when AI service operations fail"""
    
    def __init__(self, message: str, model: Optional[str] = None):
        super().__init__(
            message=f"AI service error: {message}",
            error_code=ErrorCode.AI_SERVICE_ERROR,
            details={"model": model} if model else {},
            status_code=503
        )

class ConfigurationError(BaseError):
    """Raised when configuration is invalid"""
    
    def __init__(self, message: str):
        super().__init__(
            message=f"Configuration error: {message}",
            error_code=ErrorCode.INTERNAL_ERROR,
            status_code=500
        )

class TimeoutError(BaseError):
    """Raised when operation times out"""
    
    def __init__(self, operation: str, timeout: int):
        super().__init__(
            message=f"Operation timed out: {operation} ({timeout}s)",
            error_code=ErrorCode.TIMEOUT_ERROR,
            details={"operation": operation, "timeout": timeout},
            status_code=504
        )
```

#### Validation Checklist for Step 1.2:
- [ ] Settings class loads from environment variables
- [ ] All configuration parameters have defaults and validation
- [ ] Database and Redis URLs are correctly constructed
- [ ] Constants cover all business requirements
- [ ] Exception hierarchy is complete and logical
- [ ] Error codes are unique and documented
- [ ] All exceptions have proper status codes
- [ ] Settings singleton pattern implemented

### Step 1.3: Logging Infrastructure

#### Files to Create:

##### 1.3.1 - src/core/logging.py
```python
# Purpose: Structured logging configuration with correlation IDs
# Location: /src/core/logging.py
# Dependencies: loguru, python-json-logger
# Interface: Logging setup and logger factory

import sys
import logging
from typing import Optional, Dict, Any
from pathlib import Path
import json
from datetime import datetime
from contextvars import ContextVar
from functools import wraps
import traceback

from loguru import logger
from pythonjsonlogger import jsonlogger
from src.core.config import get_settings

# Context variable for request ID
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)

class CorrelationIdFilter(logging.Filter):
    """Add correlation ID to log records"""
    
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = request_id_var.get() or "system"
        return True

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields"""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp
        log_record["timestamp"] = datetime.utcnow().isoformat()
        
        # Add level
        log_record["level"] = record.levelname
        
        # Add location
        log_record["location"] = f"{record.pathname}:{record.lineno}"
        
        # Add correlation ID
        log_record["correlation_id"] = getattr(record, "correlation_id", "system")
        
        # Add exception info if present
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

def setup_logging() -> None:
    """
    Configure application logging.
    Sets up both loguru and standard logging.
    """
    settings = get_settings()
    
    # Remove default loguru handler
    logger.remove()
    
    # Configure log format based on environment
    if settings.log_format == "json":
        # JSON format for production
        log_format = {
            "timestamp": "{time:YYYY-MM-DD HH:mm:ss.SSS}",
            "level": "{level}",
            "correlation_id": "{extra[correlation_id]}",
            "location": "{file}:{line}",
            "function": "{function}",
            "message": "{message}"
        }
        
        # Add JSON sink
        logger.add(
            sys.stdout,
            format=lambda record: json.dumps({
                **log_format,
                **{k: str(v) for k, v in record["extra"].items()}
            }) + "\n",
            level=settings.log_level.value,
            serialize=False
        )
    else:
        # Human-readable format for development
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{extra[correlation_id]}</cyan> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
        
        logger.add(
            sys.stdout,
            format=log_format,
            level=settings.log_level.value,
            colorize=True
        )
    
    # Add file handler if configured
    if settings.log_file:
        logger.add(
            settings.log_file,
            format=log_format if settings.log_format != "json" else None,
            level=settings.log_level.value,
            rotation="100 MB",
            retention="30 days",
            compression="zip",
            serialize=settings.log_format == "json"
        )
    
    # Configure standard logging for third-party libraries
    logging.basicConfig(level=logging.INFO)
    
    # Add correlation ID filter
    for handler in logging.root.handlers:
        handler.addFilter(CorrelationIdFilter())
        
        if settings.log_format == "json":
            formatter = CustomJsonFormatter(
                "%(timestamp)s %(level)s %(correlation_id)s %(name)s %(message)s"
            )
            handler.setFormatter(formatter)
    
    # Set third-party library log levels
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    logger.info("Logging configured", extra={"correlation_id": "system"})

def get_logger(name: str) -> "LoggerAdapter":
    """
    Get a logger instance with correlation ID support.
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Logger instance with correlation ID support
    """
    return LoggerAdapter(name)

class LoggerAdapter:
    """Logger adapter that adds correlation ID to all logs"""
    
    def __init__(self, name: str):
        self.name = name
        self._logger = logger.bind(logger_name=name)
    
    def _log(self, level: str, message: str, *args, **kwargs):
        """Internal log method with correlation ID"""
        correlation_id = request_id_var.get() or "system"
        extra = kwargs.pop("extra", {})
        extra["correlation_id"] = correlation_id
        
        # Format message with args if provided
        if args:
            message = message.format(*args)
        
        getattr(self._logger.opt(depth=2), level)(message, extra=extra, **kwargs)
    
    def debug(self, message: str, *args, **kwargs):
        """Log debug message"""
        self._log("debug", message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        """Log info message"""
        self._log("info", message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        """Log warning message"""
        self._log("warning", message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        """Log error message"""
        self._log("error", message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        """Log critical message"""
        self._log("critical", message, *args, **kwargs)
    
    def exception(self, message: str, *args, **kwargs):
        """Log exception with traceback"""
        exc_info = sys.exc_info()
        if exc_info[0] is not None:
            kwargs["exc_info"] = exc_info
        self._log("error", message, *args, **kwargs)

def log_execution_time(func):
    """Decorator to log function execution time"""
    
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        logger_instance = get_logger(func.__module__)
        start_time = datetime.utcnow()
        
        try:
            result = await func(*args, **kwargs)
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger_instance.debug(
                f"Function {func.__name__} executed in {execution_time:.3f}s",
                extra={"execution_time": execution_time}
            )
            return result
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger_instance.error(
                f"Function {func.__name__} failed after {execution_time:.3f}s: {str(e)}",
                extra={"execution_time": execution_time, "error": str(e)}
            )
            raise
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        logger_instance = get_logger(func.__module__)
        start_time = datetime.utcnow()
        
        try:
            result = func(*args, **kwargs)
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger_instance.debug(
                f"Function {func.__name__} executed in {execution_time:.3f}s",
                extra={"execution_time": execution_time}
            )
            return result
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger_instance.error(
                f"Function {func.__name__} failed after {execution_time:.3f}s: {str(e)}",
                extra={"execution_time": execution_time, "error": str(e)}
            )
            raise
    
    # Return appropriate wrapper based on function type
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper
```

#### Validation Checklist for Step 1.3:
- [ ] Structured JSON logging configured
- [ ] Correlation ID tracking implemented
- [ ] Log levels properly configured
- [ ] File rotation and retention set up
- [ ] Third-party library logging controlled
- [ ] Execution time decorator working
- [ ] Exception logging with full traceback
- [ ] Development and production formats differentiated

### Step 1.4: Security Utilities

#### Files to Create:

##### 1.4.1 - src/core/security.py
```python
# Purpose: Security utilities for authentication and encryption
# Location: /src/core/security.py
# Dependencies: passlib, python-jose, cryptography
# Interface: Security functions for password hashing, JWT, encryption

from typing import Optional, Dict, Any, Union
from datetime import datetime, timedelta
import secrets
import hashlib
import hmac
from jose import jwt, JWTError
from passlib.context import CryptContext
from cryptography.fernet import Fernet
from src.core.config import get_settings
from src.core.exceptions import AuthenticationError, ValidationError

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Settings
settings = get_settings()

class PasswordValidator:
    """Password strength validator"""
    
    @staticmethod
    def validate(password: str) -> tuple[bool, Optional[str]]:
        """
        Validate password strength.
        
        Args:
            password: Password to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"
        
        if not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter"
        
        if not any(c.isdigit() for c in password):
            return False, "Password must contain at least one number"
        
        return True, None

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password
        
    Raises:
        ValidationError: If password is invalid
    """
    # Validate password strength
    is_valid, error_message = PasswordValidator.validate(password)
    if not is_valid:
        raise ValidationError(error_message)
    
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Data to encode in the token
        expires_delta: Token expiration time
        
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expiration_minutes)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm
    )
    
    return encoded_jwt

def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        data: Data to encode in the token
        expires_delta: Token expiration time
        
    Returns:
        Encoded JWT refresh token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.jwt_refresh_expiration_days)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm
    )
    
    return encoded_jwt

def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT token to decode
        
    Returns:
        Decoded token payload
        
    Raises:
        AuthenticationError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError as e:
        raise AuthenticationError(f"Invalid token: {str(e)}")

def generate_api_key() -> str:
    """
    Generate a secure API key.
    
    Returns:
        Secure random API key
    """
    return secrets.token_urlsafe(32)

def generate_secret_token() -> str:
    """
    Generate a secure secret token.
    
    Returns:
        Secure random token
    """
    return secrets.token_hex(32)

def generate_verification_code(length: int = 6) -> str:
    """
    Generate a numeric verification code.
    
    Args:
        length: Length of the code
        
    Returns:
        Numeric verification code
    """
    return "".join(secrets.choice("0123456789") for _ in range(length))

class DataEncryption:
    """Symmetric encryption for sensitive data"""
    
    def __init__(self, key: Optional[str] = None):
        """
        Initialize encryption with key.
        
        Args:
            key: Encryption key (base64 encoded)
        """
        if key:
            self.fernet = Fernet(key.encode())
        else:
            # Generate a new key if not provided
            self.key = Fernet.generate_key()
            self.fernet = Fernet(self.key)
    
    def encrypt(self, data: Union[str, bytes]) -> str:
        """
        Encrypt data.
        
        Args:
            data: Data to encrypt
            
        Returns:
            Encrypted data (base64 encoded)
        """
        if isinstance(data, str):
            data = data.encode()
        
        encrypted = self.fernet.encrypt(data)
        return encrypted.decode()
    
    def decrypt(self, encrypted_data: Union[str, bytes]) -> str:
        """
        Decrypt data.
        
        Args:
            encrypted_data: Encrypted data (base64 encoded)
            
        Returns:
            Decrypted data
        """
        if isinstance(encrypted_data, str):
            encrypted_data = encrypted_data.encode()
        
        decrypted = self.fernet.decrypt(encrypted_data)
        return decrypted.decode()

def compute_signature(data: str, secret: str) -> str:
    """
    Compute HMAC signature for webhook validation.
    
    Args:
        data: Data to sign
        secret: Secret key
        
    Returns:
        HMAC signature (hex)
    """
    return hmac.new(
        secret.encode(),
        data.encode(),
        hashlib.sha256
    ).hexdigest()

def verify_signature(data: str, signature: str, secret: str) -> bool:
    """
    Verify HMAC signature.
    
    Args:
        data: Original data
        signature: Signature to verify
        secret: Secret key
        
    Returns:
        True if signature is valid
    """
    expected_signature = compute_signature(data, secret)
    return hmac.compare_digest(signature, expected_signature)

def sanitize_input(text: str) -> str:
    """
    Sanitize user input to prevent injection attacks.
    
    Args:
        text: Input text
        
    Returns:
        Sanitized text
    """
    # Remove null bytes
    text = text.replace("\x00", "")
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    # Limit length
    max_length = 10000
    if len(text) > max_length:
        text = text[:max_length]
    
    return text

def mask_sensitive_data(data: str, mask_char: str = "*", visible_chars: int = 4) -> str:
    """
    Mask sensitive data for logging.
    
    Args:
        data: Sensitive data to mask
        mask_char: Character to use for masking
        visible_chars: Number of characters to leave visible
        
    Returns:
        Masked data
    """
    if len(data) <= visible_chars * 2:
        return mask_char * len(data)
    
    return data[:visible_chars] + mask_char * (len(data) - visible_chars * 2) + data[-visible_chars:]
```

#### Validation Checklist for Step 1.4:
- [ ] Password hashing using bcrypt
- [ ] Password strength validation implemented
- [ ] JWT token creation and validation working
- [ ] Refresh token mechanism implemented
- [ ] API key generation secure
- [ ] Data encryption/decryption functional
- [ ] HMAC signature verification working
- [ ] Input sanitization comprehensive
- [ ] Sensitive data masking implemented

### Phase 1 Master Checklist:
- [ ] All configuration files created and valid
- [ ] Core configuration module complete with validation
- [ ] Logging infrastructure operational with correlation IDs
- [ ] Security utilities comprehensive and tested
- [ ] All dependencies installed successfully
- [ ] Environment variables documented
- [ ] Error handling hierarchy established
- [ ] Constants and enums defined
- [ ] All code has type hints
- [ ] All functions have docstrings

---

## 📊 PHASE 2: Database Layer Implementation

### Overview
Implement complete database layer with models, schemas, repositories, and migrations. This phase establishes the data foundation for the entire application.

### Step 2.1: Database Connection and Base Configuration

#### Files to Create:

##### 2.1.1 - src/database/connection.py
```python
# Purpose: Database connection management with connection pooling
# Location: /src/database/connection.py
# Dependencies: sqlalchemy, asyncpg
# Interface: Database session management and connection lifecycle

from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager
import asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker
)
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy import event, pool
from src.core.config import get_settings
from src.core.logging import get_logger
from src.core.exceptions import DatabaseError

logger = get_logger(__name__)
settings = get_settings()

class DatabaseConnection:
    """
    Manages database connections with pooling and health checks.
    Implements singleton pattern for connection reuse.
    """
    
    _instance: Optional["DatabaseConnection"] = None
    _engine: Optional[AsyncEngine] = None
    _session_factory: Optional[async_sessionmaker] = None
    
    def __new__(cls) -> "DatabaseConnection":
        """Singleton pattern implementation"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def initialize(self) -> None:
        """
        Initialize database connection and session factory.
        Should be called once during application startup.
        """
        if self._engine is not None:
            logger.warning("Database already initialized")
            return
        
        try:
            # Create engine with connection pooling
            self._engine = create_async_engine(
                settings.database_url,
                echo=settings.postgres_echo,
                pool_size=settings.postgres_pool_size,
                max_overflow=settings.postgres_max_overflow,
                pool_pre_ping=True,  # Verify connections before using
                pool_recycle=3600,  # Recycle connections after 1 hour
                connect_args={
                    "server_settings": {"application_name": "ai_customer_service"},
                    "command_timeout": 60,
                    "timeout": 30,
                }
            )
            
            # Create session factory
            self._session_factory = async_sessionmaker(
                self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False
            )
            
            # Test connection
            async with self._engine.begin() as conn:
                await conn.execute("SELECT 1")
            
            logger.info("Database connection initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise DatabaseError(f"Database initialization failed: {str(e)}")
    
    async def close(self) -> None:
        """
        Close database connections.
        Should be called during application shutdown.
        """
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("Database connection closed")
    
    @property
    def engine(self) -> AsyncEngine:
        """Get database engine"""
        if self._engine is None:
            raise DatabaseError("Database not initialized")
        return self._engine
    
    @property
    def session_factory(self) -> async_sessionmaker:
        """Get session factory"""
        if self._session_factory is None:
            raise DatabaseError("Database not initialized")
        return self._session_factory
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get database session.
        
        Yields:
            AsyncSession: Database session
            
        Raises:
            DatabaseError: If database is not initialized
        """
        if self._session_factory is None:
            raise DatabaseError("Database not initialized")
        
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Database session error: {str(e)}")
                raise DatabaseError(f"Database operation failed: {str(e)}")
            finally:
                await session.close()
    
    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Create a database transaction context.
        
        Yields:
            AsyncSession: Database session with transaction
        """
        async with self.get_session() as session:
            async with session.begin():
                yield session
    
    async def health_check(self) -> bool:
        """
        Check database health.
        
        Returns:
            bool: True if database is healthy
        """
        try:
            async with self._engine.begin() as conn:
                result = await conn.execute("SELECT 1")
                return result.scalar() == 1
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return False

# Global database instance
db = DatabaseConnection()

async def init_db() -> None:
    """Initialize database connection"""
    await db.initialize()

async def close_db() -> None:
    """Close database connection"""
    await db.close()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI to get database session.
    
    Yields:
        AsyncSession: Database session
    """
    async with db.get_session() as session:
        yield session
```

##### 2.1.2 - src/database/base.py
```python
# Purpose: SQLAlchemy base model and common mixins
# Location: /src/database/base.py
# Dependencies: sqlalchemy
# Interface: Base model class and common database mixins

from typing import Any
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, DateTime, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """Base class for all database models"""
    
    @declared_attr
    def __tablename__(cls) -> str:
        """Generate table name from class name"""
        name = cls.__name__
        # Convert CamelCase to snake_case
        result = []
        for i, char in enumerate(name):
            if i > 0 and char.isupper():
                result.append('_')
            result.append(char.lower())
        return ''.join(result)

class TimestampMixin:
    """Mixin for adding timestamp fields"""
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

class UUIDMixin:
    """Mixin for UUID primary key"""
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False
    )

class SoftDeleteMixin:
    """Mixin for soft delete functionality"""
    
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    
    def soft_delete(self) -> None:
        """Mark record as deleted"""
        self.deleted_at = datetime.utcnow()
        self.is_deleted = True
    
    def restore(self) -> None:
        """Restore soft deleted record"""
        self.deleted_at = None
        self.is_deleted = False

class AuditMixin:
    """Mixin for audit fields"""
    
    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    deleted_by = Column(UUID(as_uuid=True), nullable=True)

# Combined base model with common mixins
class BaseModel(Base, UUIDMixin, TimestampMixin):
    """Base model with UUID and timestamps"""
    __abstract__ = True
    
    def to_dict(self) -> dict:
        """Convert model to dictionary"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }

class AuditableModel(BaseModel, AuditMixin, SoftDeleteMixin):
    """Base model with full audit trail"""
    __abstract__ = True
```

#### Validation Checklist for Step 2.1:
- [ ] Database connection uses async SQLAlchemy
- [ ] Connection pooling configured correctly
- [ ] Singleton pattern implemented for connection
- [ ] Health check functionality working
- [ ] Transaction context manager implemented
- [ ] Base model includes all common fields
- [ ] Mixins are reusable and well-designed
- [ ] Soft delete functionality included
- [ ] Audit fields tracked properly

### Step 2.2: Domain Models Implementation

#### Files to Create:

##### 2.2.1 - src/models/organization.py
```python
# Purpose: Organization model for multi-tenancy
# Location: /src/models/organization.py
# Dependencies: sqlalchemy, src.database.base
# Interface: Organization entity with subscription and limits

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, 
    JSON, ARRAY, Enum as SQLEnum, Numeric
)
from sqlalchemy.orm import relationship
from src.database.base import BaseModel
from src.core.constants import UserRole

class SubscriptionTier(str):
    """Subscription tier enumeration"""
    TRIAL = "trial"
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"

class Organization(BaseModel):
    """
    Organization model for multi-tenant support.
    Represents a customer organization with subscription and resource limits.
    """
    
    __tablename__ = "organizations"
    __table_args__ = {"schema": "core"}
    
    # Basic Information
    slug = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    display_name = Column(String(255))
    description = Column(String(1000))
    website = Column(String(500))
    logo_url = Column(String(500))
    
    # Subscription
    subscription_tier = Column(
        String(50),
        nullable=False,
        default=SubscriptionTier.TRIAL
    )
    subscription_status = Column(String(50), nullable=False, default="active")
    subscription_started_at = Column(DateTime(timezone=True))
    subscription_expires_at = Column(DateTime(timezone=True))
    trial_ends_at = Column(DateTime(timezone=True))
    mrr_amount = Column(Numeric(10, 2))  # Monthly recurring revenue
    
    # Resource Limits
    max_users = Column(Integer, nullable=False, default=10)
    max_conversations_per_month = Column(Integer, nullable=False, default=1000)
    max_messages_per_conversation = Column(Integer, nullable=False, default=100)
    max_knowledge_entries = Column(Integer, nullable=False, default=1000)
    max_api_calls_per_hour = Column(Integer, nullable=False, default=10000)
    storage_quota_gb = Column(Integer, nullable=False, default=10)
    
    # Current Usage (updated by triggers)
    current_users_count = Column(Integer, nullable=False, default=0)
    current_month_conversations = Column(Integer, nullable=False, default=0)
    current_storage_gb = Column(Numeric(10, 3), nullable=False, default=0)
    total_conversations_lifetime = Column(Integer, nullable=False, default=0)
    
    # Settings and Features
    settings = Column(JSON, nullable=False, default=dict)
    features = Column(JSON, nullable=False, default=dict)
    branding = Column(JSON, default=dict)
    
    # Localization
    timezone = Column(String(50), nullable=False, default="UTC")
    default_language = Column(String(10), nullable=False, default="en")
    supported_languages = Column(ARRAY(String), default=["en"])
    
    # Security
    allowed_domains = Column(ARRAY(String), default=[])
    ip_whitelist = Column(ARRAY(String), default=[])
    require_mfa = Column(Boolean, default=False)
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    is_verified = Column(Boolean, nullable=False, default=False)
    is_demo = Column(Boolean, default=False)
    
    # Metadata
    metadata = Column(JSON, default=dict)
    tags = Column(ARRAY(String), default=[])
    
    # Relationships
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="organization")
    
    def is_trial_active(self) -> bool:
        """Check if trial period is active"""
        if self.subscription_tier != SubscriptionTier.TRIAL:
            return False
        if not self.trial_ends_at:
            return False
        return datetime.utcnow() < self.trial_ends_at
    
    def is_subscription_active(self) -> bool:
        """Check if subscription is active"""
        if self.subscription_status != "active":
            return False
        if self.subscription_expires_at:
            return datetime.utcnow() < self.subscription_expires_at
        return True
    
    def check_user_limit(self) -> bool:
        """Check if user limit is reached"""
        return self.current_users_count < self.max_users
    
    def check_conversation_limit(self) -> bool:
        """Check if monthly conversation limit is reached"""
        return self.current_month_conversations < self.max_conversations_per_month
    
    def check_storage_limit(self) -> bool:
        """Check if storage limit is reached"""
        return float(self.current_storage_gb) < self.storage_quota_gb
    
    def get_feature(self, feature_name: str) -> bool:
        """Check if a feature is enabled"""
        return self.features.get(feature_name, False)
    
    def get_setting(self, setting_name: str, default: Any = None) -> Any:
        """Get a setting value"""
        return self.settings.get(setting_name, default)
    
    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, slug='{self.slug}', tier='{self.subscription_tier}')>"
```

##### 2.2.2 - src/models/user.py
```python
# Purpose: User model with authentication and profile
# Location: /src/models/user.py
# Dependencies: sqlalchemy, src.database.base
# Interface: User entity with roles and permissions

from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, DateTime, JSON, 
    ARRAY, ForeignKey, Numeric, Integer
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.database.base import BaseModel
from src.core.constants import UserRole

class User(BaseModel):
    """
    User model for authentication and profile management.
    Supports both customers and agents with role-based access.
    """
    
    __tablename__ = "users"
    __table_args__ = {"schema": "core"}
    
    # Foreign Keys
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("core.organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Authentication
    email = Column(String(255), nullable=False, index=True)
    email_verified = Column(Boolean, default=False)
    email_verified_at = Column(DateTime(timezone=True))
    username = Column(String(100), index=True)
    password_hash = Column(String(255))
    password_changed_at = Column(DateTime(timezone=True))
    
    # Multi-factor Authentication
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(255))  # Encrypted
    mfa_backup_codes = Column(ARRAY(String))  # Encrypted
    
    # Profile
    first_name = Column(String(100))
    last_name = Column(String(100))
    display_name = Column(String(200))
    avatar_url = Column(String(500))
    phone_number = Column(String(50))
    phone_verified = Column(Boolean, default=False)
    
    # Role and Permissions
    role = Column(String(50), nullable=False, default=UserRole.CUSTOMER)
    permissions = Column(JSON, default=dict)
    is_admin = Column(Boolean, default=False)
    is_agent = Column(Boolean, default=False)
    
    # Customer Attributes
    customer_tier = Column(String(50))
    customer_since = Column(DateTime(timezone=True))
    lifetime_value = Column(Numeric(15, 2), default=0)
    total_conversations = Column(Integer, default=0)
    average_satisfaction_score = Column(Numeric(3, 2))
    
    # Preferences
    preferred_language = Column(String(10), default="en")
    timezone = Column(String(50))
    notification_preferences = Column(JSON, default=dict)
    communication_preferences = Column(JSON, default=dict)
    
    # API Access
    api_key = Column(String(255), unique=True, index=True)
    api_secret_hash = Column(String(255))
    api_rate_limit = Column(Integer, default=1000)
    api_last_used_at = Column(DateTime(timezone=True))
    
    # Session Management
    is_online = Column(Boolean, default=False)
    last_seen_at = Column(DateTime(timezone=True))
    last_ip_address = Column(String(45))
    last_user_agent = Column(String(500))
    
    # Status
    status = Column(String(50), default="active")
    suspended_until = Column(DateTime(timezone=True))
    
    # Metadata
    attributes = Column(JSON, default=dict)
    tags = Column(ARRAY(String), default=[])
    
    # Relationships
    organization = relationship("Organization", back_populates="users")
    conversations = relationship("Conversation", back_populates="user")
    messages = relationship("Message", back_populates="sender")
    
    @property
    def full_name(self) -> str:
        """Get user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.display_name or self.email
    
    def is_active(self) -> bool:
        """Check if user is active"""
        if self.status != "active":
            return False
        if self.suspended_until:
            return datetime.utcnow() > self.suspended_until
        return True
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission"""
        if self.is_admin:
            return True
        return self.permissions.get(permission, False)
    
    def can_access_api(self) -> bool:
        """Check if user can access API"""
        return bool(self.api_key) and self.is_active()
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"
```

##### 2.2.3 - src/models/conversation.py
```python
# Purpose: Conversation model for chat sessions
# Location: /src/models/conversation.py
# Dependencies: sqlalchemy, src.database.base
# Interface: Conversation entity with state and metrics

from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, 
    JSON, ARRAY, ForeignKey, Numeric, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.database.base import BaseModel
from src.core.constants import ConversationStatus, ConversationChannel, Priority

class Conversation(BaseModel):
    """
    Conversation model representing a chat session.
    Tracks conversation state, metrics, and resolution.
    """
    
    __tablename__ = "conversations"
    __table_args__ = {"schema": "core"}
    
    # Foreign Keys
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("core.organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("core.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    assigned_agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("core.users.id"),
        nullable=True,
        index=True
    )
    
    # Identifiers
    conversation_number = Column(Integer, autoincrement=True, unique=True)
    external_id = Column(String(255))
    thread_id = Column(UUID(as_uuid=True), index=True)
    
    # Basic Information
    title = Column(String(500))
    description = Column(Text)
    channel = Column(String(50), nullable=False, default=ConversationChannel.WEB)
    source = Column(String(100))
    
    # Status and Priority
    status = Column(
        String(50),
        nullable=False,
        default=ConversationStatus.INITIALIZED,
        index=True
    )
    priority = Column(Integer, default=Priority.MEDIUM)
    is_urgent = Column(Boolean, default=False)
    
    # Timing
    started_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    first_message_at = Column(DateTime(timezone=True))
    first_response_at = Column(DateTime(timezone=True))
    last_activity_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    ended_at = Column(DateTime(timezone=True))
    
    # Message Counts
    message_count = Column(Integer, default=0)
    user_message_count = Column(Integer, default=0)
    agent_message_count = Column(Integer, default=0)
    ai_message_count = Column(Integer, default=0)
    
    # Response Times (seconds)
    first_response_time = Column(Integer)
    average_response_time = Column(Integer)
    max_response_time = Column(Integer)
    total_handle_time = Column(Integer)
    
    # AI Metrics
    ai_handled = Column(Boolean, default=True)
    ai_confidence_avg = Column(Numeric(4, 3))
    ai_confidence_min = Column(Numeric(4, 3))
    ai_resolution_score = Column(Numeric(5, 2))
    ai_fallback_count = Column(Integer, default=0)
    
    # Sentiment and Emotion
    sentiment_initial = Column(String(20))
    sentiment_current = Column(String(20), default="neutral")
    sentiment_final = Column(String(20))
    sentiment_trend = Column(String(20))
    emotion_trajectory = Column(JSON, default=list)
    
    # Resolution
    resolved = Column(Boolean, default=False, index=True)
    resolved_by = Column(String(50))
    resolved_at = Column(DateTime(timezone=True))
    resolution_time_seconds = Column(Integer)
    resolution_summary = Column(Text)
    resolution_code = Column(String(50))
    
    # Escalation
    escalated = Column(Boolean, default=False, index=True)
    escalation_reason = Column(String(255))
    escalated_at = Column(DateTime(timezone=True))
    escalation_count = Column(Integer, default=0)
    
    # Satisfaction
    satisfaction_score = Column(Numeric(2, 1))
    satisfaction_feedback = Column(Text)
    nps_score = Column(Integer)
    
    # Context and Metadata
    context = Column(JSON, nullable=False, default=dict)
    context_variables = Column(JSON, default=dict)
    metadata = Column(JSON, default=dict)
    tags = Column(ARRAY(String), default=[])
    
    # Integration References
    salesforce_case_id = Column(String(18), index=True)
    external_ticket_id = Column(String(100))
    
    # Relationships
    organization = relationship("Organization", back_populates="conversations")
    user = relationship("User", back_populates="conversations", foreign_keys=[user_id])
    assigned_agent = relationship("User", foreign_keys=[assigned_agent_id])
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    
    def is_active(self) -> bool:
        """Check if conversation is active"""
        return self.status in [
            ConversationStatus.ACTIVE,
            ConversationStatus.WAITING_FOR_USER,
            ConversationStatus.WAITING_FOR_AGENT,
            ConversationStatus.PROCESSING
        ]
    
    def can_send_message(self) -> bool:
        """Check if messages can be sent"""
        return self.is_active() and not self.resolved
    
    def calculate_resolution_time(self) -> Optional[int]:
        """Calculate resolution time in seconds"""
        if self.resolved and self.resolved_at and self.started_at:
            delta = self.resolved_at - self.started_at
            return int(delta.total_seconds())
        return None
    
    def needs_escalation(self) -> bool:
        """Check if conversation needs escalation"""
        # Business logic for escalation
        if self.ai_confidence_avg and self.ai_confidence_avg < 0.3:
            return True
        if self.sentiment_current in ["very_negative", "angry"]:
            return True
        if self.ai_fallback_count >= 3:
            return True
        return False
    
    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, number={self.conversation_number}, status='{self.status}')>"
```

#### Validation Checklist for Step 2.2:
- [ ] All models inherit from appropriate base classes
- [ ] Foreign key relationships properly defined
- [ ] Indexes added for frequently queried fields
- [ ] Business logic methods implemented
- [ ] JSON fields have default values
- [ ] Decimal fields have appropriate precision
- [ ] Timestamp fields use timezone-aware datetime
- [ ] All models have meaningful __repr__ methods
- [ ] Relationships configured with proper cascade options

---

## 🔄 Phase Independence Verification

### Parallel Execution Matrix

| Phase | Can Start After | Can Run Parallel With | Produces | Consumes |
|-------|----------------|---------------------|----------|----------|
| 1 | None | None | Config, Logging, Security | None |
| 2 | None | 3, 4, 5 | Models, Schemas | Config |
| 3 | None | 2, 4, 5 | API Framework | Config |
| 4 | None | 2, 3, 5 | Business Logic | Config |
| 5 | None | 2, 3, 4 | AI Services | Config |
| 6 | 1 | 7, 8 | Conversation Engine | All Core |
| 7 | 1 | 6, 8 | Integrations | Config |
| 8 | 1 | 6, 7 | Frontend | Config |
| 9 | All | None | Tests | All |
| 10 | 1 | None | Deployment | Config |

---

## 🏁 Master Execution Checklist

### Phase Completion Verification

#### Phase 1: Core Infrastructure ✓
- [ ] Configuration management operational
- [ ] Logging with correlation IDs working
- [ ] Security utilities tested
- [ ] Exception hierarchy complete
- [ ] All environment variables documented

#### Phase 2: Database Layer ✓
- [ ] Database connection pooling active
- [ ] All models created with relationships
- [ ] Schemas validated with Pydantic
- [ ] Migrations generated successfully
- [ ] Indexes optimized for queries

#### Phase 3: API Framework
- [ ] FastAPI application running
- [ ] All middleware configured
- [ ] WebSocket support functional
- [ ] OpenAPI documentation complete
- [ ] Rate limiting active

#### Phase 4: Business Logic
- [ ] Service layer implemented
- [ ] Rules engine operational
- [ ] Workflow engine tested
- [ ] SLA tracking functional
- [ ] Escalation logic verified

#### Phase 5: AI Integration
- [ ] LLM connections established
- [ ] NLP models loaded
- [ ] Knowledge base indexed
- [ ] RAG pipeline operational
- [ ] Fallback chains tested

#### Phase 6: Conversation Management
- [ ] State machine functioning
- [ ] Context preservation verified
- [ ] Message processing complete
- [ ] Emotion tracking active
- [ ] Analytics collection working

#### Phase 7: External Integrations
- [ ] Salesforce connected
- [ ] Communication channels integrated
- [ ] Webhooks operational
- [ ] Third-party APIs connected
- [ ] Sync mechanisms tested

#### Phase 8: Frontend Application
- [ ] Components rendered correctly
- [ ] State management functional
- [ ] API integration complete
- [ ] WebSocket connected
- [ ] Responsive design verified

#### Phase 9: Testing Suite
- [ ] Unit test coverage > 85%
- [ ] Integration tests passing
- [ ] E2E tests complete
- [ ] Performance benchmarks met
- [ ] Security scans clean

#### Phase 10: Deployment
- [ ] Docker images built
- [ ] Kubernetes manifests validated
- [ ] CI/CD pipelines operational
- [ ] Monitoring active
- [ ] Documentation complete

---

## 📊 Success Metrics

### Code Quality Standards
- **Test Coverage**: Minimum 85%
- **Type Coverage**: 100% for public APIs
- **Documentation**: All public functions documented
- **Complexity**: Cyclomatic complexity < 10
- **Performance**: All endpoints < 200ms P50

### Delivery Milestones
- **Phase 1-2**: Foundation complete (Week 1)
- **Phase 3-5**: Core services ready (Week 2)
- **Phase 6-7**: Business logic operational (Week 3)
- **Phase 8-9**: Frontend and testing (Week 4)
- **Phase 10**: Production deployment (Week 5)

---

## 🎯 Critical Success Factors

### For AI Coding Agents

1. **Start with imports**: Always verify all imports before implementation
2. **Type everything**: No untyped functions or variables
3. **Test first**: Write tests before implementation
4. **Document inline**: Add docstrings immediately
5. **Handle errors**: Never leave exceptions unhandled
6. **Log appropriately**: Use correct log levels
7. **Validate inputs**: Check all inputs at boundaries
8. **Follow patterns**: Use established patterns consistently

### Common Implementation Pitfalls to Avoid

1. **Circular imports**: Plan module dependencies carefully
2. **Synchronous blocking**: Always use async/await
3. **Resource leaks**: Close all connections properly
4. **SQL injection**: Use parameterized queries only
5. **Hardcoded values**: Use configuration always
6. **Missing indexes**: Add indexes for all foreign keys
7. **Unhandled promises**: Catch all async errors
8. **Memory leaks**: Dispose of resources properly

---

This comprehensive execution plan provides everything needed for AI coding agents to build the complete system independently. Each phase is self-contained with clear specifications, validation criteria, and no ambiguity about implementation details. The plan ensures high-quality, production-ready code that follows best practices and maintains consistency across all components.
