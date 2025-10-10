# Augustan Trading System - Dockerfile
# Multi-stage build for production-ready container

# ============================================================================
# BUILD STAGE
# ============================================================================
FROM python:3.9-slim as builder

# Set build arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

# Add labels for metadata
LABEL maintainer="Augustan Trading System" \
      org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.version=$VERSION \
      org.label-schema.name="augustan-trading-system" \
      org.label-schema.description="Cryptocurrency trading system with AI/ML strategies" \
      org.label-schema.vcs-url="https://github.com/your-org/augustan"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ============================================================================
# PRODUCTION STAGE
# ============================================================================
FROM python:3.9-slim as production

# Create non-root user for security
RUN groupadd -r augustan && useradd -r -g augustan augustan

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder stage
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/config && \
    chown -R augustan:augustan /app

# Switch to non-root user
USER augustan

# Set environment variables
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENVIRONMENT=production \
    PAPER_TRADING=true \
    LIVE_TRADING=false

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Default command
CMD ["python", "-m", "trading_system.cli", "--help"]

# Expose port (if API server is implemented)
EXPOSE 8000

# ============================================================================
# DEVELOPMENT STAGE
# ============================================================================
FROM python:3.9-slim as development

# Install development dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install all dependencies including dev tools
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/config

# Set environment variables for development
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=development \
    DEBUG=true \
    PAPER_TRADING=true \
    LIVE_TRADING=false

# Default command for development
CMD ["python", "-m", "trading_system.cli", "--help"]

# ============================================================================
# TESTING STAGE
# ============================================================================
FROM python:3.9-slim as testing

# Install testing dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install all dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/config

# Set environment variables for testing
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=testing \
    DEBUG=true \
    PAPER_TRADING=true \
    LIVE_TRADING=false \
    TEST_DATABASE_URL=sqlite:///./test_trading.db

# Default command for testing
CMD ["python", "run_tests.py"]
