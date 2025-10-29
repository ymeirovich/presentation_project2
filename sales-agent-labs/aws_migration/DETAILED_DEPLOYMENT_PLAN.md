# Detailed Deployment Plan for PresGen on AWS Lightsail

**Version:** 2.0
**Date:** October 28, 2025
**Based on:** AWS_MIGRATION_PLAN.md v1.0
**Application:** PresGen Sales Agent Labs (3-tier architecture)
**Target:** AWS Lightsail + S3 + CloudWatch

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Critical Questions & Considerations](#critical-questions--considerations)
3. [Architecture Deep Dive](#architecture-deep-dive)
4. [Pre-Deployment Checklist](#pre-deployment-checklist)
5. [Dockerization](#dockerization)
6. [Lightsail Deployment Scripts](#lightsail-deployment-scripts)
7. [Post-Deployment Maintenance](#post-deployment-maintenance)
8. [Monitoring & Alerting](#monitoring--alerting)
9. [Troubleshooting Procedures](#troubleshooting-procedures)
10. [Scaling Strategies](#scaling-strategies)

---

## Executive Summary

### What We're Deploying

**PresGen Sales Agent Labs** is a **3-tier AI-powered presentation generation platform**:

```
┌──────────────────────────────────────────────────────────┐
│                  PresGen Full Stack                      │
├──────────────────────────────────────────────────────────┤
│  Frontend:  Next.js 15.5 + React 19 (Port 3000)         │
│  Assess:    FastAPI + SQLAlchemy (Port 8000)            │
│  Core:      FastAPI + MCP Orchestrator (Port 8080)      │
│  Database:  SQLite → PostgreSQL (production)            │
│  Storage:   Local FS → S3 (production)                  │
│  AI/ML:     Gemini, Vertex AI, GPT-4, ElevenLabs        │
└──────────────────────────────────────────────────────────┘
```

### Deployment Target

**AWS Lightsail** - Cost-optimized, simple management
- **Instance**: 2GB RAM, 2 vCPU ($10/month)
- **Storage**: 40GB SSD (expandable)
- **Services**: 3 Docker containers behind nginx reverse proxy
- **Total Cost**: $10-15/month

### Timeline

- **Dockerization**: 2-3 hours (NEW - not done yet)
- **AWS Setup**: 1 hour
- **Deployment**: 1-2 hours
- **Testing**: 1 hour
- **Total**: 5-7 hours

---

## Critical Questions & Considerations

### Questions You Haven't Asked (But Should Consider)

#### 1. Data Persistence & Disaster Recovery

**Q: What happens if the instance crashes?**

**Considerations:**
- SQLite database is on local disk → **Risk of data loss**
- Generated presentations, videos, assessments → **Need backup strategy**
- User uploaded files (Excel, documents) → **Should be in S3**

**Recommendations:**
- ✅ Use PostgreSQL instead of SQLite for production (better crash recovery)
- ✅ Daily automated snapshots of Lightsail instance ($0.60/month)
- ✅ Store ALL user uploads in S3 immediately (not local disk)
- ✅ Export database to S3 daily (via automated cron job)

**Decision Required:**
- [ ] Use PostgreSQL or stick with SQLite?
- [ ] Accept data loss risk or implement backup strategy?
- [ ] Budget $2-3/month extra for backups?

---

#### 2. API Secrets & Credentials Management

**Q: How do we securely store 5+ API keys?**

**Current API Dependencies:**
- OpenAI API Key (GPT-4 for assessment generation)
- Google Cloud Service Account JSON (Gemini, Vertex AI, Cloud Storage, Slides, Forms)
- Google OAuth Token (user-specific Google Workspace access)
- ElevenLabs API Key (text-to-speech)

**Risks:**
- Storing in `.env` file on server → **Vulnerable if SSH compromised**
- Hardcoding in Docker images → **Keys exposed in image layers**
- Logging API responses → **Accidental key exposure**

**Recommendations:**
- ✅ Use AWS Secrets Manager ($0.40/secret/month) OR
- ✅ Use environment variables ONLY (loaded at runtime, never committed)
- ✅ Implement key rotation schedule (every 90 days)
- ✅ Add logging filters to prevent key exposure
- ✅ Use IAM roles for AWS services (S3, CloudWatch) - no keys needed

**Decision Required:**
- [ ] Use AWS Secrets Manager ($2/month) or environment variables?
- [ ] Who manages key rotation?
- [ ] What's the incident response plan if keys are compromised?

---

#### 3. Google Cloud Authentication Strategy

**Q: How do we authenticate with Google APIs without OAuth consent flow on a headless server?**

**Critical Discovery:** Service accounts do NOT work with Google Workspace APIs (Slides, Forms, Sheets) on personal Gmail accounts without a Google Workspace subscription ($6-18/month) + Domain-Wide Delegation setup.

**The Two-Part Authentication Problem:**

| API Type | Service Account | OAuth Token | Winner |
|----------|----------------|-------------|---------|
| Google Cloud APIs (Vertex AI, Gemini, Cloud Storage) | ✅ Works perfectly | ✅ Works | Service Account (simpler) |
| Google Workspace APIs (Slides, Forms, Sheets, Drive) | ❌ Requires Workspace subscription | ✅ Works | OAuth Token (required) |

**Why This Matters:**
- PresGen uses **BOTH** types of APIs
- You need **BOTH** authentication methods
- The code already has OAuth fallback built-in!

**What You Already Have:**

1. **Service Account** (`presgen-service-account.json`)
   - Email: `presgen-service-account-test@presgen.iam.gserviceaccount.com`
   - Works for: Vertex AI image generation, Gemini API, Cloud Storage
   - Never expires

2. **OAuth Token** (`token.json`)
   - Works for: Creating Google Slides, Forms, Sheets, Drive files
   - Refreshes automatically (uses refresh token)
   - Already authenticated for your Google account

**Deployment Configuration:**

```bash
# .env file for AWS (RECOMMENDED - Dual Authentication)

# Service Account (for Vertex AI, Gemini, Cloud APIs)
GOOGLE_APPLICATION_CREDENTIALS=/secrets/google-creds.json

# OAuth Tokens (for Slides, Forms, Sheets, Drive)
OAUTH_TOKEN_PATH=/secrets/token.json
OAUTH_CLIENT_JSON=/secrets/oauth_slides_client.json

# Google Cloud Project
GOOGLE_CLOUD_PROJECT=presgen
GOOGLE_QUOTA_PROJECT=presgen

# ⚠️ IMPORTANT: Do NOT set FORCE_SERVICE_ACCOUNT=true
# This allows OAuth fallback for Workspace APIs
```

**Files to Deploy:**

```bash
# Create secrets directory
mkdir -p secrets

# Copy all auth files
cp presgen-service-account.json secrets/google-creds.json
cp token.json secrets/token.json
cp config/google_slides_credentials.json secrets/oauth_slides_client.json

# Verify
ls -lh secrets/
# Should show all three files
```

**How the Code Works:**

The authentication flow in [src/agent/slides_google.py:44-78](../src/agent/slides_google.py):

1. **Try service account first** (if GOOGLE_APPLICATION_CREDENTIALS set)
   - If successful → Use for all APIs (works for Cloud APIs only)
   - If fails or not available → Fall back to step 2

2. **Fall back to OAuth** (if OAUTH_TOKEN_PATH set)
   - Loads token.json
   - Automatically refreshes if expired
   - Works for ALL APIs including Workspace

**Risks & Mitigation:**

| Risk | Impact | Mitigation |
|------|--------|------------|
| OAuth token expires | Can't create Slides/Forms | Tokens auto-refresh using refresh token |
| Refresh token expires | Manual re-auth needed | Expires after ~6 months of no use; regenerate before demo |
| Service account key compromised | Unauthorized API access | Rotate keys every 90 days, monitor API usage |
| Secrets exposed in logs | Security breach | Filter logs to remove token/key patterns |

**Testing Strategy:**

```bash
# Test 1: Service Account (Cloud APIs)
docker exec presgen-core python3 << 'EOF'
from google.oauth2.service_account import Credentials
creds = Credentials.from_service_account_file(
    '/secrets/google-creds.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
print(f"✅ Service Account: {creds.service_account_email}")
EOF

# Test 2: OAuth (Workspace APIs)
docker exec presgen-core python3 << 'EOF'
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

creds = Credentials.from_authorized_user_file(
    '/secrets/token.json',
    scopes=['https://www.googleapis.com/auth/presentations']
)
service = build('slides', 'v1', credentials=creds)
pres = service.presentations().create(body={'title': 'Test'}).execute()
print(f"✅ Created test presentation: {pres['presentationId']}")

# Clean up
drive = build('drive', 'v3', credentials=creds)
drive.files().delete(fileId=pres['presentationId']).execute()
print("✅ Test presentation deleted")
EOF
```

**Recommendations:**
- ✅ Use dual authentication (service account + OAuth)
- ✅ Deploy all three files (google-creds.json, token.json, oauth_slides_client.json)
- ✅ Do NOT set FORCE_SERVICE_ACCOUNT=true
- ✅ Test both auth methods after deployment
- ✅ Set up monitoring for auth failures in CloudWatch
- ✅ Rotate service account keys every 90 days

**Decision Required:**
- [ ] Accept dual authentication approach?
- [ ] Who will regenerate OAuth token if it expires?
- [ ] Budget for optional Google Workspace subscription ($6-18/month)?

**Cost Impact:**
- Service Account: Free
- OAuth Token: Free
- Google Cloud API usage: ~$0.40/demo (within free tier initially)
- Google Workspace subscription: $0 (not needed with OAuth approach)

**Documentation:**
- See [GOOGLE_AUTH_CONFIGURATION.md](GOOGLE_AUTH_CONFIGURATION.md) for detailed setup
- See [AWS_MIGRATION_PLAN.md - Google Cloud Authentication Setup](AWS_MIGRATION_PLAN.md#google-cloud-authentication-setup) for complete guide

---

#### 4. Database Scaling & Migration

**Q: What happens when SQLite can't handle concurrent users?**

**Current Limitations:**
- SQLite: **Single-writer** architecture
- Expected load: **3-10 concurrent demo users**
- Assessment workflow: **11 steps**, 30-90 seconds each
- Database writes: **Every workflow step** updates database

**When SQLite Breaks:**
- **Symptom**: "Database is locked" errors
- **Threshold**: ~5-10 concurrent assessments
- **Mitigation**: Queue system or PostgreSQL

**Migration Path:**

```python
# Option A: Quick fix - Add retry logic
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential())
async def save_workflow_step(session, workflow_id, step_data):
    # Automatic retry on database lock
    pass

# Option B: Migrate to PostgreSQL
# 1. Export SQLite data
# 2. Create PostgreSQL on AWS RDS or Lightsail Database ($15/month)
# 3. Import data
# 4. Change DATABASE_URL in .env
```

**Recommendations:**
- ✅ Start with SQLite + retry logic
- ✅ Monitor "database locked" errors in CloudWatch
- ✅ Prepare PostgreSQL migration script (use when needed)
- ✅ Budget $15-20/month if PostgreSQL becomes necessary

**Decision Required:**
- [ ] Accept SQLite limitations for demo (max 5 concurrent users)?
- [ ] Pre-migrate to PostgreSQL for safety?
- [ ] Set threshold: "If >X lock errors/day, migrate to PostgreSQL"?

---

#### 4. Large File Handling (Videos & Presentations)

**Q: What happens when a user generates a 200MB video?**

**File Size Analysis:**
- **Excel uploads**: 1-5MB (small)
- **Generated presentations** (PPTX): 5-20MB (medium)
- **Avatar videos**: 50-200MB+ (large) ← **PROBLEM**
- **Batch processing**: Multiple presentations in parallel

**Disk Space Calculation:**
- Lightsail 40GB SSD (included)
- Docker images: ~3GB
- Application code: ~500MB
- **Available for user data**: ~36GB
- **Max videos storable**: 180 videos @ 200MB = **36GB**

**What Breaks First:**
1. **Disk fills up** → Application crashes (can't write temp files)
2. **Upload times out** → nginx 100MB limit reached
3. **Memory exhausted** → Video processing on 2GB RAM instance

**Solutions:**

```yaml
# nginx.conf - Increase upload size
client_max_body_size 500M;
proxy_read_timeout 600;
proxy_send_timeout 600;

# Immediate S3 upload after generation
async def generate_video(file_path):
    video = await process_video(file_path)

    # Upload to S3 immediately
    s3_url = await upload_to_s3(video, bucket='presgen-videos')

    # Delete local file
    os.remove(video)

    return s3_url

# Cleanup cron job
# /etc/cron.daily/cleanup-presgen
find /home/ubuntu/presgen/data/temp -type f -mtime +1 -delete
find /home/ubuntu/presgen/data/uploads -type f -mtime +7 -delete
```

**Recommendations:**
- ✅ **Upload to S3 immediately** after generation (delete local copy)
- ✅ Set nginx limits: 500MB upload, 10 min timeout
- ✅ Daily cleanup cron for temp files
- ✅ Monitor disk usage with CloudWatch alarm (alert at 80%)
- ✅ Consider **disabling** MuseTalk avatar generation for demo (requires GPU + large files)

**Decision Required:**
- [ ] Enable video generation on Lightsail (slow, CPU-only)?
- [ ] Disable video generation for demo (show pre-generated examples)?
- [ ] Add EC2 GPU spot instance for video ($0.16/hour on-demand)?

---

#### 5. Google Cloud API Quotas & Costs

**Q: What happens if we hit Google Cloud quotas during demo?**

**Current Google Cloud Usage:**
- **Gemini API**: Text generation for presentations
- **Vertex AI Imagen**: AI-generated slide images
- **Google Slides API**: Presentation creation
- **Google Forms API**: Assessment form generation
- **Google Sheets API**: Data export
- **Cloud Storage**: Temporary file storage

**Quota Risks:**

| Service | Free Tier | Cost After | Risk |
|---------|----------|------------|------|
| Gemini API | 15 RPM | $0.35/1K tokens | Medium |
| Vertex AI Imagen | 50 images/month | $0.02/image | High (demo use) |
| Google Slides | 500 requests/day | Free (no billing) | Low |
| Google Forms | 500 requests/day | Free | Low |
| Cloud Storage | 5GB free | $0.02/GB | Low |

**Potential Issues:**
- **During AllCloud CTO demo**: 5 users generate 5 presentations each = **25 presentations**
- Each presentation: 10 slides × AI images = **250 images** → **Costs $5**
- Each assessment: 50 questions generated = **~50K tokens** → **Costs $1.75**

**Per-Demo Cost Estimate:**
- 5 users × 2 presentations = **$10** (AI images)
- 5 users × 1 assessment = **$8.75** (Gemini tokens)
- **Total per demo**: ~$20 in Google Cloud costs

**Solutions:**

```python
# config.py - Configurable AI image generation
USE_AI_IMAGES = os.getenv('USE_AI_IMAGES', 'false').lower() == 'true'
AI_IMAGE_QUOTA_PER_DAY = int(os.getenv('AI_IMAGE_QUOTA', '50'))

# Implement quota checking
async def generate_slide_image(prompt: str):
    if not USE_AI_IMAGES:
        return get_placeholder_image()

    current_usage = await get_daily_image_count()
    if current_usage >= AI_IMAGE_QUOTA_PER_DAY:
        logger.warning("Daily AI image quota exceeded, using placeholder")
        return get_placeholder_image()

    return await vertex_ai_image_gen(prompt)

# Set billing alerts in Google Cloud Console
# Alert when daily spend > $5
```

**Recommendations:**
- ✅ Set Google Cloud billing alert: **$10/day threshold**
- ✅ Make AI image generation **optional** (env var: `USE_AI_IMAGES=false`)
- ✅ Implement quota limits in code (50 images/day)
- ✅ Use placeholder images for demo if budget is tight
- ✅ Monitor costs daily during demo period

**Decision Required:**
- [ ] Budget $20-50 for Google Cloud during demo?
- [ ] Disable AI image generation (use placeholders)?
- [ ] Set strict quotas (50 requests/day)?

---

#### 6. Multi-Service Orchestration & Dependencies

**Q: What if one service fails? Does the whole app crash?**

**Service Dependencies:**

```
Frontend (Next.js)
  ↓ (depends on)
Assess API (FastAPI)
  ↓ (depends on)
Core API (FastAPI)
  ↓ (depends on)
External APIs (Google, OpenAI)
```

**Failure Scenarios:**

| Scenario | Impact | Mitigation |
|----------|--------|------------|
| Core API down | ❌ No presentations | Health check + auto-restart |
| Assess API down | ❌ No assessments | Health check + auto-restart |
| Frontend down | ❌ Entire UI broken | Health check + auto-restart |
| Google API quota exceeded | ⚠️ Partial functionality | Fallback to cached data |
| OpenAI API down | ⚠️ No AI questions | Use pre-generated templates |
| Database locked | ⚠️ Workflow fails | Retry logic |
| S3 upload fails | ⚠️ File lost | Local fallback + retry |

**Resilience Strategies:**

```yaml
# docker-compose.yml - Health checks and dependencies
services:
  presgen-core:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    restart: unless-stopped

  presgen-assess:
    depends_on:
      presgen-core:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    restart: unless-stopped

  presgen-ui:
    depends_on:
      presgen-assess:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "wget", "--spider", "http://localhost:3000"]
    restart: unless-stopped
```

```python
# Graceful degradation example
async def generate_assessment(certification_id: str):
    try:
        # Primary: Use OpenAI GPT-4
        questions = await openai_generate_questions(certification_id)
    except openai.RateLimitError:
        logger.warning("OpenAI rate limit, using Gemini fallback")
        questions = await gemini_generate_questions(certification_id)
    except Exception as e:
        logger.error(f"AI generation failed: {e}, using template")
        questions = get_template_questions(certification_id)

    return questions
```

**Recommendations:**
- ✅ Implement health check endpoints for ALL services
- ✅ Use `restart: unless-stopped` in docker-compose
- ✅ Add fallback logic for external API failures
- ✅ Implement circuit breaker pattern for expensive APIs
- ✅ Set up CloudWatch alarms for service failures

**Decision Required:**
- [ ] Accept reduced functionality if APIs fail?
- [ ] Pre-cache fallback data for all modules?
- [ ] Set up automated failover to backup instances?

---

#### 7. Performance Under Load

**Q: Can the 2GB Lightsail instance handle 5 concurrent demo users?**

**Memory Analysis:**

| Service | Base Memory | Peak Memory (per user) |
|---------|-------------|------------------------|
| nginx | 50MB | +5MB/user |
| presgen-core | 300MB | +100MB/request |
| presgen-assess | 300MB | +50MB/request |
| presgen-ui | 200MB | +20MB/user |
| PostgreSQL (if used) | 200MB | +30MB |
| **TOTAL** | **1050MB** | **+175MB/user** |

**Concurrent User Calculation:**
- Available memory: 2GB = 2048MB
- System reserved: 200MB
- Base services: 1050MB
- **Available for users**: 798MB
- **Max concurrent users**: 798MB / 175MB = **~4.5 users**

**CPU Analysis:**
- 2 vCPU (Lightsail medium instance)
- AI image generation: **CPU-intensive** (15-30 sec/image)
- Video processing: **VERY CPU-intensive** (3-5 min/video on CPU)
- Assessment generation: **Network-bound** (API calls)

**Load Test Recommendations:**

```bash
# Install locust for load testing
pip install locust

# locustfile.py
from locust import HttpUser, task, between

class PresGenUser(HttpUser):
    wait_time = between(5, 15)

    @task(3)
    def generate_presentation(self):
        self.client.post("/api/presentations", json={
            "title": "Demo Presentation",
            "slides": 10
        })

    @task(1)
    def generate_assessment(self):
        self.client.post("/api/v1/workflows", json={
            "certification_id": "test-cert-123"
        })

# Run load test
locust -f locustfile.py --host http://YOUR_LIGHTSAIL_IP \
  --users 5 --spawn-rate 1 --run-time 5m
```

**Recommendations:**
- ✅ Run load test BEFORE demo day
- ✅ Set memory limits in docker-compose (prevent OOM killer)
- ✅ Add swap space (2GB) as safety buffer
- ✅ Disable video generation for demo (too CPU-intensive)
- ✅ Consider upgrading to 4GB instance ($20/month) if performance issues

**Decision Required:**
- [ ] Run load test to validate 5-user capacity?
- [ ] Upgrade to 4GB instance for safety ($20/month)?
- [ ] Limit concurrent users via application logic?

---

#### 8. Logging, Monitoring & Debugging

**Q: How do we debug issues during the live demo?**

**Current Logging:**
- FastAPI: uvicorn logs (JSON format)
- Next.js: console.log (browser + server)
- Docker: container stdout/stderr

**Production Logging Strategy:**

```python
# logger.py - Structured logging
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'service': 'presgen-assess',
            'message': record.getMessage(),
            'pathname': record.pathname,
            'lineno': record.lineno,
        }
        if hasattr(record, 'user_id'):
            log_obj['user_id'] = record.user_id
        if hasattr(record, 'workflow_id'):
            log_obj['workflow_id'] = record.workflow_id

        return json.dumps(log_obj)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/var/log/presgen/assess.log')
    ]
)
logging.getLogger().handlers[0].setFormatter(JSONFormatter())
```

**Monitoring Dashboard:**

```bash
# Real-time monitoring script
#!/bin/bash
# /home/ubuntu/presgen/scripts/monitor.sh

while true; do
  clear
  echo "=== PresGen Health Dashboard ==="
  echo "Time: $(date)"
  echo ""

  # Service status
  echo "Services:"
  docker-compose ps
  echo ""

  # Resource usage
  echo "Resources:"
  free -h | grep -E "Mem:|Swap:"
  df -h | grep -E "/dev/root"
  docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
  echo ""

  # Recent errors
  echo "Recent Errors (last 5 min):"
  docker-compose logs --since=5m | grep -i error | tail -10
  echo ""

  # Active workflows
  echo "Active Workflows:"
  curl -s http://localhost:8000/api/v1/workflows?status=running | jq -r '.[] | "\(.id) - \(.current_step)"'

  sleep 30
done
```

**Recommendations:**
- ✅ Send logs to CloudWatch Logs ($0.50/GB ingested)
- ✅ Create real-time monitoring dashboard (local script)
- ✅ Set up error rate alarms (>10 errors/min)
- ✅ Implement request tracing (track user journey)
- ✅ Add debug mode (enable with env var: `DEBUG=true`)

**Decision Required:**
- [ ] Send logs to CloudWatch ($2-5/month) or keep local?
- [ ] Set up real-time monitoring dashboard?
- [ ] Define "critical errors" that trigger SMS alerts?

---

#### 9. Security & Access Control

**Q: Who can access the application? How do we prevent unauthorized use?**

**Current Security:**
- **Planned**: HTTP Basic Auth (nginx)
- **Database**: No authentication (SQLite file)
- **API**: No authentication (open endpoints)
- **SSH**: Key-based authentication to Lightsail

**Security Gaps:**

| Layer | Current State | Risk | Mitigation |
|-------|--------------|------|------------|
| Application | No auth | ❌ **CRITICAL** | Add Basic Auth |
| API endpoints | Public | ⚠️ High | JWT tokens or API keys |
| Database | File-based | ⚠️ Medium | PostgreSQL with password |
| File uploads | No virus scan | ⚠️ Medium | ClamAV scanning |
| Secrets | .env file | ⚠️ Medium | AWS Secrets Manager |
| Network | Public IP | ⚠️ Medium | Firewall rules |

**Recommended Security Layers:**

```nginx
# 1. nginx Basic Auth (IMMEDIATE)
location / {
    auth_basic "PresGen Demo Access";
    auth_basic_user_file /etc/nginx/auth/.htpasswd;
    proxy_pass http://frontend:3000;
}

# 2. IP Whitelist (OPTIONAL - for extra security)
location / {
    # AllCloud office IP
    allow 1.2.3.4;
    # Your home IP
    allow 5.6.7.8;
    # CTO's IP
    allow 9.10.11.12;
    deny all;

    auth_basic "PresGen Demo Access";
    ...
}
```

```python
# 3. API Key Authentication (RECOMMENDED)
from fastapi import Header, HTTPException

VALID_API_KEYS = {
    "presgen-demo-key-abc123": "Demo User",
    "presgen-cto-key-xyz789": "CTO Access"
}

async def verify_api_key(x_api_key: str = Header(None)):
    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return VALID_API_KEYS[x_api_key]

# Apply to routes
@app.post("/api/presentations", dependencies=[Depends(verify_api_key)])
async def create_presentation(data: PresentationRequest):
    ...
```

```bash
# 4. Firewall Rules (AWS Lightsail)
aws lightsail put-instance-public-ports \
  --instance-name presgen-demo \
  --port-infos '[
    {"fromPort":22,"toPort":22,"protocol":"tcp","cidrs":["YOUR_IP/32"]},
    {"fromPort":80,"toPort":80,"protocol":"tcp","cidrs":["0.0.0.0/0"]},
    {"fromPort":443,"toPort":443,"protocol":"tcp","cidrs":["0.0.0.0/0"]}
  ]'
```

**Recommendations:**
- ✅ **IMMEDIATE**: Implement HTTP Basic Auth (as in migration plan)
- ✅ **SHORT-TERM**: Add API key authentication for backend APIs
- ✅ **OPTIONAL**: IP whitelist (if CTO's office has static IP)
- ✅ **BEST PRACTICE**: Migrate to JWT-based authentication for production
- ✅ **COMPLIANCE**: Scan uploads for viruses (ClamAV)

**Decision Required:**
- [ ] Basic Auth only (simplest) or add API keys?
- [ ] IP whitelist (more secure) or public access?
- [ ] Budget for virus scanning ($0.50/month ClamAV on server)?

---

#### 10. Compliance, Privacy & Data Retention

**Q: What data are we collecting? How long do we keep it? Is it GDPR-compliant?**

**Data Being Stored:**

| Data Type | Storage Location | Contains PII? | Retention |
|-----------|-----------------|---------------|-----------|
| User uploads (Excel, docs) | S3 or local disk | ❓ Maybe | ❓ Undefined |
| Assessment responses | Database | ✅ Yes (names, emails) | ❓ Undefined |
| Generated presentations | S3 or local disk | ⚠️ Maybe (company data) | ❓ Undefined |
| Workflow execution logs | CloudWatch | ⚠️ Maybe | 30 days (default) |
| Access logs (nginx) | Local disk | ✅ Yes (IP addresses) | ❓ Undefined |
| Database backups | S3 | ✅ Yes (full data copy) | ❓ Undefined |

**GDPR Considerations:**
- **Right to erasure**: Can users delete their data?
- **Data minimization**: Are we collecting only necessary data?
- **Data retention**: How long do we keep demo data?
- **Cross-border transfer**: Data in US servers (AllCloud CTO in Israel?)

**Recommended Data Retention Policy:**

```yaml
# Data Retention Policy
demo_data:
  retention_days: 90  # Delete after 3 months
  apply_to:
    - uploads/
    - generated_presentations/
    - workflow_executions/

production_data:
  retention_days: 365  # Keep for 1 year
  apply_to:
    - assessment_results/
    - certification_profiles/
    - user_accounts/

logs:
  retention_days: 30  # CloudWatch default
  apply_to:
    - application_logs/
    - access_logs/
    - error_logs/

backups:
  retention_count: 7  # Keep last 7 snapshots
  frequency: daily
  apply_to:
    - instance_snapshots/
    - database_exports/
```

```python
# Automated cleanup script
# cleanup_old_data.py
from datetime import datetime, timedelta
import boto3
from sqlalchemy import select
from models import Workflow, Assessment

async def cleanup_old_data():
    """Delete data older than 90 days"""
    cutoff_date = datetime.utcnow() - timedelta(days=90)

    # Delete old workflows
    result = await session.execute(
        select(Workflow).where(Workflow.created_at < cutoff_date)
    )
    old_workflows = result.scalars().all()

    for workflow in old_workflows:
        logger.info(f"Deleting old workflow: {workflow.id}")
        await session.delete(workflow)

    await session.commit()

    # Delete S3 files
    s3 = boto3.client('s3')
    response = s3.list_objects_v2(Bucket='presgen-demo-files', Prefix='uploads/')
    for obj in response.get('Contents', []):
        if obj['LastModified'] < cutoff_date:
            s3.delete_object(Bucket='presgen-demo-files', Key=obj['Key'])
            logger.info(f"Deleted old S3 file: {obj['Key']}")

# Cron job
# 0 2 * * * /usr/bin/python3 /home/ubuntu/presgen/scripts/cleanup_old_data.py
```

**Recommendations:**
- ✅ Define data retention policy (90 days for demo, 365 for production)
- ✅ Implement automated cleanup script (runs daily at 2 AM)
- ✅ Add "Delete my data" feature in UI
- ✅ Log all data deletions for audit trail
- ✅ Add privacy policy page (simple, 1-page doc)

**Decision Required:**
- [ ] Data retention: 30, 60, or 90 days?
- [ ] GDPR compliance required? (If yes, needs legal review)
- [ ] Allow users to delete their own data?
- [ ] Where is data stored? (US, EU, or other region?)

---

## Summary of Critical Decisions

### MUST Decide Before Deployment

- [ ] **Database**: SQLite or PostgreSQL?
- [ ] **Secrets**: AWS Secrets Manager or environment variables?
- [ ] **Video Generation**: Enable (slow) or disable (demo-only)?
- [ ] **AI Images**: Enable (costly) or use placeholders?
- [ ] **Security**: Basic Auth only or add API keys?
- [ ] **Backup Strategy**: Daily snapshots ($2/month) or none?
- [ ] **Instance Size**: 2GB ($10/month) or 4GB ($20/month)?
- [ ] **Data Retention**: 30, 60, or 90 days?

### SHOULD Decide Soon

- [ ] **Monitoring**: CloudWatch Logs ($2-5/month) or local logs?
- [ ] **Load Testing**: Run before demo or skip?
- [ ] **Google Cloud Budget**: $20-50 or disable AI features?
- [ ] **IP Whitelist**: Public access or restricted IPs?
- [ ] **PostgreSQL Migration**: Pre-migrate or wait for issues?
- [ ] **Virus Scanning**: Add ClamAV ($0.50/month) or skip?

### OPTIONAL (Can Decide Later)

- [ ] **SSL/HTTPS**: Add Let's Encrypt or use HTTP for demo?
- [ ] **Domain Name**: Use custom domain or IP address?
- [ ] **Kubernetes**: Migrate to EKS later or stay on Lightsail?
- [ ] **Multi-Region**: Deploy to EU region for GDPR compliance?
- [ ] **CDN**: Add CloudFront for faster asset delivery?

---

## Next Sections

The following sections provide detailed implementation guides:

- **Dockerization**: Step-by-step containerization of all 3 services
- **Lightsail Deployment Scripts**: Automated deployment from zero to production
- **Maintenance Procedures**: Backup, restore, update, scale, monitor
- **Troubleshooting**: Common issues and solutions

Continue reading for complete technical implementation details.

---

## Cost Summary (All Decisions)

### Minimum Configuration
- Lightsail 2GB: $10/month
- S3 Storage (5GB): $0.15/month
- CloudWatch Alarms: $0.50/month
- **Total**: **$10.65/month**

### Recommended Configuration
- Lightsail 2GB: $10/month
- S3 Storage + Requests: $1/month
- Snapshots (weekly): $1.20/month
- CloudWatch Logs + Alarms: $3/month
- SNS (SMS): $0.50/month
- **Total**: **$15.70/month**

### Maximum Configuration (All Features)
- Lightsail 4GB: $20/month
- PostgreSQL Database (Lightsail): $15/month
- S3 Storage + Requests: $2/month
- Snapshots (daily): $2.40/month
- CloudWatch Logs + Alarms: $5/month
- SNS (Email + SMS): $1/month
- AWS Secrets Manager (5 secrets): $2/month
- EC2 GPU Spot (10 hrs/month): $1.60/month
- **Total**: **$49/month**

**Recommended for Demo**: $15-20/month (middle configuration)

---

*Continue to next sections for detailed implementation...*
