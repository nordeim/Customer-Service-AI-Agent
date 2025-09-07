# Multi-stage build for AI Customer Service Agent
FROM python:3.12-trixie AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libpq-dev \
    libssl-dev \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements first for better caching
COPY requirements.txt /tmp/requirements.txt

# Upgrade tooling and install deps (prefer binary wheels)
# pip install --prefer-binary -r /tmp/requirements.txt
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r /tmp/requirements.txt

# -----------------------------------------------------------------------------

FROM python:3.12-trixie

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Create non-root user
RUN groupadd -r aiagent && useradd -r -g aiagent aiagent

# Install runtime dependencies
# Note: Debian trixie provides these package names.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libssl3 \
    libffi8 \
    curl \
    netcat-traditional \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create application directories
RUN mkdir -p /app/logs /app/data /app/config && \
    chown -R aiagent:aiagent /app

# Set working directory
WORKDIR /app
ENV PYTHONPATH="/app"

# Copy application code
COPY --chown=aiagent:aiagent src/ ./src/
COPY --chown=aiagent:aiagent tests/ ./tests/
COPY --chown=aiagent:aiagent database_schema.sql ./
COPY --chown=aiagent:aiagent pyproject.toml ./
COPY --chown=aiagent:aiagent README.md ./

# Ensure directories exist with correct ownership
RUN mkdir -p /app/logs /app/data && \
    chown -R aiagent:aiagent /app

# Switch to non-root user
USER aiagent

# Health check (use curl to avoid Python import dependency)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Default command
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
