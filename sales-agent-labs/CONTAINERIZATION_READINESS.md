# Presgen Containerization Readiness Assessment

**Project**: Presgen Core & Data
**Date**: October 24, 2025
**Status**: Development - Not Yet Containerized (But Ready)

---

## Executive Summary

**Current State**: Presgen is **NOT containerized** - there are no Dockerfile, docker-compose, or container orchestration files in the repository.

**Readiness Level**: **High** - The architecture is well-suited for containerization with minimal changes required.

**Estimated Effort**: 2-3 days to production-ready containers

---

## Current Deployment Model

### How It Runs Today

**Backend**:
```bash
cd sales-agent-labs
uvicorn src.service.http:app --reload --port 8080
```

**Frontend**:
```bash
cd presgen-ui
npm run dev  # Development mode on localhost:3000
```

**Requirements**:
- Python 3.13 installed locally
- Node.js 18+ installed locally
- Google Cloud credentials in local files
- Manual environment variable setup
- Direct file system access to `out/` directory

### Why This Works (For Now)

✅ Single developer environment
✅ Full control over dependencies
✅ Easy debugging with hot reload
✅ No orchestration complexity

❌ Not scalable
❌ Not reproducible across environments
❌ No isolation between components
❌ Manual deployment process

---

## Containerization Readiness Analysis

### ✅ What's Already Container-Friendly

#### 1. **Clean Dependency Management**
```
requirements.txt (Python) - 95 packages with pinned versions
presgen-ui/package.json (Node.js) - All frontend deps specified
```
**Why this matters**: No manual "install X, then Y" instructions needed

#### 2. **Stateless Application Design**
- FastAPI server doesn't maintain sessions or in-memory state
- All persistent data in `out/` directory (can be volume-mounted)
- MCP subprocess communication works fine in containers

#### 3. **Environment Variable Configuration**
```bash
# .env file already used for all secrets
GOOGLE_CLOUD_PROJECT=...
GOOGLE_APPLICATION_CREDENTIALS=...
SLACK_BOT_TOKEN=...
```
**Why this matters**: 12-factor app compliance, easy to pass into containers

#### 4. **Clear Service Boundaries**
- Backend: Port 8080
- Frontend: Port 3000/3003
- MCP Server: Subprocess (no external port)
- No tight coupling requiring shared file system

#### 5. **Subprocess Architecture Works in Containers**
```python
# src/mcp_lab/rpc_client.py
subprocess.Popen([sys.executable, "-m", "src.mcp.server"], ...)
```
**Why this matters**: No Docker-in-Docker needed, just Python subprocess

#### 6. **Single Binary Execution**
- Backend starts with one command: `uvicorn ...`
- Frontend starts with one command: `npm run dev` (or `npm start` for prod)
- No multi-step initialization process

---

### ⚠️ What Needs Adjustment for Containers

#### 1. **File System Dependencies**

**Current Issue**:
```python
# Hardcoded local paths
out/data/         # Uploaded datasets
out/images/       # Generated charts
out/state/        # Cache
src/logs/         # Application logs
```

**Container Solution**:
- Mount volumes for persistent data
- Use Cloud Storage (GCS) for production
- Container-local ephemeral storage for temp files

**Code Changes Needed**:
```python
# config.py - Add support for GCS paths
DATA_DIR = os.getenv("DATA_DIR", "out/data")  # Can be gs://bucket/data
```

#### 2. **Google Cloud Credentials**

**Current Issue**:
```bash
GOOGLE_APPLICATION_CREDENTIALS=./presgen-service-account.json
```
File path won't exist in container unless explicitly copied (security risk).

**Container Solution**:
```dockerfile
# Option 1: Use Workload Identity (GKE/Cloud Run)
# No credential files needed, IAM-based

# Option 2: Mount secret as volume
# Better than baking into image
```

#### 3. **OAuth Token Storage**

**Current Issue**:
```python
# token.json stored locally
# Needs to persist across container restarts
```

**Container Solution**:
- Store in mounted volume
- Or use Secret Manager with refresh token
- Or session-based OAuth in web UI

#### 4. **Next.js Production Build**

**Current Issue**:
```bash
npm run dev  # Development mode, not optimized
```

**Container Solution**:
```dockerfile
RUN npm run build  # Creates optimized production build
CMD ["npm", "start"]  # Serves production build
```

#### 5. **Log File Management**

**Current Issue**:
```python
# Logs written to src/logs/presgen-{timestamp}.log
```

**Container Solution**:
- Write to stdout/stderr (container-native)
- Use log aggregation (Cloud Logging, Datadog)
- Or mount log volume

---

## Proposed Container Architecture

### Multi-Stage Docker Build

