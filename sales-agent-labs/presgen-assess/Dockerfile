# Dockerfile for PresGen-Assess (Assessment API)
# Port: 8000
# Purpose: Assessment workflows, gap analysis, Google Forms integration

FROM python:3.13-slim

LABEL maintainer="ymeirovich@gmail.com"
LABEL service="presgen-assess"
LABEL version="1.0"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY tests/ ./tests/
COPY .pre-commit-config.yaml ./
COPY alembic.ini ./
COPY alembic/ ./alembic/

# Create directories for runtime
RUN mkdir -p /app/data /app/logs /app/uploads /app/exports && \
    chmod 777 /app/data /app/logs /app/uploads /app/exports

# Create non-root user for security
RUN useradd -m -u 1000 presgen && \
    chown -R presgen:presgen /app

USER presgen

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    HOST=0.0.0.0 \
    LOG_LEVEL=INFO \
    DATABASE_URL=sqlite+aiosqlite:////app/data/presgen_assess.db \
    PRESGEN_CORE_URL=http://presgen-core:8080 \
    WORKERS=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Expose port
EXPOSE 8000

# Run database migrations on startup, then start server
CMD alembic upgrade head && \
    uvicorn src.service.app:app --host 0.0.0.0 --port 8000 --workers 1 --log-level info
