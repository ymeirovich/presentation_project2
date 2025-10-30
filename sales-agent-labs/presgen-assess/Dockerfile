# Dockerfile for PresGen-Assess (Assessment API)
# Port: 8000
# Purpose: Assessment workflows, gap analysis, Google Forms integration

FROM python:3.11-slim

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
COPY presgen-assess/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY presgen-assess/src/ ./src/
COPY presgen-assess/tests/ ./tests/
COPY presgen-assess/.pre-commit-config.yaml ./
COPY presgen-assess/alembic.ini ./
COPY presgen-assess/alembic/ ./alembic/

# Copy sales-agent-labs slides_google.py and dependencies for Google Slides integration
# This creates the expected directory structure: /app/sales-agent-labs/src/agent/
RUN mkdir -p /app/sales-agent-labs/src/agent && \
    touch /app/sales-agent-labs/src/__init__.py && \
    touch /app/sales-agent-labs/src/agent/__init__.py
COPY src/agent/slides_google.py /app/sales-agent-labs/src/agent/slides_google.py
COPY src/agent/notes_apps_script.py /app/sales-agent-labs/src/agent/notes_apps_script.py
COPY src/agent/notes_native_api.py /app/sales-agent-labs/src/agent/notes_native_api.py

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

# Health check updated 2025-10-30
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run database migrations on startup, then start server
CMD alembic upgrade head && \
    uvicorn src.service.app:app --host 0.0.0.0 --port 8000 --workers 1 --log-level info