```dockerfile
# ── Backend Dockerfile ──
FROM python:3.13-slim as backend

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ src/
COPY config.yaml .

# Create directories for volumes
RUN mkdir -p /app/out/data /app/out/images /app/out/state

# Non-root user for security
RUN useradd -m -u 1000 presgen && chown -R presgen:presgen /app
USER presgen

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s \
  CMD curl -f http://localhost:8080/health || exit 1

# Run application
CMD ["uvicorn", "src.service.http:app", "--host", "0.0.0.0", "--port", "8080"]
```

```dockerfile
# ── Frontend Dockerfile ──
FROM node:18-alpine as builder

WORKDIR /app

# Install dependencies
COPY presgen-ui/package*.json ./
RUN npm ci --only=production

# Copy source and build
COPY presgen-ui/ .
RUN npm run build

# Production image
FROM node:18-alpine
WORKDIR /app

COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./

EXPOSE 3000

CMD ["npm", "start"]
```

### Docker Compose for Local Development

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    ports:
      - "8080:8080"
    environment:
      - GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT}
      - GOOGLE_CLOUD_REGION=${GOOGLE_CLOUD_REGION}
      - PRESGEN_USE_CACHE=true
    volumes:
      - ./out:/app/out  # Persistent data
      - gcp-credentials:/app/credentials:ro  # Read-only credentials
    env_file:
      - .env
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build:
      context: ./presgen-ui
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_BASE_URL=http://backend:8080
    depends_on:
      - backend

volumes:
  gcp-credentials:
    driver: local
```

---

## Production Deployment Path

### Recommended: Google Cloud Run

**Why Cloud Run?**
- ✅ Serverless (no container orchestration)
- ✅ Auto-scaling (0 to N instances)
- ✅ Pay-per-request pricing
- ✅ Built-in HTTPS
- ✅ Integrated with GCP services (Vertex AI, Cloud Storage)

**Deployment Steps**:

1. **Build container image**:
```bash
gcloud builds submit --tag gcr.io/$PROJECT_ID/presgen-backend
```

2. **Deploy to Cloud Run**:
```bash
gcloud run deploy presgen-backend \
  --image gcr.io/$PROJECT_ID/presgen-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT_ID \
  --service-account presgen-sa@$PROJECT_ID.iam.gserviceaccount.com \
  --memory 2Gi \
  --timeout 600s \
  --concurrency 10
```

3. **No credential files needed**:
   - Service account attached to Cloud Run service
   - Workload Identity handles authentication

**Alternative: Google Kubernetes Engine (GKE)**

**When to use**:
- Need more control over scaling policies
- Want to run multiple services in same cluster
- Need persistent storage (StatefulSets)

**Trade-offs**:
- More complex setup
- Higher baseline cost (control plane)
- Requires Kubernetes expertise

---

## Migration Checklist

### Phase 1: Containerize Development Environment (1 day)

- [ ] Create `Dockerfile.backend`
- [ ] Create `Dockerfile.frontend`
- [ ] Create `docker-compose.yml`
- [ ] Create `.dockerignore` (exclude `.env`, `out/`, `node_modules/`)
- [ ] Test local development with `docker-compose up`
- [ ] Verify MCP subprocess communication works in container
- [ ] Test file uploads and data persistence with volumes

### Phase 2: Refactor File System Access (1 day)

- [ ] Abstract storage layer in `src/common/storage.py`
- [ ] Support both local filesystem and GCS paths
- [ ] Environment variable for storage backend (`STORAGE_BACKEND=local|gcs`)
- [ ] Migrate logs to stdout/stderr (remove file logging)
- [ ] Test with `STORAGE_BACKEND=local` in containers

### Phase 3: Production Cloud Run Deployment (1 day)

- [ ] Create service account with required IAM roles
- [ ] Store OAuth tokens in Secret Manager (not files)
- [ ] Update `config.yaml` to use Secret Manager
- [ ] Build production container image
- [ ] Deploy to Cloud Run staging environment
- [ ] Test end-to-end flow (text → slides)
- [ ] Test data pipeline (CSV → slides with charts)
- [ ] Set up Cloud Logging for centralized logs
- [ ] Configure Cloud Monitoring alerts

### Phase 4: Frontend Production Build (0.5 days)

- [ ] Create optimized Next.js production build
- [ ] Deploy frontend to Cloud Run (separate service)
- [ ] Configure custom domain (optional)
- [ ] Update CORS settings for production URLs

### Phase 5: CI/CD Pipeline (0.5 days)

- [ ] GitHub Actions workflow for automated builds
- [ ] Automated testing in containers
- [ ] Deploy on merge to `main` branch

**Total Estimated Effort**: 3-4 days

---

## Cost Implications

### Current Development Cost
- $0 infrastructure (runs on laptop)
- ~$315-615/month API costs (OpenAI, Firecrawl, etc.)

### Containerized Cloud Run Cost (Estimated)

**Assumptions**:
- 500 presentations/month
- Average request: 45 seconds
- Memory: 2 GiB
- CPU: 1 vCPU

**Cloud Run Pricing**:
```
CPU: $0.00002400 per vCPU-second
Memory: $0.00000250 per GiB-second

