# AWS Migration Plan for Presgen Demo
## Cost-Optimized Deployment to AWS Lightsail

**Version:** 1.0  
**Date:** October 28, 2025  
**Prepared for:** AllCloud CTO Demo  
**Target Environment:** AWS Lightsail (medium_2_0: 2GB RAM, 2 vCPUs)  
**Estimated Monthly Cost:** $22-24
**Deployment Time:** 2-3 hours  

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Cost Analysis](#cost-analysis)
4. [Technical Limitations & Workarounds](#technical-limitations--workarounds)
5. [Security Implementation](#security-implementation)
6. [**Google Cloud Authentication Setup**](#google-cloud-authentication-setup) ⭐ **NEW**
7. [Configuration Changes Required](#configuration-changes-required)
8. [Pre-Migration Checklist](#pre-migration-checklist)
9. [Deployment Instructions](#deployment-instructions)
10. [Monitoring & Alerts Setup](#monitoring--alerts-setup)
11. [Post-Deployment Operations](#post-deployment-operations)
12. [Troubleshooting Guide](#troubleshooting-guide)
13. [Appendix: Alternative Deployment Options](#appendix-alternative-deployment-options)

---

## Executive Summary

### Recommendation: AWS Lightsail with Hybrid GPU Processing

**Why Lightsail?**

- ✅ **Predictable cost:** $20/month for medium_2_0 instance (2GB RAM, 2 vCPUs)
- ✅ **Fastest deployment:** 2-3 hours total
- ✅ **Predictable billing:** No surprise costs, all-inclusive pricing
- ✅ **Simple management:** Single instance, no VPC complexity
- ✅ **CTO-friendly:** Easy to understand architecture

### What This Plan Delivers

```
┌─────────────────────────────────────────────────────────┐
│         Lightsail medium_2_0 ($20/month)                │
│         2GB RAM, 2 vCPUs, 60GB SSD                      │
│                                                         │
│  ✅ Presgen Core (Text → Slides)                        │
│  ✅ Presgen Data (Excel → Charts)                       │
│  ✅ Presgen Assess (RAG Assessments + Courses)         │
│  ⚠️  Presgen Video (CPU-based, slower)                  │
│  ❌ Presgen Avatar (Requires GPU - see workaround)      │
│                                                         │
│  ✅ Service Account Auth (No OAuth needed)             │
│  ✅ SQLite Database (Simple, fast)                      │
│  ✅ HTTP Basic Auth Security                            │
│  ✅ Automated Backups (SQLite + Image cleanup)         │
│  ✅ Email & SMS Alerts                                  │
│  ✅ Cost Monitoring                                     │
└─────────────────────────────────────────────────────────┘
```

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Compute** | Lightsail medium_2_0 (2GB) | Best performance for workload |
| **Storage** | Local Disk (S3 optional) | Simple, sufficient for demo |
| **Security** | HTTP Basic Auth | Simple, effective for demo |
| **Authentication** | Service Account only | No OAuth needed (headless) |
| **GPU Workloads** | Hybrid (local/optional EC2) | Lightsail has no GPU |
| **Database** | SQLite on instance | Simple, fast, $0 cost |
| **Monitoring** | CloudWatch + SNS | Email + SMS alerts included |

---

## Architecture Overview

### Deployed Architecture

```
                    ┌─────────────────────────────────────┐
                    │         Internet Users              │
                    └──────────────┬──────────────────────┘
                                   │
                                   │ HTTPS (Basic Auth)
                                   │
                    ┌──────────────▼──────────────────────┐
                    │   AWS Lightsail Instance (1GB)      │
                    │   Static IP: 54.x.x.x               │
                    │   $5/month all-inclusive            │
                    │                                     │
                    │  ┌───────────────────────────────┐  │
                    │  │    Docker Compose Stack       │  │
                    │  │                               │  │
                    │  │  ┌─────────┐                 │  │
                    │  │  │  nginx  │ :80 (Basic Auth)│  │
                    │  │  └────┬────┘                 │  │
                    │  │       │                      │  │
                    │  │  ┌────▼──────┐  ┌─────────┐ │  │
                    │  │  │  Next.js  │  │ FastAPI │ │  │
                    │  │  │  :3000    │  │  :8000  │ │  │
                    │  │  └───────────┘  └────┬────┘ │  │
                    │  │                      │      │  │
                    │  │                 ┌────▼────┐ │  │
                    │  │                 │ SQLite  │ │  │
                    │  │                 │ /data/  │ │  │
                    │  │                 └─────────┘ │  │
                    │  └───────────────────────────────┘  │
                    │                                     │
                    │  Persistent Storage: 40GB SSD       │
                    │  Included Transfer: 2TB/month       │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │        S3 Bucket (Optional)         │
                    │        $0.50-2/month                │
                    │                                     │
                    │  ├── uploads/     (user files)      │
                    │  ├── outputs/     (generated files) │
                    │  └── videos/      (large files)     │
                    └─────────────────────────────────────┘

              ┌─────────────────────────────────────────┐
              │    CloudWatch + SNS Alerts              │
              │                                         │
              │  ├── Cost alerts > $10                  │
              │  ├── CPU usage > 80%                    │
              │  ├── Disk usage > 80%                   │
              │  └── Instance health checks             │
              │                                         │
              │  Notifications to:                      │
              │  📧 ymeirovich@gmail.com                │
              │  📱 +972527563792                        │
              └─────────────────────────────────────────┘
```

### GPU Processing Workaround

```
┌──────────────────────────────────────────────────────┐
│  Option A: Hybrid Setup (Recommended for Demo)      │
│                                                      │
│  Lightsail: API, Core, Data, Assess                 │
│  Local Mac: Video + Avatar processing (GPU)         │
│                                                      │
│  Demo approach:                                     │
│  - Show Core/Data modules working live              │
│  - Show pre-generated video examples                │
│  - Explain GPU module runs elsewhere                │
│                                                      │
│  Cost: $5/month                                      │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│  Option B: Add EC2 GPU Spot (If Needed)             │
│                                                      │
│  Lightsail: API, Core, Data, Assess                 │
│  EC2 g4dn.xlarge Spot: Video + Avatar (on-demand)   │
│                                                      │
│  Cost: $5/month + $0.16/hour when processing        │
│        = $5-10/month (depends on usage)              │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│  Option C: CPU-Only Video (Slower, No Avatar)       │
│                                                      │
│  All on Lightsail with CPU-based processing          │
│  - Video transcription: 3-5 min (vs 23 sec)         │
│  - Skip LivePortrait avatars for demo               │
│                                                      │
│  Cost: $5/month                                      │
└──────────────────────────────────────────────────────┘
```

---

## Cost Analysis

### Monthly Cost Breakdown

#### Lightsail medium_2_0 Instance - Recommended Configuration

| Component | Specification | Monthly Cost |
|-----------|--------------|--------------|
| **Compute** | 2GB RAM, 2 vCPU (medium_2_0) | $20.00 |
| **Storage** | 60GB SSD (included) | $0.00 |
| **Data Transfer** | 3TB outbound (included) | $0.00 |
| **Static IP** | 1 static IP (included) | $0.00 |
| **Snapshots** | Weekly backups, 4 × 15GB (optional) | $3.00 |
| **S3 Storage** | 3GB files (optional) | $0.07 |
| **S3 Requests** | 10K GET, 2K PUT (optional) | $0.06 |
| **CloudWatch** | 5 alarms | $0.50 |
| **SNS** | Email alerts | $0.50 |
| | |
| **TOTAL (minimal)** | | **$21.00/month** |
| **TOTAL (with backups/S3)** | | **$24.13/month** |

#### Cost Optimization Scenarios

| Scenario | Configuration | Monthly Cost |
|----------|--------------|--------------|
| **Minimal** | No backups, no S3, local storage only | $21.00 |
| **Recommended** | Weekly backups, local storage, full monitoring | $24.00 |
| **With S3** | Add S3 for backups | $24.13 |
| **24/7 Demo** | Same as recommended | $24.00 |
| **Stop When Idle** | Stopped 20 days/month | $3.60 |

### 3-Month Demo Period Total Costs

```
Scenario 1: Minimal Configuration (No backups, local storage)
├── Month 1: $21.00
├── Month 2: $21.00
└── Month 3: $21.00
    TOTAL: $63.00

Scenario 2: Recommended Configuration (Backups + monitoring)
├── Month 1: $24.00
├── Month 2: $24.00
└── Month 3: $24.00
    TOTAL: $72.00

Scenario 3: Stop When Not Demoing (10 hours/week)
├── Month 1: $3.60 (storage only + occasional compute)
├── Month 2: $3.60
└── Month 3: $3.60
    TOTAL: $10.80
```

### Cost Comparison: All AWS Options

| Option | Deploy Time | Monthly Cost | Best For |
|--------|-------------|--------------|----------|
| **Lightsail medium_2_0** ⭐ | **2-3 hrs** | **$21-24** | **Recommended: Simple + Reliable** |
| Lambda + EFS | 5-6 hrs | $0.37-2 | Absolute minimum cost (limited) |
| EC2 t4g.small Spot | 3-4 hrs | $6-8 | Cheapest compute (similar specs) |
| EC2 t3.small On-Demand | 3-4 hrs | $15-18 (24/7) | Flexible scaling |
| App Runner | 4-5 hrs | $10-15 | Serverless simplicity |

---

## Technical Limitations & Workarounds

### Lightsail Limitations

#### 1. No GPU Support

**Impact:** Cannot run LivePortrait avatar generation or GPU-accelerated video processing.

**Workarounds:**

**A. Hybrid Setup (Recommended for Demo)**
```bash
# Keep GPU workloads local or on separate EC2 instance
# Lightsail handles: API, database, frontend, CPU workloads
# Local/EC2 handles: GPU video processing, avatar generation

# Communication via API webhooks
# Lightsail → Local: Send processing request
# Local → Lightsail: Upload result to S3, callback when done
```

**B. CPU-Only Mode**
```python
# backend/config.py
GPU_ENABLED = os.getenv('GPU_ENABLED', 'false').lower() == 'true'

if not GPU_ENABLED:
    # Use CPU-based alternatives
    WHISPER_MODEL = "base"  # Smaller model
    SKIP_AVATAR_GENERATION = True
    VIDEO_PROCESSING_TIMEOUT = 300  # 5 minutes vs 23 seconds
```

**C. Pre-Generated Demos**
```bash
# For demo purposes, show pre-generated video/avatar examples
# Explain that production version uses GPU for speed
```

#### 2. Memory Constraints (1GB RAM)

**Impact:** Docker Compose with multiple services needs ~700-800MB.

**Workarounds:**

```yaml
# docker-compose.yml - Memory-optimized configuration
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    mem_limit: 50m
    mem_reservation: 30m

  api:
    build: ./backend
    mem_limit: 400m
    mem_reservation: 300m
    environment:
      - WORKERS=1  # Single worker to save memory
      - THREADS=2

  frontend:
    build: ./frontend
    mem_limit: 300m
    mem_reservation: 200m
    environment:
      - NODE_OPTIONS=--max-old-space-size=256
```

**Monitor memory usage:**
```bash
# Install on Lightsail instance
docker stats --no-stream

# Set up swap if needed
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

#### 3. Storage Limitations (40GB)

**Impact:** Large video files can fill disk quickly.

**Workarounds:**

**A. Use S3 for Large Files**
```python
# backend/storage.py
import boto3

s3 = boto3.client('s3')
BUCKET = 'presgen-demo-files'

def store_video(local_path, key):
    # Upload to S3
    s3.upload_file(local_path, BUCKET, key)
    
    # Delete local copy
    os.remove(local_path)
    
    # Return S3 URL
    return f"https://{BUCKET}.s3.amazonaws.com/{key}"
```

**B. Automatic Cleanup**
```bash
# Cron job to clean old temp files
0 2 * * * find /home/ubuntu/presgen/uploads -type f -mtime +7 -delete
0 2 * * * find /tmp -type f -mtime +1 -delete
```

**C. Monitor Disk Usage**
```bash
# Alert when disk > 80% full
df -h | grep -vE '^Filesystem|tmpfs|cdrom' | awk '{ print $5 " " $1 }' | while read output;
do
  usage=$(echo $output | awk '{ print $1}' | cut -d'%' -f1)
  if [ $usage -ge 80 ]; then
    echo "Disk usage alert: $output"
  fi
done
```

#### 4. No Auto-Scaling

**Impact:** Cannot handle traffic spikes automatically.

**Workarounds:**

**A. Manual Scaling**
```bash
# Upgrade to larger instance if needed
aws lightsail update-instance-bundle \
  --instance-name presgen-demo \
  --bundle-id micro_2_0  # 2GB RAM, $10/month
```

**B. Rate Limiting**
```python
# backend/middleware/rate_limit.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/presentations")
@limiter.limit("10/minute")
async def get_presentations():
    return {"presentations": []}
```

#### 5. No VPC/Private Networking

**Impact:** Cannot use VPC-only AWS services or private networking.

**Workarounds:**

```python
# Use public endpoints for AWS services
# S3 - public endpoint with IAM authentication
# RDS - public endpoint with security group restrictions (if needed later)
# All traffic encrypted via HTTPS

import boto3

# S3 via public endpoint
s3 = boto3.client(
    's3',
    region_name='us-east-1',
    endpoint_url='https://s3.amazonaws.com'  # Public endpoint
)

# Use IAM instance role for authentication (no keys in code)
```

### What Works Perfectly on Lightsail

✅ **Full Docker Support** - All containers run normally  
✅ **FastAPI Backend** - Excellent performance  
✅ **Next.js Frontend** - Fast and responsive  
✅ **SQLite Database** - Perfect for demo, handles 100+ concurrent users  
✅ **S3 Integration** - Works via public endpoints  
✅ **Core Module** - Text → Slides generation  
✅ **Data Module** - Excel → Charts  
✅ **Assess Module** - RAG assessments  
✅ **Basic Auth** - Full nginx support  
✅ **SSL/HTTPS** - Can add Let's Encrypt certificate  
✅ **CloudWatch Monitoring** - Full integration  
✅ **Snapshots** - Easy backup/restore  

---

## Security Implementation

### HTTP Basic Authentication with Nginx

**Why Basic Auth?**
- ✅ 5 minutes to implement
- ✅ No code changes required
- ✅ Works in all browsers
- ✅ Industry standard
- ✅ Easy to share credentials
- ✅ Perfect for 3-5 person demo

### Implementation Steps

#### 1. Generate Password File

```bash
# On Lightsail instance after deployment

# Install htpasswd utility
sudo apt-get update
sudo apt-get install -y apache2-utils

# Create password file
sudo mkdir -p /etc/nginx/auth
sudo htpasswd -c /etc/nginx/auth/.htpasswd demo_user
# Enter password when prompted: AllCloud2024!

# Add more users
sudo htpasswd /etc/nginx/auth/.htpasswd cto_user
# Password: CTODemo2024!

sudo htpasswd /etc/nginx/auth/.htpasswd yosi_user
# Password: YosiDemo2024!

# Verify users
cat /etc/nginx/auth/.htpasswd
```

#### 2. Configure Nginx

```nginx
# /etc/nginx/sites-available/presgen
server {
    listen 80;
    server_name _;

    # Enable Basic Authentication
    auth_basic "Presgen Demo - Authorized Personnel Only";
    auth_basic_user_file /etc/nginx/auth/.htpasswd;

    # Main application
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API endpoints
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        
        # Increase timeouts for file uploads
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
        
        # Increase max body size
        client_max_body_size 100M;
    }

    # Health check endpoint (no auth required for monitoring)
    location /health {
        auth_basic off;
        proxy_pass http://localhost:8000/health;
        access_log off;
    }

    # Static files (if serving from nginx)
    location /static/ {
        alias /home/ubuntu/presgen/static/;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }
}
```

#### 3. Apply Configuration

```bash
# Create symbolic link
sudo ln -sf /etc/nginx/sites-available/presgen /etc/nginx/sites-enabled/presgen

# Remove default site
sudo rm -f /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

### Demo Credentials

**Share these credentials with demo participants:**

```
═══════════════════════════════════════════════
         PRESGEN DEMO ACCESS CREDENTIALS
═══════════════════════════════════════════════

URL: http://54.x.x.x (will be provided after deployment)

Credentials:
┌──────────────────────────────────────────────┐
│ Username: demo_user                          │
│ Password: AllCloud2024!                      │
│ Purpose:  General demo access                │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│ Username: cto_user                           │
│ Password: CTODemo2024!                       │
│ Purpose:  CTO exclusive access               │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│ Username: yosi_user                          │
│ Password: YosiDemo2024!                      │
│ Purpose:  Yosi Frankel access                │
└──────────────────────────────────────────────┘

Notes:
- Browser will prompt for username/password on first visit
- Credentials cached in browser session
- Logout: Clear browser cache or use private/incognito mode

Support: ymeirovich@gmail.com
═══════════════════════════════════════════════
```

### Security Best Practices

```bash
# 1. Secure password file permissions
sudo chmod 644 /etc/nginx/auth/.htpasswd
sudo chown root:root /etc/nginx/auth/.htpasswd

# 2. Rotate passwords after demo (if needed)
sudo htpasswd /etc/nginx/auth/.htpasswd demo_user
# Enter new password

# 3. Remove user access
sudo htpasswd -D /etc/nginx/auth/.htpasswd old_user

# 4. Optional: Add IP whitelist for extra security
# Add to nginx config:
# allow 1.2.3.4;     # AllCloud office IP
# allow 5.6.7.8;     # Your IP
# deny all;

# 5. Monitor access logs
sudo tail -f /var/log/nginx/access.log | grep -i "401\|403"
```

### Alternative Security Options (If Needed Later)

#### Option: API Key Authentication

```python
# backend/middleware/api_key.py
from fastapi import Header, HTTPException

API_KEYS = {
    "presgen-demo-key-123": "Demo User",
    "presgen-cto-key-456": "CTO Access",
}

async def verify_api_key(x_api_key: str = Header(None)):
    if not x_api_key or x_api_key not in API_KEYS:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")
    return API_KEYS[x_api_key]

# Apply to routes
@app.get("/api/protected", dependencies=[Depends(verify_api_key)])
async def protected_route():
    return {"status": "authenticated"}
```

---

## Google Cloud Authentication Setup

### Critical: Understanding Google Cloud Authentication

**This section is ESSENTIAL for successful deployment.** PresGen uses two different Google Cloud authentication methods depending on which APIs are being accessed.

### Authentication Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    PresGen Authentication Flow                   │
└─────────────────────────────────────────────────────────────────┘

    ┌──────────────────────┐              ┌──────────────────────┐
    │  Google Cloud APIs   │              │ Google Workspace APIs │
    │  (Backend Services)  │              │  (Document Creation)  │
    │                      │              │                       │
    │  • Vertex AI         │              │  • Google Slides      │
    │  • Gemini API        │              │  • Google Forms       │
    │  • Cloud Storage     │              │  • Google Sheets      │
    │  • Cloud Vision      │              │  • Google Drive       │
    └──────────┬───────────┘              └──────────┬────────────┘
               │                                     │
               │ ✅ Service Account                  │ ✅ Service Account
               │    Works perfectly                  │    Works in headless!
               │                                     │
    ┌──────────▼─────────────────────────────────────▼────────────┐
    │                  PresGen Application                         │
    │                                                              │
    │  Authentication (Headless Deployment):                      │
    │  ✅ Service Account ONLY (FORCE_SERVICE_ACCOUNT=true)       │
    │  ❌ OAuth NOT needed (no browser for token refresh)         │
    └──────────────────────────────────────────────────────────────┘
```

### Service Account Authentication (Headless Deployment)

**IMPORTANT UPDATE:** Service Account authentication DOES work for Google Slides API in headless environments!

**Service Account for Headless Deployment:**

| Aspect | Details |
|--------|---------|
| **What it is** | "Robot" account for server applications |
| **Works with** | All Google APIs including Slides, Forms, Sheets, Drive |
| **Works headless?** | ✅ YES - Perfect for AWS deployment |
| **User consent** | Not required |
| **Token expiry** | Never expires (long-lived credentials) |
| **Setup complexity** | Simple (single JSON file) |
| **Best for** | Headless server deployments |

### Authentication Strategy (CORRECTED)

**Previous assumption (INCORRECT):** OAuth required for Slides API
**Reality (CORRECT):** Service Account works for Slides API in headless mode

**Investigation:** Code in `src/agent/slides_google.py:54-89` confirms Service Account authentication works for:

- `https://www.googleapis.com/auth/presentations` (Slides API)
- `https://www.googleapis.com/auth/drive.file` (Drive API)

**Deployment Strategy:** Service Account ONLY (no OAuth)

### What You Need

✅ **Service Account** (`presgen-service-account.json`)
- Email: `presgen-service-account-test@presgen.iam.gserviceaccount.com`
- Project: `presgen`
- Works for: All Google APIs (Vertex AI, Gemini, Slides, Forms, Sheets, Drive)

✅ **Code with Service Account Authentication** ([src/agent/slides_google.py:54-89](../src/agent/slides_google.py))
- Service Account authentication for all APIs
- No OAuth needed in headless mode
- Set `FORCE_SERVICE_ACCOUNT=true`

### Deployment Configuration (AWS Lightsail)

#### Service Account Only (RECOMMENDED for Headless)

Use Service Account authentication for all Google APIs - no OAuth needed.

**Configuration:**

```bash
# .env file for AWS deployment

# ============================================================================
# Google Cloud Authentication (Service Account Only)
# ============================================================================

# Service Account (for ALL Google APIs)
GOOGLE_APPLICATION_CREDENTIALS=/secrets/google-creds.json

# Force Service Account (no OAuth fallback)
FORCE_SERVICE_ACCOUNT=true

# Google Cloud Project
GOOGLE_CLOUD_PROJECT=presgen
GOOGLE_QUOTA_PROJECT=presgen
```

**Files to Deploy:**

```bash
# Local preparation
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs

# Create secrets directory
mkdir -p secrets

# Copy service account file
cp presgen-service-account.json secrets/google-creds.json

# Verify file exists
ls -lh secrets/
# Should show:
# google-creds.json (service account)
```

**No OAuth files needed:**

- ❌ token.json (not needed)
- ❌ oauth_slides_client.json (not needed)

### Deployment Steps

#### 1. Prepare Secrets Locally

```bash
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs

# Create secrets directory
mkdir -p secrets

# Copy service account file only
cp presgen-service-account.json secrets/google-creds.json

# Verify file
ls -lh secrets/
```

#### 2. Update .env File

```bash
# Edit .env file
nano .env

# Add/update these lines:
GOOGLE_APPLICATION_CREDENTIALS=/secrets/google-creds.json
FORCE_SERVICE_ACCOUNT=true
GOOGLE_CLOUD_PROJECT=presgen
GOOGLE_QUOTA_PROJECT=presgen

# Save and close (Ctrl+X, Y, Enter)
```

#### 3. Deploy to AWS (Automatic Upload)

The deployment script will automatically upload secrets:

```bash
# Run deployment
./deployment/deploy-to-lightsail.sh presgen-demo small_2_0

# Script will:
# 1. Create secrets/ directory on server
# 2. Upload all files from local secrets/ to /home/ubuntu/presgen/secrets/
# 3. Set correct permissions (chmod 600 for security)
# 4. Configure environment variables in docker-compose.yml
# 5. Mount secrets volume in containers
```

#### 4. Verify on Server

```bash
# SSH into server
ssh -i lightsail-key.pem ubuntu@YOUR_STATIC_IP

# Check secrets uploaded
ls -lh /home/ubuntu/presgen/secrets/
# Should show:
# -rw------- 1 ubuntu ubuntu google-creds.json
# -rw------- 1 ubuntu ubuntu token.json
# -rw------- 1 ubuntu ubuntu oauth_slides_client.json

# Check environment variables
docker exec presgen-core env | grep GOOGLE
# Should show:
# GOOGLE_APPLICATION_CREDENTIALS=/secrets/google-creds.json
# OAUTH_TOKEN_PATH=/secrets/token.json
# OAUTH_CLIENT_JSON=/secrets/oauth_slides_client.json
# GOOGLE_CLOUD_PROJECT=presgen
```

### Testing Authentication

#### Test 1: Service Account (Cloud APIs)

```bash
# SSH into server
ssh -i lightsail-key.pem ubuntu@YOUR_STATIC_IP

# Test service account authentication
docker exec presgen-core python3 << 'EOF'
import os
from google.oauth2.service_account import Credentials

creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
creds = Credentials.from_service_account_file(
    creds_path,
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)

print(f"✅ Service Account: {creds.service_account_email}")
print(f"✅ Project ID: {creds.project_id}")
print("✅ Service account authentication working!")
EOF
```

**Expected Output:**
```
✅ Service Account: presgen-service-account-test@presgen.iam.gserviceaccount.com
✅ Project ID: presgen
✅ Service account authentication working!
```

#### Test 2: OAuth (Workspace APIs)

```bash
# Test OAuth authentication
docker exec presgen-core python3 << 'EOF'
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

token_path = os.getenv('OAUTH_TOKEN_PATH')
creds = Credentials.from_authorized_user_file(
    token_path,
    scopes=['https://www.googleapis.com/auth/presentations']
)

# Test by creating a test presentation
service = build('slides', 'v1', credentials=creds)
presentation = service.presentations().create(body={'title': 'Test'}).execute()
presentation_id = presentation['presentationId']

print(f"✅ OAuth authentication working!")
print(f"✅ Created test presentation: {presentation_id}")
print(f"✅ URL: https://docs.google.com/presentation/d/{presentation_id}/edit")

# Clean up
drive_service = build('drive', 'v3', credentials=creds)
drive_service.files().delete(fileId=presentation_id).execute()
print("✅ Test presentation deleted")
EOF
```

**Expected Output:**
```
✅ OAuth authentication working!
✅ Created test presentation: 1a2b3c4d5e6f7g8h9i0j
✅ URL: https://docs.google.com/presentation/d/1a2b3c4d5e6f7g8h9i0j/edit
✅ Test presentation deleted
```

#### Test 3: Full Application Test

```bash
# Test through API endpoint
curl -X POST http://localhost:8080/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "AI in Healthcare",
    "slides": 5
  }'

# Check logs for authentication messages
docker logs presgen-core --tail 50 | grep -i "auth\|credential\|token"
```

**What to Look For:**
```
✅ Successfully authenticated with service account
✅ Using Service Account for Slides API
✅ Presentation created: https://docs.google.com/presentation/d/...
```

### Required Google Cloud APIs

**Enable these APIs in Google Cloud Console:**

```bash
# Visit: https://console.cloud.google.com/apis/library

# Enable these APIs:
1. Google Slides API          ✅ slides.googleapis.com
2. Google Drive API           ✅ drive.googleapis.com
3. Google Forms API           ✅ forms.googleapis.com
4. Google Sheets API          ✅ sheets.googleapis.com
5. Vertex AI API              ✅ aiplatform.googleapis.com
6. Cloud Vision API           ✅ vision.googleapis.com
7. Cloud Storage API          ✅ storage.googleapis.com
```

**Quick Enable Command:**

```bash
# Enable all required APIs at once
gcloud services enable \
  slides.googleapis.com \
  drive.googleapis.com \
  forms.googleapis.com \
  sheets.googleapis.com \
  aiplatform.googleapis.com \
  vision.googleapis.com \
  storage.googleapis.com \
  --project=presgen
```

### Permissions & Access

#### Service Account Permissions

Your service account has **Owner** role, which includes all necessary permissions:

```bash
# Check permissions
gcloud projects get-iam-policy presgen \
  --flatten="bindings[].members" \
  --filter="bindings.members:presgen-service-account-test@presgen.iam.gserviceaccount.com"
```

**Required Roles:**
- ✅ `roles/owner` (you have this)
- ✅ `roles/aiplatform.user` (included in owner)
- ✅ `roles/storage.objectAdmin` (included in owner)

#### Service Account Scopes

Service Account authentication works with these scopes:

```python
# Scopes for Service Account
SCOPES = [
    'https://www.googleapis.com/auth/presentations',      # Create/edit slides
    'https://www.googleapis.com/auth/drive.file',        # Create Drive files
    'https://www.googleapis.com/auth/forms',             # Create forms
    'https://www.googleapis.com/auth/spreadsheets',      # Create sheets
]
```

**Note:** These scopes work with Service Account in headless environments.

### Troubleshooting

#### Issue 1: "Service account file not found"

**Error:**
```
FileNotFoundError: [Errno 2] No such file or directory: '/secrets/google-creds.json'
```

**Solution:**
```bash
# Check if file exists on server
ssh -i lightsail-key.pem ubuntu@YOUR_STATIC_IP
ls -lh /home/ubuntu/presgen/secrets/google-creds.json

# If missing, upload manually
scp -i lightsail-key.pem secrets/google-creds.json \
    ubuntu@YOUR_STATIC_IP:/home/ubuntu/presgen/secrets/

# Set correct permissions
ssh -i lightsail-key.pem ubuntu@YOUR_STATIC_IP
chmod 600 /home/ubuntu/presgen/secrets/google-creds.json

# Restart containers
docker-compose restart presgen-core
```

#### Issue 2: "403 Permission Denied" for Slides API

**Error:**
```
HttpError 403: The caller does not have permission
```

**Diagnosis:**
```bash
# Check authentication environment variable
docker exec presgen-core env | grep FORCE_SERVICE_ACCOUNT
# Should show "true" for headless deployment
```

**Solution:**
```bash
# Verify Service Account file exists
docker exec presgen-core ls -lh /secrets/google-creds.json

# Verify FORCE_SERVICE_ACCOUNT is set
ssh -i lightsail-key.pem ubuntu@YOUR_STATIC_IP
cd /home/ubuntu/presgen
nano .env
# Should have: FORCE_SERVICE_ACCOUNT=true
# Save and exit

# Rebuild and restart
docker-compose down
docker-compose up -d --build
```

#### Issue 3: "API not enabled"

**Error:**
```
HttpError 403: Google Slides API has not been used in project presgen before
```

**Solution:**
```bash
# Enable the API
gcloud services enable slides.googleapis.com --project=presgen

# Or enable via Cloud Console:
# 1. Visit: https://console.cloud.google.com/apis/library/slides.googleapis.com
# 2. Click "Enable"
# 3. Wait 1-2 minutes for propagation
```

#### Issue 4: Container can't read secrets

**Error:**
```
PermissionError: [Errno 13] Permission denied: '/secrets/google-creds.json'
```

**Solution:**
```bash
# Fix permissions on server
ssh -i lightsail-key.pem ubuntu@YOUR_STATIC_IP

# Set correct ownership and permissions
sudo chown -R ubuntu:ubuntu /home/ubuntu/presgen/secrets
chmod 600 /home/ubuntu/presgen/secrets/*

# Verify
ls -lh /home/ubuntu/presgen/secrets/
# Should show: -rw------- ubuntu ubuntu

# Restart containers
docker-compose restart
```

### Security Best Practices

#### 1. Secrets File Permissions

```bash
# On server
chmod 600 /home/ubuntu/presgen/secrets/*.json
chown ubuntu:ubuntu /home/ubuntu/presgen/secrets/*.json

# Verify
ls -lh /home/ubuntu/presgen/secrets/
# Should show: -rw------- 1 ubuntu ubuntu
```

#### 2. Never Commit Secrets

```bash
# Verify .gitignore includes:
cat .gitignore | grep -E "secrets|token.json|*-service-account.json"

# Should show:
# secrets/
# token.json
# *-service-account.json
# *.pem
```

#### 3. Rotate Service Account Keys

```bash
# Every 90 days, create new service account key

# 1. Create new key
gcloud iam service-accounts keys create new-key.json \
  --iam-account=presgen-service-account-test@presgen.iam.gserviceaccount.com

# 2. Test new key locally
export GOOGLE_APPLICATION_CREDENTIALS=new-key.json
python3 scripts/test-google-auth.py

# 3. Upload to server
scp -i lightsail-key.pem new-key.json ubuntu@YOUR_STATIC_IP:/home/ubuntu/presgen/secrets/google-creds.json

# 4. Restart services
ssh -i lightsail-key.pem ubuntu@YOUR_STATIC_IP
docker-compose restart

# 5. Delete old key from Google Cloud
gcloud iam service-accounts keys list \
  --iam-account=presgen-service-account-test@presgen.iam.gserviceaccount.com
# Note the old key ID
gcloud iam service-accounts keys delete OLD_KEY_ID \
  --iam-account=presgen-service-account-test@presgen.iam.gserviceaccount.com
```

#### 4. Monitor API Usage

```bash
# Check API quota usage
gcloud services quota list \
  --service=slides.googleapis.com \
  --consumer="project:presgen" \
  --filter="metric.type:slides.googleapis.com/quota/read/requests"

# Set up billing alerts
gcloud billing budgets create \
  --billing-account=YOUR_BILLING_ACCOUNT_ID \
  --display-name="PresGen API Budget" \
  --budget-amount=20 \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=90
```

### Checklist: Google Cloud Auth Ready

Before deploying, verify:

- [ ] `secrets/google-creds.json` exists locally (service account)
- [ ] `.env` has `GOOGLE_APPLICATION_CREDENTIALS=/secrets/google-creds.json`
- [ ] `.env` has `FORCE_SERVICE_ACCOUNT=true` (for headless deployment)
- [ ] All Google APIs enabled in Cloud Console (Slides, Drive, Forms, Sheets, Vertex AI)
- [ ] Service account has Owner role in project `presgen`
- [ ] Project billing is enabled
- [ ] `.gitignore` includes `secrets/` directory

**No OAuth files needed for headless deployment:**

- ❌ `secrets/token.json` (not needed)
- ❌ `secrets/oauth_slides_client.json` (not needed)

If all checked, you're ready for deployment! 🚀

### Cost Impact

**Google Cloud API Costs (Free Tier):**

| API | Free Tier | Cost After | Demo Usage | Estimated Cost |
|-----|-----------|------------|------------|----------------|
| Google Slides | 100 requests/100 sec | $0 | ~50 requests/demo | $0 |
| Google Drive | 1,000 requests/100 sec | $0 | ~20 requests/demo | $0 |
| Vertex AI (Gemini) | First 1M tokens | $0.002/1K tokens | ~100K tokens/demo | $0.20 |
| Vertex AI (Imagen) | First 100 images | $0.02/image | ~10 images/demo | $0.20 |

**Total Google Cloud Cost: ~$0.40 per demo** (within free tier for first few demos)

**Google Workspace Subscription:**

- NOT needed - Service Account works without subscription
- Cost savings: $6-18/month per user

---

## Configuration Changes Required

### Summary of Changes

✅ **Minimal changes required** - Most code runs as-is  
⚠️ **Environment variables** - Update for AWS  
⚠️ **Memory limits** - Add to docker-compose  
✅ **Storage** - Optional S3 integration  

### 1. Frontend Configuration

#### Update `frontend/.env.production`

```bash
# Before (local development)
NEXT_PUBLIC_API_URL=http://localhost:8000

# After (Lightsail deployment)
NEXT_PUBLIC_API_URL=http://54.x.x.x/api

# Or use relative URL (recommended)
NEXT_PUBLIC_API_URL=/api
```

#### Update `frontend/next.config.js`

```javascript
/** @type {import('next').NextConfig} */
module.exports = {
  // Output standalone for Docker
  output: 'standalone',
  
  // Environment variables
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || '/api',
  },
  
  // Production optimizations
  compress: true,
  poweredByHeader: false,
  
  // Image optimization
  images: {
    domains: ['presgen-demo-files.s3.amazonaws.com'],
  },
  
  // Disable source maps in production (smaller build)
  productionBrowserSourceMaps: false,
}
```

### 2. Backend Configuration

#### Update `backend/.env.production`

```bash
# Environment
ENVIRONMENT=production
DEBUG=false

# Database (SQLite for demo)
DATABASE_URL=sqlite:////data/presgen.db

# Storage Configuration
STORAGE_PROVIDER=s3  # or 'local' for demo
AWS_REGION=us-east-1
S3_BUCKET=presgen-demo-files

# API Keys (load from environment)
OPENAI_API_KEY=${OPENAI_API_KEY}
GOOGLE_APPLICATION_CREDENTIALS=/secrets/google-creds.json

# Google Workspace
GOOGLE_SLIDES_ENABLED=true
GOOGLE_FORMS_ENABLED=true

# GPU Settings (disabled on Lightsail)
GPU_ENABLED=false
WHISPER_MODEL=base  # Smaller model for CPU
SKIP_AVATAR_GENERATION=true

# Performance
WORKERS=1  # Single worker for 1GB RAM
THREADS=2
MAX_UPLOAD_SIZE=104857600  # 100MB

# Security
CORS_ORIGINS=http://54.x.x.x,https://your-domain.com
ALLOWED_HOSTS=*
```

#### Update `backend/config.py` (Add S3 Support)

```python
# backend/config.py
import os
import boto3
from typing import Optional

# Environment
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
DEBUG = ENVIRONMENT != 'production'

# Database
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./presgen.db')

# Storage
STORAGE_PROVIDER = os.getenv('STORAGE_PROVIDER', 'local')
S3_BUCKET = os.getenv('S3_BUCKET')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')

# Initialize S3 client if using S3
s3_client: Optional[boto3.client] = None
if STORAGE_PROVIDER == 's3':
    s3_client = boto3.client('s3', region_name=AWS_REGION)

# Storage functions
def get_upload_path(filename: str) -> str:
    """Get path for uploaded file"""
    if STORAGE_PROVIDER == 'local':
        return f"/data/uploads/{filename}"
    else:
        return f"uploads/{filename}"

def get_output_path(filename: str) -> str:
    """Get path for generated output"""
    if STORAGE_PROVIDER == 'local':
        return f"/data/outputs/{filename}"
    else:
        return f"outputs/{filename}"

def store_file(local_path: str, key: str) -> str:
    """Store file and return URL"""
    if STORAGE_PROVIDER == 'local':
        return local_path
    
    # Upload to S3
    s3_client.upload_file(local_path, S3_BUCKET, key)
    
    # Return public URL
    return f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{key}"

def retrieve_file(key: str, local_path: str) -> str:
    """Retrieve file from storage"""
    if STORAGE_PROVIDER == 'local':
        return key  # Already local
    
    # Download from S3
    s3_client.download_file(S3_BUCKET, key, local_path)
    return local_path

# GPU Settings
GPU_ENABLED = os.getenv('GPU_ENABLED', 'false').lower() == 'true'
SKIP_AVATAR_GENERATION = not GPU_ENABLED

# Performance
MAX_WORKERS = int(os.getenv('WORKERS', '1'))
THREAD_COUNT = int(os.getenv('THREADS', '2'))
```

### 3. Docker Compose Configuration

#### Update `docker-compose.yml` (Memory Optimized)

```yaml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    container_name: presgen-nginx
    restart: unless-stopped
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - /etc/nginx/auth/.htpasswd:/etc/nginx/auth/.htpasswd:ro
    depends_on:
      - api
      - frontend
    mem_limit: 50m
    mem_reservation: 30m
    networks:
      - presgen-network

  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: presgen-api
    restart: unless-stopped
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=sqlite:////data/presgen.db
      - STORAGE_PROVIDER=${STORAGE_PROVIDER:-local}
      - AWS_REGION=${AWS_REGION:-us-east-1}
      - S3_BUCKET=${S3_BUCKET}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - GPU_ENABLED=false
      - WORKERS=1
      - THREADS=2
    volumes:
      - ./data:/data
      - ./secrets:/secrets:ro
    mem_limit: 400m
    mem_reservation: 300m
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - presgen-network

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        - NEXT_PUBLIC_API_URL=/api
    container_name: presgen-frontend
    restart: unless-stopped
    environment:
      - NODE_ENV=production
      - NODE_OPTIONS=--max-old-space-size=256
    mem_limit: 300m
    mem_reservation: 200m
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:3000"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - presgen-network

volumes:
  data:
    driver: local

networks:
  presgen-network:
    driver: bridge
```

### 4. Nginx Configuration

#### Create `nginx.conf`

```nginx
events {
    worker_connections 512;  # Reduced for low memory
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log warn;

    # Performance
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 100M;
    client_body_buffer_size 1M;

    # Compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript 
               application/json application/javascript application/xml+rss;

    # Upstream services
    upstream frontend {
        server frontend:3000;
    }

    upstream api {
        server api:8000;
    }

    server {
        listen 80;
        server_name _;

        # Basic Authentication
        auth_basic "Presgen Demo - Authorized Access Only";
        auth_basic_user_file /etc/nginx/auth/.htpasswd;

        # Frontend
        location / {
            proxy_pass http://frontend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_cache_bypass $http_upgrade;
        }

        # API
        location /api/ {
            proxy_pass http://api/;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Timeouts for long-running requests
            proxy_connect_timeout 300s;
            proxy_send_timeout 300s;
            proxy_read_timeout 300s;
        }

        # Health check (no auth)
        location /health {
            auth_basic off;
            proxy_pass http://api/health;
            access_log off;
        }

        # Static files (if needed)
        location /static/ {
            auth_basic off;
            alias /data/static/;
            expires 7d;
            add_header Cache-Control "public, immutable";
        }
    }
}
```

### 5. Dockerfile Updates

#### Backend Dockerfile

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 presgen && \
    chown -R presgen:presgen /app
USER presgen

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "src.service.http:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

#### Frontend Dockerfile

```dockerfile
# frontend/Dockerfile
FROM node:18-alpine AS builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy source
COPY . .

# Build application
ARG NEXT_PUBLIC_API_URL=/api
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
RUN npm run build

# Production image
FROM node:18-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

# Create non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy built application
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
```

---

## Pre-Migration Checklist

### 1. AWS Account Setup

```bash
□ Access to AWS sandbox account
□ AWS CLI installed locally
□ AWS credentials configured

# Install AWS CLI (if not installed)
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Configure credentials
aws configure
# AWS Access Key ID: [PROVIDED BY CTO]
# AWS Secret Access Key: [PROVIDED BY CTO]
# Default region: us-east-1
# Default output format: json

# Verify access
aws sts get-caller-identity
```

### 2. Application Prerequisites

```bash
□ Application code in Git repository
□ .env files created (.env.production)
□ API keys available (OpenAI, Google)
□ Docker and Docker Compose tested locally
□ All modules tested end-to-end

# Test locally first
cd presgen
docker-compose up -d
curl http://localhost/health

# Verify all modules work
# - Core: Text → Slides
# - Data: Excel → Charts
# - Assess: Create assessment

# Stop local instance
docker-compose down
```

### 3. AWS Resources Required

```bash
□ S3 bucket name decided: presgen-demo-files-[TIMESTAMP]
□ SNS topic for alerts
□ Email confirmed: ymeirovich@gmail.com
□ Phone confirmed: +972527563792
□ Lightsail instance name: presgen-demo
□ Static IP allocated
```

### 4. Security Credentials

```bash
□ HTTP Basic Auth passwords chosen
  - demo_user: AllCloud2024!
  - cto_user: CTODemo2024!
  - yosi_user: YosiDemo2024!
□ API keys secured (not in Git)
□ SSH key pair created for Lightsail access
```

### 5. Documentation

```bash
□ Architecture diagram saved
□ Access credentials documented
□ Cost estimates reviewed
□ Monitoring plan confirmed
□ Rollback plan prepared
```

---

## Deployment Instructions

### Phase 1: AWS Infrastructure Setup (30 minutes)

#### Step 1.1: Create S3 Bucket

```bash
#!/bin/bash
# 01-create-s3-bucket.sh

set -e

TIMESTAMP=$(date +%s)
BUCKET_NAME="presgen-demo-files-${TIMESTAMP}"
REGION="us-east-1"

echo "Creating S3 bucket: $BUCKET_NAME"

# Create bucket
aws s3 mb s3://${BUCKET_NAME} --region ${REGION}

# Enable versioning (optional, for safety)
aws s3api put-bucket-versioning \
  --bucket ${BUCKET_NAME} \
  --versioning-configuration Status=Enabled

# Set lifecycle policy (delete old files after 30 days)
cat > lifecycle.json <<EOF
{
  "Rules": [
    {
      "Id": "DeleteOldUploads",
      "Status": "Enabled",
      "Prefix": "uploads/",
      "Expiration": {
        "Days": 30
      }
    },
    {
      "Id": "MoveOldOutputsToIA",
      "Status": "Enabled",
      "Prefix": "outputs/",
      "Transitions": [
        {
          "Days": 7,
          "StorageClass": "STANDARD_IA"
        }
      ]
    }
  ]
}
EOF

aws s3api put-bucket-lifecycle-configuration \
  --bucket ${BUCKET_NAME} \
  --lifecycle-configuration file://lifecycle.json

# Enable CORS
cat > cors.json <<EOF
[
  {
    "AllowedOrigins": ["*"],
    "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
    "AllowedHeaders": ["*"],
    "MaxAgeSeconds": 3000
  }
]
EOF

aws s3api put-bucket-cors \
  --bucket ${BUCKET_NAME} \
  --cors-configuration file://cors.json

# Block public access by default
aws s3api put-public-access-block \
  --bucket ${BUCKET_NAME} \
  --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# Set bucket policy for outputs folder (public read)
cat > bucket-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadOutputs",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::${BUCKET_NAME}/outputs/*"
    }
  ]
}
EOF

# Note: This will fail due to public access block
# Remove block for outputs if needed, or use signed URLs

echo "✅ S3 bucket created: $BUCKET_NAME"
echo "Export this for later:"
echo "export S3_BUCKET=$BUCKET_NAME"

# Save to file
echo "S3_BUCKET=$BUCKET_NAME" > aws-resources.env
```

#### Step 1.2: Create Lightsail Instance

```bash
#!/bin/bash
# 02-create-lightsail-instance.sh

set -e

source aws-resources.env

INSTANCE_NAME="presgen-demo"
BUNDLE_ID="medium_2_0"  # 1GB RAM, 2 vCPUs, $10/month
# Use nano_2_0 for $5/month (512MB) if budget is tight
BLUEPRINT_ID="ubuntu_22_04"
REGION="us-east-1"
AZ="${REGION}a"

echo "Creating Lightsail instance: $INSTANCE_NAME"

# Create startup script
cat > startup-script.sh <<'STARTUP'
#!/bin/bash
set -e

# Update system
apt-get update
apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
usermod -aG docker ubuntu

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Install AWS CLI
apt-get install -y awscli unzip

# Install utilities
apt-get install -y \
  htop \
  vim \
  curl \
  wget \
  git \
  apache2-utils

# Create directories
mkdir -p /home/ubuntu/presgen
mkdir -p /etc/nginx/auth
chown -R ubuntu:ubuntu /home/ubuntu/presgen

# Enable swap (helpful for 1GB instance)
fallocate -l 1G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab

echo "✅ Startup script completed"
STARTUP

# Create instance
aws lightsail create-instances \
  --instance-names ${INSTANCE_NAME} \
  --availability-zone ${AZ} \
  --blueprint-id ${BLUEPRINT_ID} \
  --bundle-id ${BUNDLE_ID} \
  --user-data file://startup-script.sh \
  --tags key=Project,value=Presgen key=Environment,value=Demo

echo "Waiting for instance to be running..."
aws lightsail wait instance-running --instance-name ${INSTANCE_NAME}

# Allocate and attach static IP
echo "Allocating static IP..."
aws lightsail allocate-static-ip \
  --static-ip-name ${INSTANCE_NAME}-ip

aws lightsail attach-static-ip \
  --static-ip-name ${INSTANCE_NAME}-ip \
  --instance-name ${INSTANCE_NAME}

# Get static IP
STATIC_IP=$(aws lightsail get-static-ip \
  --static-ip-name ${INSTANCE_NAME}-ip \
  --query 'staticIp.ipAddress' \
  --output text)

echo "✅ Instance created with static IP: $STATIC_IP"

# Open ports
echo "Configuring firewall..."
aws lightsail put-instance-public-ports \
  --instance-name ${INSTANCE_NAME} \
  --port-infos '[
    {"fromPort":22,"toPort":22,"protocol":"tcp","cidrs":["0.0.0.0/0"]},
    {"fromPort":80,"toPort":80,"protocol":"tcp","cidrs":["0.0.0.0/0"]},
    {"fromPort":443,"toPort":443,"protocol":"tcp","cidrs":["0.0.0.0/0"]}
  ]'

# Save instance info
echo "INSTANCE_NAME=$INSTANCE_NAME" >> aws-resources.env
echo "STATIC_IP=$STATIC_IP" >> aws-resources.env

echo "
✅ Lightsail instance ready!

Instance: $INSTANCE_NAME
IP: $STATIC_IP
Region: $REGION

Access via SSH:
  aws lightsail download-default-key-pair --output text > lightsail-key.pem
  chmod 600 lightsail-key.pem
  ssh -i lightsail-key.pem ubuntu@$STATIC_IP

Note: Wait 2-3 minutes for startup script to complete
"
```

#### Step 1.3: Create IAM Role for Lightsail

```bash
#!/bin/bash
# 03-create-iam-role.sh

set -e

ROLE_NAME="presgen-lightsail-role"

echo "Creating IAM role for Lightsail..."

# Create trust policy
cat > trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lightsail.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create role
aws iam create-role \
  --role-name ${ROLE_NAME} \
  --assume-role-policy-document file://trust-policy.json \
  --description "Role for Presgen Lightsail instance"

# Create S3 access policy
cat > s3-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::presgen-demo-files-*/*",
        "arn:aws:s3:::presgen-demo-files-*"
      ]
    }
  ]
}
EOF

# Create and attach policy
POLICY_ARN=$(aws iam create-policy \
  --policy-name presgen-s3-access \
  --policy-document file://s3-policy.json \
  --query 'Policy.Arn' \
  --output text)

aws iam attach-role-policy \
  --role-name ${ROLE_NAME} \
  --policy-arn ${POLICY_ARN}

# Attach CloudWatch logs policy
aws iam attach-role-policy \
  --role-name ${ROLE_NAME} \
  --policy-arn arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy

echo "✅ IAM role created: $ROLE_NAME"
echo "Policy ARN: $POLICY_ARN"

# Note: Lightsail doesn't directly support instance profiles
# Instead, configure AWS CLI on instance with credentials
```

### Phase 2: Application Deployment (60 minutes)

#### Step 2.1: Download SSH Key and Access Instance

```bash
#!/bin/bash
# 04-access-instance.sh

set -e

source aws-resources.env

# Download SSH key
aws lightsail download-default-key-pair \
  --query 'privateKeyBase64' \
  --output text | base64 -d > lightsail-key.pem

chmod 600 lightsail-key.pem

echo "✅ SSH key downloaded: lightsail-key.pem"
echo ""
echo "Connect to instance:"
echo "  ssh -i lightsail-key.pem ubuntu@${STATIC_IP}"
echo ""
echo "Checking if startup script completed..."
sleep 10

# Check if Docker is installed
ssh -i lightsail-key.pem -o StrictHostKeyChecking=no ubuntu@${STATIC_IP} << 'ENDSSH'
  echo "Checking Docker installation..."
  if command -v docker &> /dev/null; then
    echo "✅ Docker installed: $(docker --version)"
  else
    echo "⏳ Docker not yet installed, waiting for startup script..."
    exit 1
  fi
  
  if command -v docker-compose &> /dev/null; then
    echo "✅ Docker Compose installed: $(docker-compose --version)"
  else
    echo "⏳ Docker Compose not yet installed..."
    exit 1
  fi
  
  echo "✅ Instance ready for deployment!"
ENDSSH

if [ $? -ne 0 ]; then
  echo "⏳ Startup script still running. Wait 2-3 minutes and try again:"
  echo "  ssh -i lightsail-key.pem ubuntu@${STATIC_IP}"
  exit 1
fi
```

#### Step 2.2: Upload Application Code

```bash
#!/bin/bash
# 05-upload-application.sh

set -e

source aws-resources.env

echo "Preparing application for upload..."

# Create deployment package
mkdir -p deploy-package
cd deploy-package

# Copy application files
cp -r ../backend .
cp -r ../frontend .
cp ../docker-compose.yml .
cp ../nginx.conf .

# Create .env file
cat > .env <<EOF
# Environment
ENVIRONMENT=production
NODE_ENV=production

# AWS Configuration
AWS_REGION=us-east-1
S3_BUCKET=${S3_BUCKET}
STORAGE_PROVIDER=s3

# API Keys (will be set separately)
# OPENAI_API_KEY=
# GOOGLE_CREDENTIALS=

# Application
WORKERS=1
THREADS=2
GPU_ENABLED=false
EOF

# Create README for deployment
cat > DEPLOY.md <<'EOF'
# Deployment Instructions

1. Set API keys:
   export OPENAI_API_KEY="your-key-here"
   
2. Build and start:
   docker-compose up -d --build
   
3. Check logs:
   docker-compose logs -f
   
4. Verify health:
   curl http://localhost:8000/health
EOF

cd ..

# Upload to instance
echo "Uploading application to ${STATIC_IP}..."
scp -i lightsail-key.pem -r deploy-package ubuntu@${STATIC_IP}:/home/ubuntu/presgen

echo "✅ Application uploaded"
```

#### Step 2.3: Configure Secrets

```bash
#!/bin/bash
# 06-configure-secrets.sh

set -e

source aws-resources.env

echo "Configuring secrets on instance..."

# Prompt for API keys
read -sp "Enter OpenAI API Key: " OPENAI_KEY
echo
read -sp "Enter Google Credentials (paste entire JSON, then Ctrl+D): " GOOGLE_CREDS
echo

# Upload secrets to instance
ssh -i lightsail-key.pem ubuntu@${STATIC_IP} << ENDSSH
  # Create secrets directory
  mkdir -p /home/ubuntu/presgen/secrets
  
  # Store OpenAI key
  echo "OPENAI_API_KEY=${OPENAI_KEY}" > /home/ubuntu/presgen/.env.secrets
  
  # Store Google credentials
  cat > /home/ubuntu/presgen/secrets/google-creds.json <<'GOOGLEEOF'
${GOOGLE_CREDS}
GOOGLEEOF
  
  # Set permissions
  chmod 600 /home/ubuntu/presgen/.env.secrets
  chmod 600 /home/ubuntu/presgen/secrets/google-creds.json
  
  echo "✅ Secrets configured"
ENDSSH

echo "✅ Secrets uploaded and secured"
```

#### Step 2.4: Setup Basic Authentication

```bash
#!/bin/bash
# 07-setup-authentication.sh

set -e

source aws-resources.env

echo "Setting up HTTP Basic Authentication..."

ssh -i lightsail-key.pem ubuntu@${STATIC_IP} << 'ENDSSH'
  # Install htpasswd utility
  sudo apt-get update
  sudo apt-get install -y apache2-utils
  
  # Create auth directory
  sudo mkdir -p /etc/nginx/auth
  
  # Create users
  echo "Creating demo_user..."
  echo 'AllCloud2024!' | sudo htpasswd -ci /etc/nginx/auth/.htpasswd demo_user
  
  echo "Creating cto_user..."
  echo 'CTODemo2024!' | sudo htpasswd -i /etc/nginx/auth/.htpasswd cto_user
  
  echo "Creating yosi_user..."
  echo 'YosiDemo2024!' | sudo htpasswd -i /etc/nginx/auth/.htpasswd yosi_user
  
  # Set permissions
  sudo chmod 644 /etc/nginx/auth/.htpasswd
  
  # Verify
  echo "✅ Users created:"
  sudo cat /etc/nginx/auth/.htpasswd | cut -d: -f1
ENDSSH

echo "✅ Authentication configured"
echo ""
echo "Demo credentials:"
echo "  demo_user / AllCloud2024!"
echo "  cto_user / CTODemo2024!"
echo "  yosi_user / YosiDemo2024!"
```

#### Step 2.5: Deploy Application

```bash
#!/bin/bash
# 08-deploy-application.sh

set -e

source aws-resources.env

echo "Deploying application on ${STATIC_IP}..."

ssh -i lightsail-key.pem ubuntu@${STATIC_IP} << 'ENDSSH'
  cd /home/ubuntu/presgen/deploy-package
  
  # Load secrets
  source ../.env.secrets
  export OPENAI_API_KEY
  
  # Build images
  echo "Building Docker images..."
  docker-compose build
  
  # Start services
  echo "Starting services..."
  docker-compose up -d
  
  # Wait for services to start
  echo "Waiting for services to start..."
  sleep 30
  
  # Check status
  docker-compose ps
  
  # Check logs
  echo ""
  echo "Recent logs:"
  docker-compose logs --tail=20
  
  # Test health
  echo ""
  echo "Testing health endpoint..."
  curl -f http://localhost:8000/health || echo "Health check failed"
  
  echo ""
  echo "✅ Deployment complete!"
ENDSSH

echo "
✅ Application deployed!

Access at: http://${STATIC_IP}

Credentials:
  demo_user / AllCloud2024!
  cto_user / CTODemo2024!
  yosi_user / YosiDemo2024!

Check status:
  ssh -i lightsail-key.pem ubuntu@${STATIC_IP}
  docker-compose ps
  docker-compose logs -f
"
```

### Phase 3: Monitoring & Alerts Setup (30 minutes)

#### Step 3.1: Setup SNS Topic and Subscriptions

```bash
#!/bin/bash
# 09-setup-alerts.sh

set -e

EMAIL="ymeirovich@gmail.com"
PHONE="+972527563792"

echo "Setting up alerts and monitoring..."

# Create SNS topic
TOPIC_ARN=$(aws sns create-topic \
  --name presgen-demo-alerts \
  --query 'TopicArn' \
  --output text)

echo "SNS Topic: $TOPIC_ARN"

# Subscribe email
aws sns subscribe \
  --topic-arn ${TOPIC_ARN} \
  --protocol email \
  --notification-endpoint ${EMAIL}

echo "⚠️  Email subscription created. CHECK ${EMAIL} and confirm!"

# Subscribe SMS
aws sns subscribe \
  --topic-arn ${TOPIC_ARN} \
  --protocol sms \
  --notification-endpoint ${PHONE}

echo "SMS subscription created for ${PHONE}"

# Set SMS preferences
aws sns set-sms-attributes \
  --attributes DefaultSMSType=Transactional

# Save topic ARN
echo "TOPIC_ARN=${TOPIC_ARN}" >> aws-resources.env

echo "✅ SNS topic configured"
echo ""
echo "IMPORTANT: Check ${EMAIL} and confirm subscription!"
```

#### Step 3.2: Create CloudWatch Alarms

```bash
#!/bin/bash
# 10-create-alarms.sh

set -e

source aws-resources.env

echo "Creating CloudWatch alarms..."

# 1. Cost alarm (billing)
aws cloudwatch put-metric-alarm \
  --alarm-name presgen-cost-alert \
  --alarm-description "Alert when estimated monthly cost exceeds $10" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 21600 \
  --evaluation-periods 1 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions ${TOPIC_ARN} \
  --dimensions Name=Currency,Value=USD

echo "✅ Cost alarm created (threshold: $10/month)"

# 2. Instance health alarm
aws cloudwatch put-metric-alarm \
  --alarm-name presgen-instance-health \
  --alarm-description "Alert when Lightsail instance fails health checks" \
  --metric-name StatusCheckFailed \
  --namespace AWS/Lightsail \
  --statistic Maximum \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --alarm-actions ${TOPIC_ARN} \
  --dimensions Name=InstanceName,Value=${INSTANCE_NAME}

echo "✅ Instance health alarm created"

# 3. High CPU alarm
aws cloudwatch put-metric-alarm \
  --alarm-name presgen-high-cpu \
  --alarm-description "Alert when CPU usage exceeds 80% for 10 minutes" \
  --metric-name CPUUtilization \
  --namespace AWS/Lightsail \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions ${TOPIC_ARN} \
  --dimensions Name=InstanceName,Value=${INSTANCE_NAME}

echo "✅ CPU alarm created (threshold: 80%)"

# 4. Network out alarm (approaching data transfer limit)
aws cloudwatch put-metric-alarm \
  --alarm-name presgen-high-network \
  --alarm-description "Alert when network transfer approaches 1.5TB (75% of 2TB limit)" \
  --metric-name NetworkOut \
  --namespace AWS/Lightsail \
  --statistic Sum \
  --period 86400 \
  --evaluation-periods 1 \
  --threshold 1610612736000 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions ${TOPIC_ARN} \
  --dimensions Name=InstanceName,Value=${INSTANCE_NAME}

echo "✅ Network transfer alarm created (threshold: 1.5TB/month)"

# Test alert
echo ""
echo "Testing alert system..."
aws sns publish \
  --topic-arn ${TOPIC_ARN} \
  --subject "Presgen Demo Alert Test" \
  --message "This is a test alert from the Presgen demo monitoring system. If you receive this, alerts are working correctly!"

echo "
✅ All alarms configured!

Alerts will be sent to:
  📧 Email: ${EMAIL}
  📱 SMS: ${PHONE}

Alarms configured:
  ✓ Monthly cost > $10
  ✓ Instance health failures
  ✓ CPU usage > 80%
  ✓ Network transfer > 1.5TB/month

View alarms:
  aws cloudwatch describe-alarms --alarm-names presgen-cost-alert presgen-instance-health presgen-high-cpu presgen-high-network

⚠️  IMPORTANT: Confirm email subscription to receive alerts!
"
```

#### Step 3.3: Setup Log Monitoring

```bash
#!/bin/bash
# 11-setup-logging.sh

set -e

source aws-resources.env

echo "Setting up application logging..."

ssh -i lightsail-key.pem ubuntu@${STATIC_IP} << 'ENDSSH'
  cd /home/ubuntu/presgen/deploy-package
  
  # Create log rotation config
  sudo tee /etc/logrotate.d/presgen <<EOF
/home/ubuntu/presgen/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0644 ubuntu ubuntu
    sharedscripts
    postrotate
        docker-compose restart nginx api frontend
    endscript
}
EOF
  
  # Create logging script
  cat > /home/ubuntu/presgen/logs-to-cloudwatch.sh <<'LOGSCRIPT'
#!/bin/bash
# Send error logs to CloudWatch

ERROR_COUNT=$(docker-compose logs --tail=100 | grep -i error | wc -l)

if [ $ERROR_COUNT -gt 10 ]; then
  aws sns publish \
    --topic-arn "$TOPIC_ARN" \
    --subject "Presgen: High Error Rate" \
    --message "More than 10 errors detected in last 100 log lines. Check application logs."
fi
LOGSCRIPT
  
  chmod +x /home/ubuntu/presgen/logs-to-cloudwatch.sh
  
  # Add to cron (check every hour)
  (crontab -l 2>/dev/null; echo "0 * * * * /home/ubuntu/presgen/logs-to-cloudwatch.sh") | crontab -
  
  echo "✅ Logging configured"
ENDSSH

echo "✅ Log monitoring configured"
```

### Phase 4: Verification and Testing (30 minutes)

#### Step 4.1: Health Checks

```bash
#!/bin/bash
# 12-verify-deployment.sh

set -e

source aws-resources.env

echo "Verifying deployment on ${STATIC_IP}..."

# Test health endpoint (no auth)
echo "1. Testing health endpoint (no authentication)..."
HEALTH=$(curl -s http://${STATIC_IP}/health)
echo "   Response: $HEALTH"

if echo "$HEALTH" | grep -q "healthy"; then
  echo "   ✅ Health check passed"
else
  echo "   ❌ Health check failed"
  exit 1
fi

# Test with authentication
echo ""
echo "2. Testing with Basic Auth (demo_user)..."
AUTH_RESPONSE=$(curl -s -w "%{http_code}" -u demo_user:AllCloud2024! http://${STATIC_IP}/)
HTTP_CODE="${AUTH_RESPONSE: -3}"

if [ "$HTTP_CODE" = "200" ]; then
  echo "   ✅ Authentication working"
else
  echo "   ❌ Authentication failed (HTTP $HTTP_CODE)"
fi

# Test API endpoint
echo ""
echo "3. Testing API endpoint..."
API_RESPONSE=$(curl -s -u demo_user:AllCloud2024! http://${STATIC_IP}/api/presentations 2>&1)
echo "   Response: ${API_RESPONSE:0:100}..."

# Check Docker status
echo ""
echo "4. Checking Docker containers..."
ssh -i lightsail-key.pem ubuntu@${STATIC_IP} << 'ENDSSH'
  cd /home/ubuntu/presgen/deploy-package
  docker-compose ps
  
  echo ""
  echo "Container health:"
  docker inspect presgen-api --format='{{.State.Health.Status}}' 2>/dev/null || echo "No health check"
  docker inspect presgen-frontend --format='{{.State.Health.Status}}' 2>/dev/null || echo "No health check"
ENDSSH

# Check disk space
echo ""
echo "5. Checking disk space..."
ssh -i lightsail-key.pem ubuntu@${STATIC_IP} 'df -h | grep -E "Filesystem|/dev/root"'

# Check memory
echo ""
echo "6. Checking memory usage..."
ssh -i lightsail-key.pem ubuntu@${STATIC_IP} 'free -h'

echo "
═══════════════════════════════════════════════
          Deployment Verification Complete
═══════════════════════════════════════════════

Application URL: http://${STATIC_IP}

Test Credentials:
  Username: demo_user
  Password: AllCloud2024!

API Health: http://${STATIC_IP}/health (no auth required)

Next Steps:
  1. Open http://${STATIC_IP} in browser
  2. Log in with demo_user credentials
  3. Test Core module (text → slides)
  4. Test Data module (Excel → charts)
  5. Verify file uploads work
  6. Check email for SNS confirmation

Monitoring:
  Email: ymeirovich@gmail.com
  SMS: +972527563792
  Alerts: Cost, CPU, Health, Network

SSH Access:
  ssh -i lightsail-key.pem ubuntu@${STATIC_IP}

View Logs:
  docker-compose logs -f

═══════════════════════════════════════════════
"
```

#### Step 4.2: Module Testing

```bash
#!/bin/bash
# 13-test-modules.sh

set -e

source aws-resources.env

echo "Testing Presgen modules..."

# Test Core module (text → slides)
echo ""
echo "1. Testing Core Module (Text → Slides)..."
curl -X POST \
  -u demo_user:AllCloud2024! \
  -H "Content-Type: application/json" \
  -d '{
    "report_text": "Test presentation. This is a demo slide. This is another demo slide.",
    "slides": 3,
    "title": "Test Presentation",
    "use_ai_images": false
  }' \
  http://${STATIC_IP}/api/core/generate

echo ""
echo "   ✅ Core module tested (check response above)"

# Test Data module (if Excel file available)
echo ""
echo "2. Testing Data Module..."
echo "   (Manual test required - upload Excel file via UI)"

# Test health of all services
echo ""
echo "3. Testing all service endpoints..."
for service in core data assess; do
  echo -n "   Testing /${service}/health... "
  RESPONSE=$(curl -s -u demo_user:AllCloud2024! http://${STATIC_IP}/api/${service}/health)
  if echo "$RESPONSE" | grep -q "ok\|healthy"; then
    echo "✅"
  else
    echo "❌ (Response: $RESPONSE)"
  fi
done

echo "
✅ Module testing complete

Manual tests required:
  1. Upload Excel file and generate charts
  2. Create assessment
  3. Upload video (if CPU-based processing enabled)

Access the application:
  http://${STATIC_IP}
  Username: demo_user
  Password: AllCloud2024!
"
```

---

## Monitoring & Alerts Setup

### CloudWatch Alarms Configured

| Alarm Name | Metric | Threshold | Action |
|------------|--------|-----------|--------|
| **presgen-cost-alert** | Estimated Charges | > $10/month | Email + SMS to ymeirovich@gmail.com / +972527563792 |
| **presgen-instance-health** | Status Check Failed | ≥ 1 failure | Email + SMS alert |
| **presgen-high-cpu** | CPU Utilization | > 80% for 10 min | Email + SMS alert |
| **presgen-high-network** | Network Out | > 1.5TB/month | Email + SMS alert |

### SNS Configuration

```yaml
Topic: presgen-demo-alerts
Subscriptions:
  - Protocol: email
    Endpoint: ymeirovich@gmail.com
    Status: Pending confirmation (check email!)
  
  - Protocol: sms
    Endpoint: +972527563792
    Status: Active
```

### Manual Monitoring Commands

```bash
# View all alarms
aws cloudwatch describe-alarms \
  --alarm-names presgen-cost-alert presgen-instance-health presgen-high-cpu presgen-high-network

# Check alarm state
aws cloudwatch describe-alarm-history \
  --alarm-name presgen-cost-alert \
  --max-records 10

# Get cost to date
aws ce get-cost-and-usage \
  --time-period Start=2025-10-01,End=2025-10-28 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --filter file://cost-filter.json

# Monitor instance metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lightsail \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceName,Value=presgen-demo \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average
```

### Dashboard Creation (Optional)

```bash
# Create CloudWatch dashboard
aws cloudwatch put-dashboard \
  --dashboard-name presgen-demo \
  --dashboard-body file://dashboard.json

# dashboard.json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/Lightsail", "CPUUtilization", {"stat": "Average"}],
          [".", "NetworkOut", {"stat": "Sum"}]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "Presgen Instance Metrics"
      }
    }
  ]
}

# View dashboard
echo "Dashboard URL: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=presgen-demo"
```

---

## Post-Deployment Operations

### Daily Operations

#### Start/Stop Instance (Cost Savings)

```bash
# Stop instance when not demoing
aws lightsail stop-instance --instance-name presgen-demo

# Cost while stopped: ~$0.60/month (storage only)

# Start instance for demo
aws lightsail start-instance --instance-name presgen-demo

# Wait for instance to be ready (2-3 minutes)
aws lightsail wait instance-running --instance-name presgen-demo

# Get current status
aws lightsail get-instance --instance-name presgen-demo \
  --query 'instance.state.name' --output text
```

#### View Logs

```bash
# SSH into instance
ssh -i lightsail-key.pem ubuntu@$STATIC_IP

# View all logs
cd /home/ubuntu/presgen/deploy-package
docker-compose logs -f

# View specific service logs
docker-compose logs -f api
docker-compose logs -f frontend
docker-compose logs -f nginx

# View last 100 lines
docker-compose logs --tail=100

# Search logs for errors
docker-compose logs | grep -i error

# View nginx access logs
docker exec presgen-nginx tail -f /var/log/nginx/access.log
```

#### Restart Services

```bash
# Restart all services
ssh -i lightsail-key.pem ubuntu@$STATIC_IP << 'ENDSSH'
  cd /home/ubuntu/presgen/deploy-package
  docker-compose restart
ENDSSH

# Restart specific service
docker-compose restart api

# Full rebuild (if code changed)
docker-compose down
docker-compose up -d --build
```

### Backup and Restore

#### Create Snapshot

```bash
# Create snapshot (backup)
aws lightsail create-instance-snapshot \
  --instance-name presgen-demo \
  --instance-snapshot-name presgen-demo-$(date +%Y%m%d)

# List snapshots
aws lightsail get-instance-snapshots

# Snapshot cost: $0.05/GB/month (typically ~$0.60/month for 12GB)
```

#### Restore from Snapshot

```bash
# Create new instance from snapshot
aws lightsail create-instances-from-snapshot \
  --instance-names presgen-demo-restored \
  --availability-zone us-east-1a \
  --bundle-id medium_2_0 \
  --instance-snapshot-name presgen-demo-20251028

# Attach static IP to restored instance
aws lightsail attach-static-ip \
  --static-ip-name presgen-demo-ip \
  --instance-name presgen-demo-restored
```

#### Database Backup

```bash
# Backup SQLite database
ssh -i lightsail-key.pem ubuntu@$STATIC_IP << 'ENDSSH'
  cd /home/ubuntu/presgen
  
  # Create backup
  docker exec presgen-api sqlite3 /data/presgen.db .dump > backup-$(date +%Y%m%d).sql
  
  # Compress
  gzip backup-$(date +%Y%m%d).sql
  
  # Upload to S3
  aws s3 cp backup-$(date +%Y%m%d).sql.gz s3://$S3_BUCKET/backups/
ENDSSH

# Download backup locally
scp -i lightsail-key.pem ubuntu@$STATIC_IP:/home/ubuntu/presgen/backup-*.sql.gz ./
```

### Scaling Up (If Needed)

#### Upgrade Instance Size

```bash
# Stop instance
aws lightsail stop-instance --instance-name presgen-demo

# Create snapshot before upgrading
aws lightsail create-instance-snapshot \
  --instance-name presgen-demo \
  --instance-snapshot-name presgen-before-upgrade

# Upgrade bundle (requires instance stopped)
aws lightsail update-instance-bundle \
  --instance-name presgen-demo \
  --bundle-id large_2_0  # 2GB RAM, $20/month

# Start instance
aws lightsail start-instance --instance-name presgen-demo

# Available bundles:
# - nano_2_0: 512MB, $3.50/month
# - micro_2_0: 1GB, $5/month
# - small_2_0: 2GB, $10/month
# - medium_2_0: 4GB, $20/month
# - large_2_0: 8GB, $40/month
```

#### Add More Storage

```bash
# Create and attach disk (if more than 40GB needed)
aws lightsail create-disk \
  --disk-name presgen-extra-storage \
  --availability-zone us-east-1a \
  --size-in-gb 100

# Attach disk
aws lightsail attach-disk \
  --disk-name presgen-extra-storage \
  --instance-name presgen-demo \
  --disk-path /dev/xvdf

# Mount on instance
ssh -i lightsail-key.pem ubuntu@$STATIC_IP << 'ENDSSH'
  # Format disk
  sudo mkfs -t ext4 /dev/xvdf
  
  # Create mount point
  sudo mkdir -p /mnt/extra-storage
  
  # Mount disk
  sudo mount /dev/xvdf /mnt/extra-storage
  
  # Add to fstab for auto-mount
  echo '/dev/xvdf /mnt/extra-storage ext4 defaults,nofail 0 2' | sudo tee -a /etc/fstab
  
  # Move uploads to extra storage
  sudo mv /home/ubuntu/presgen/data/uploads /mnt/extra-storage/
  sudo ln -s /mnt/extra-storage/uploads /home/ubuntu/presgen/data/uploads
ENDSSH

# Cost: Additional storage = $0.10/GB/month
```

### Security Updates

```bash
# Update system packages
ssh -i lightsail-key.pem ubuntu@$STATIC_IP << 'ENDSSH'
  sudo apt-get update
  sudo apt-get upgrade -y
  sudo apt-get autoremove -y
ENDSSH

# Update Docker images
ssh -i lightsail-key.pem ubuntu@$STATIC_IP << 'ENDSSH'
  cd /home/ubuntu/presgen/deploy-package
  docker-compose pull
  docker-compose up -d --build
ENDSSH

# Rotate Basic Auth passwords
ssh -i lightsail-key.pem ubuntu@$STATIC_IP << 'ENDSSH'
  # Change password for user
  sudo htpasswd /etc/nginx/auth/.htpasswd demo_user
  
  # Reload nginx
  docker-compose restart nginx
ENDSSH
```

### Cost Monitoring

```bash
# Check current month costs
aws ce get-cost-and-usage \
  --time-period Start=$(date +%Y-%m-01),End=$(date +%Y-%m-%d) \
  --granularity DAILY \
  --metrics BlendedCost \
  --group-by Type=SERVICE

# Forecast costs for rest of month
aws ce get-cost-forecast \
  --time-period Start=$(date +%Y-%m-%d),End=$(date -d "$(date +%Y-%m-01) +1 month -1 day" +%Y-%m-%d) \
  --metric BLENDED_COST \
  --granularity MONTHLY

# Set up budget alert (one-time setup)
aws budgets create-budget \
  --account-id $(aws sts get-caller-identity --query Account --output text) \
  --budget file://budget.json \
  --notifications-with-subscribers file://notifications.json
```

---

## Troubleshooting Guide

### Common Issues and Solutions

#### Issue 1: Cannot Access Application (401 Unauthorized)

**Symptoms:**
- Browser prompts for username/password
- Credentials don't work

**Solutions:**

```bash
# Check if .htpasswd file exists
ssh -i lightsail-key.pem ubuntu@$STATIC_IP << 'ENDSSH'
  if [ -f /etc/nginx/auth/.htpasswd ]; then
    echo "✅ Password file exists"
    sudo cat /etc/nginx/auth/.htpasswd
  else
    echo "❌ Password file missing!"
  fi
ENDSSH

# Recreate password file
ssh -i lightsail-key.pem ubuntu@$STATIC_IP << 'ENDSSH'
  sudo apt-get install -y apache2-utils
  echo 'AllCloud2024!' | sudo htpasswd -ci /etc/nginx/auth/.htpasswd demo_user
  sudo chmod 644 /etc/nginx/auth/.htpasswd
  docker-compose restart nginx
ENDSSH

# Test authentication
curl -u demo_user:AllCloud2024! http://$STATIC_IP/
```

#### Issue 2: 502 Bad Gateway

**Symptoms:**
- Nginx returns 502 error
- Application not responding

**Solutions:**

```bash
# Check if all containers are running
ssh -i lightsail-key.pem ubuntu@$STATIC_IP << 'ENDSSH'
  cd /home/ubuntu/presgen/deploy-package
  docker-compose ps
ENDSSH

# Check logs for errors
docker-compose logs api | tail -50
docker-compose logs frontend | tail -50

# Restart services
docker-compose restart

# Check if services are listening on correct ports
docker exec presgen-api netstat -tlnp | grep 8000
docker exec presgen-frontend netstat -tlnp | grep 3000
```

#### Issue 3: Out of Memory

**Symptoms:**
- Containers crashing
- OOM (Out of Memory) errors in logs
- Services restarting frequently

**Solutions:**

```bash
# Check memory usage
ssh -i lightsail-key.pem ubuntu@$STATIC_IP << 'ENDSSH'
  free -h
  docker stats --no-stream
ENDSSH

# Add swap if not present
ssh -i lightsail-key.pem ubuntu@$STATIC_IP << 'ENDSSH'
  if [ ! -f /swapfile ]; then
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
  fi
  
  free -h
ENDSSH

# Reduce memory limits if needed
# Edit docker-compose.yml and reduce mem_limit values

# Upgrade to larger instance
aws lightsail stop-instance --instance-name presgen-demo
aws lightsail update-instance-bundle \
  --instance-name presgen-demo \
  --bundle-id small_2_0  # 2GB RAM
aws lightsail start-instance --instance-name presgen-demo
```

#### Issue 4: Disk Space Full

**Symptoms:**
- Cannot upload files
- Application crashes
- Logs show "No space left on device"

**Solutions:**

```bash
# Check disk usage
ssh -i lightsail-key.pem ubuntu@$STATIC_IP 'df -h'

# Clean up Docker
ssh -i lightsail-key.pem ubuntu@$STATIC_IP << 'ENDSSH'
  # Remove unused containers, images, volumes
  docker system prune -af
  
  # Check space again
  df -h
ENDSSH

# Clean up old files
ssh -i lightsail-key.pem ubuntu@$STATIC_IP << 'ENDSSH'
  # Remove old uploads
  find /home/ubuntu/presgen/data/uploads -type f -mtime +7 -delete
  
  # Remove logs older than 7 days
  find /var/log -type f -mtime +7 -delete
  
  # Clear temp files
  sudo find /tmp -type f -mtime +1 -delete
ENDSSH

# Move large files to S3
# Or add additional disk (see Scaling Up section)
```

#### Issue 5: High CPU Usage

**Symptoms:**
- Application slow
- CloudWatch alert triggered
- Server unresponsive

**Solutions:**

```bash
# Check which process is using CPU
ssh -i lightsail-key.pem ubuntu@$STATIC_IP << 'ENDSSH'
  top -bn1 | head -20
  docker stats --no-stream
ENDSSH

# Check for runaway processes
ps aux --sort=-%cpu | head -10

# Restart API service (often fixes it)
docker-compose restart api

# Check for infinite loops in logs
docker-compose logs api | grep -i error

# Limit CPU usage in docker-compose.yml
# Add: cpus: '0.5' to service config
```

#### Issue 6: S3 Access Denied

**Symptoms:**
- Cannot upload files to S3
- Logs show "Access Denied" errors

**Solutions:**

```bash
# Check IAM credentials on instance
ssh -i lightsail-key.pem ubuntu@$STATIC_IP << 'ENDSSH'
  aws sts get-caller-identity
  aws s3 ls s3://presgen-demo-files/ || echo "Access denied"
ENDSSH

# Check S3 bucket policy
aws s3api get-bucket-policy --bucket presgen-demo-files

# Test S3 access
echo "test" > test.txt
aws s3 cp test.txt s3://presgen-demo-files/test.txt

# If using instance profile, verify permissions
aws iam get-role-policy \
  --role-name presgen-lightsail-role \
  --policy-name presgen-s3-access
```

#### Issue 7: Email Alerts Not Working

**Symptoms:**
- Not receiving CloudWatch alerts
- SNS subscription pending

**Solutions:**

```bash
# Check SNS subscription status
aws sns list-subscriptions-by-topic \
  --topic-arn $TOPIC_ARN

# Resend confirmation email
aws sns subscribe \
  --topic-arn $TOPIC_ARN \
  --protocol email \
  --notification-endpoint ymeirovich@gmail.com

# Test alert manually
aws sns publish \
  --topic-arn $TOPIC_ARN \
  --subject "Test Alert" \
  --message "Testing alert system"

# Check spam folder for confirmation email
# Confirm subscription by clicking link in email
```

#### Issue 8: Container Won't Start

**Symptoms:**
- `docker-compose up` fails
- Container exits immediately
- Logs show error on startup

**Solutions:**

```bash
# Check container logs
docker-compose logs api

# Run container interactively to debug
docker-compose run --rm api bash

# Inside container, test manually
python -c "import sys; print(sys.path)"
python -m uvicorn src.service.http:app --host 0.0.0.0 --port 8000

# Check environment variables
docker-compose config

# Rebuild from scratch
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

#### Issue 9: SSL/HTTPS Not Working

**Note:** Lightsail deployment uses HTTP by default. For HTTPS:

```bash
# Install Certbot for Let's Encrypt SSL
ssh -i lightsail-key.pem ubuntu@$STATIC_IP << 'ENDSSH'
  sudo apt-get install -y certbot python3-certbot-nginx
  
  # Get SSL certificate (requires domain name)
  sudo certbot --nginx -d your-domain.com
  
  # Nginx will be automatically configured for HTTPS
ENDSSH

# Or use CloudFront for HTTPS (free SSL certificate)
# Create CloudFront distribution pointing to Lightsail IP
```

### Getting Help

**If issues persist:**

1. **Check application logs:**
   ```bash
   ssh -i lightsail-key.pem ubuntu@$STATIC_IP
   cd /home/ubuntu/presgen/deploy-package
   docker-compose logs -f
   ```

2. **Check AWS service health:**
   ```bash
   aws lightsail get-instance --instance-name presgen-demo
   aws cloudwatch describe-alarms
   ```

3. **Contact information:**
   - Email: ymeirovich@gmail.com
   - Phone: +972527563792

4. **Useful AWS documentation:**
   - Lightsail: https://docs.aws.amazon.com/lightsail/
   - CloudWatch: https://docs.aws.amazon.com/cloudwatch/
   - SNS: https://docs.aws.amazon.com/sns/

---

## Appendix: Alternative Deployment Options

### Option A: Lambda + EFS (Absolute Minimum Cost)

**Cost:** $0.37-2/month  
**Complexity:** High  
**Deploy Time:** 5-6 hours

See complete deployment guide in separate document: `AWS_Lambda_Deployment.md`

**When to use:**
- Budget is absolute priority ($0-2/month)
- Low traffic (< 10K requests/month)
- Don't need GPU processing
- Comfortable with VPC/EFS complexity

### Option B: EC2 Spot Instance (Cheapest Compute)

**Cost:** $0.21-4/month (depending on usage)  
**Complexity:** Medium  
**Deploy Time:** 3-4 hours

**Setup:**

```bash
# Request spot instance
aws ec2 request-spot-instances \
  --spot-price "0.01" \
  --instance-count 1 \
  --type "persistent" \
  --launch-specification '{
    "ImageId": "ami-0c7217cdde317cfec",
    "InstanceType": "t4g.micro",
    "KeyName": "presgen-key",
    "SecurityGroupIds": ["sg-xxxxx"]
  }'

# Same deployment steps as Lightsail after instance starts
```

**When to use:**
- Want absolute minimum compute cost
- Don't mind potential interruptions (rare for t4g.micro)
- Need flexibility to scale up/down

### Option C: ECS Fargate (Containerized Serverless)

**Cost:** $5-15/month  
**Complexity:** High  
**Deploy Time:** 6-8 hours

**When to use:**
- Want auto-scaling
- Need production-grade container orchestration
- Plan to scale to many users
- Already familiar with ECS

### Option D: EC2 + GPU for Full Platform

**Cost:** $10-50/month (depending on GPU usage)  
**Complexity:** Medium-High  
**Deploy Time:** 4-6 hours

**Architecture:**

```
Lightsail (API + Frontend): $5/month
  +
EC2 g4dn.xlarge Spot (GPU): $0.16/hour × usage hours
  = $5-50/month total
```

**When to use:**
- Need to demo Video + Avatar modules with GPU
- Budget allows for GPU costs
- Want production-like performance

---

## Summary

This migration plan delivers a **cost-optimized AWS deployment** of Presgen on Lightsail for **$5-9/month** with:

✅ **Full deployment in 2-3 hours**  
✅ **Simple HTTP Basic Authentication**  
✅ **Automated monitoring and alerts**  
✅ **Email + SMS notifications**  
✅ **Minimal configuration changes**  
✅ **Core, Data, and Assess modules fully working**  
✅ **Professional demo-ready environment**  

**Total estimated cost for 3-month demo:** $15-27

**Deployment steps:**
1. Run infrastructure scripts (30 min)
2. Deploy application (60 min)
3. Configure monitoring (30 min)
4. Verify and test (30 min)

**Contact:**
- Email: ymeirovich@gmail.com
- Phone: +972527563792

**Ready to deploy!** 🚀