Monthly Cost:
- CPU: 500 requests × 45s × $0.000024 = $0.54
- Memory: 500 × 45s × 2 GiB × $0.0000025 = $0.11
- Requests: 500 × $0.40 per million = $0.0002

Total Cloud Run: ~$0.65/month (negligible!)
```

**Additional Costs**:
- Cloud Storage (for `out/` replacement): ~$5/month
- Cloud Logging: ~$10/month (can be disabled)
- Load Balancer (if using custom domain): ~$18/month

**Total Infrastructure**: ~$33/month + existing API costs

---

## Comparison: Current vs. Containerized

| Aspect | Current (Local) | Containerized (Cloud Run) |
|--------|----------------|---------------------------|
| **Setup Time** | 30 min (Python + Node install) | 5 min (just `gcloud run deploy`) |
| **Reproducibility** | Low (works on my machine™) | High (exact same container everywhere) |
| **Scaling** | 1 instance (your laptop) | Auto-scale 0 to N instances |
| **Availability** | Only when laptop on | 99.95% SLA |
| **Security** | Local files, manual secrets | IAM, Secret Manager, no credential files |
| **Cost** | $0 infra | ~$33/month infra |
| **Deployment** | Manual SSH/rsync | One command (`gcloud run deploy`) |
| **Rollback** | Git checkout, restart | One command (deploy previous image) |
| **Monitoring** | Local logs only | Cloud Logging, Error Reporting, Metrics |

---

## Risks & Mitigations

### Risk 1: MCP Subprocess Fails in Container
**Likelihood**: Low
**Impact**: High (breaks core functionality)
**Mitigation**:
- MCP already uses `subprocess.Popen` - works fine in containers
- Test thoroughly in development containers before production
- Add subprocess health monitoring

### Risk 2: Slow Cold Starts
**Likelihood**: Medium (Cloud Run cold starts)
**Impact**: Medium (first request after idle takes 5-10s)
**Mitigation**:
- Set minimum instances to 1 (costs ~$10/month)
- Use startup optimization (lazy imports)
- Pre-warm container with health checks

### Risk 3: Persistent Storage Issues
**Likelihood**: Medium (switching to GCS)
**Impact**: Medium (file upload/download errors)
**Mitigation**:
- Thoroughly test storage abstraction layer
- Keep local filesystem fallback for development
- Use GCS signed URLs for large files

### Risk 4: Secret Management Complexity
**Likelihood**: Low
**Impact**: Medium (credential errors)
**Mitigation**:
- Use Workload Identity (no credential files)
- Store OAuth tokens in Secret Manager
- Test secret access in staging first

---

## Recommendation for CTO

### Short-Term (Next 2 Weeks)
✅ **Containerize development environment**
- Proves out container architecture
- Enables consistent team onboarding
- Minimal risk (can fallback to local)

### Medium-Term (Next 30 Days)
✅ **Deploy to Cloud Run staging**
- Test production infrastructure
- Validate cost assumptions
- Identify any container-specific issues

### Long-Term (3-6 Months)
✅ **Full production migration**
- CI/CD pipeline
- Multi-region deployment
- Advanced monitoring and alerting

### Why This Matters

**Scalability**: Current architecture can't handle >1 concurrent user
**Reliability**: Laptop crashes = service down
**Team Growth**: New developers need clean setup, not "works on my machine"
**Customer Trust**: Production-grade infrastructure = credible product

---

## Appendix: Example Dockerfile (Backend)

```dockerfile
# Multi-stage build for smaller final image
FROM python:3.13-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# ── Final image ──
FROM python:3.13-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local

# Update PATH
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY src/ src/
COPY config.yaml .

# Create non-root user
RUN useradd -m -u 1000 presgen && \
    mkdir -p /app/out/data /app/out/images /app/out/state && \
    chown -R presgen:presgen /app

USER presgen

# Expose port
EXPOSE 8080

# Health check endpoint (add to FastAPI)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

# Run application
CMD ["uvicorn", "src.service.http:app", \
     "--host", "0.0.0.0", \
     "--port", "8080", \
     "--workers", "1", \
     "--log-level", "info"]
```

**Image Size Optimization**:
- Multi-stage build: ~400MB (vs 1GB+ single stage)
- No dev dependencies in final image
- Minimal base image (slim, not full Python)

---

**Status**: This assessment reflects the current non-containerized state and provides a clear roadmap for containerization. The architecture is well-suited for Docker, requiring only file system abstraction and credential management changes.

**Next Steps**: Review with team, prioritize containerization in sprint planning, allocate 3-4 days for implementation.
