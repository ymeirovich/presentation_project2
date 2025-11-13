# PresGen AWS Lightsail Migration - Phased Implementation Plan

**Version:** 3.0
**Date:** November 12, 2025
**Status:** 🚀 Ready for Phased Implementation
**Target Platform:** AWS Lightsail
**AWS Account:** 788159322332 (presgen_user)

---

## Executive Summary

This document provides a comprehensive, phased approach to migrating the PresGen application suite to AWS Lightsail. The migration is broken down into 8 manageable phases, each with clear deliverables, time estimates, and success criteria.

**Total Estimated Time:** 3-5 days (20-32 hours)
**Monthly Cost:** $12-50 depending on configuration
**Risk Level:** Low (phased approach with rollback capability)

---

## Current Architecture Overview

### System Components

```
┌─────────────────────────────────────────┐
│   Frontend (presgen-ui)                 │
│   Next.js 14.x TypeScript               │
│   Port: 3000                             │
└────────────┬────────────────────────────┘
             │
┌────────────▼──────────────────────────────────────────┐
│  nginx Reverse Proxy                                  │
│  - HTTP Basic Auth                                    │
│  - Rate Limiting                                      │
│  - Client max body: 500MB                             │
│  Port: 80/443                                         │
└────────────┬──────────────────────────────────────────┘
             │
    ┌────────┴────────────────┬──────────────────┐
    │                         │                  │
┌───▼────────────────┐   ┌───▼──────────┐  ┌──▼──────────┐
│ PresGen-Core       │   │PresGen-Assess│  │PresGen-Avatar│
│ Port: 8080         │   │ Port: 8000    │  │ Port: 8002    │
│ Python 3.13        │   │ Python 3.11   │  │ Python 3.11   │
│ MCP Orchestrator   │   │ Assessment    │  │ Video Gen     │
│ Google APIs        │   │ RAG/ChromaDB  │  │ (Stub)        │
└────────────────────┘   └───────────────┘  └───────────────┘
         │                       │
         │                       ▼
         │              ┌─────────────────┐
         │              │ SQLite / Postgres│
         │              │ Port: 5432       │
         │              └─────────────────┘
         │
         ▼
┌──────────────────┐
│ Redis Cache      │
│ Port: 6379       │
└──────────────────┘
```

### Key Dependencies
- **Google Cloud APIs:** Slides, Drive, Forms, Sheets, Vertex AI (Gemini, Imagen)
- **OpenAI:** GPT models, Whisper transcription
- **ElevenLabs:** Voice synthesis
- **Storage:** Local filesystem (dev) / S3 (production)

---

## Phase 1: Pre-Migration Preparation & Documentation
**Duration:** 4-6 hours
**Prerequisites:** None
**Risk Level:** Very Low

### Objectives
- Document current architecture comprehensively
- Identify all secrets, credentials, and API keys
- Create migration checklist and rollback procedures
- Test current system thoroughly to establish baseline

### Tasks

#### 1.1 Architecture Documentation (1 hour)
- [x] Map all services and dependencies (COMPLETED via exploration)
- [ ] Document all environment variables and their sources
- [ ] Create network topology diagram
- [ ] Document data flow between services
- [ ] Identify external API integrations and quotas

**Deliverable:** `CURRENT_ARCHITECTURE.md` with complete system documentation

#### 1.2 Secrets and Credentials Audit (1 hour)
- [ ] List all API keys (Google Cloud, OpenAI, ElevenLabs)
- [ ] Document service account credentials
- [ ] Identify OAuth tokens and refresh procedures
- [ ] Document HTTP Basic Auth credentials
- [ ] Create secrets migration plan

**Deliverable:** `SECRETS_CHECKLIST.md` (encrypted, not in git)

#### 1.3 Baseline Testing (2 hours)
- [ ] Test presentation generation (simple case)
- [ ] Test presentation generation (complex, 30+ slides)
- [ ] Test assessment workflow end-to-end
- [ ] Test course generation with video
- [ ] Test file upload (exam guides, transcripts)
- [ ] Document performance metrics (timing, resource usage)
- [ ] Test Google Drive integration
- [ ] Test Google Forms integration

**Deliverable:** `BASELINE_TEST_RESULTS.md` with performance benchmarks

#### 1.4 Rollback Procedure (1 hour)
- [ ] Document current Docker Compose configuration
- [ ] Create local environment restoration script
- [ ] Document database backup/restore procedure
- [ ] Create emergency contact list
- [ ] Document quick rollback steps

**Deliverable:** `ROLLBACK_PROCEDURE.md`

### Success Criteria
- [ ] All current functionality documented
- [ ] Baseline performance metrics recorded
- [ ] All secrets identified and secured
- [ ] Rollback procedure tested successfully

---

## Phase 2: AWS Infrastructure Setup
**Duration:** 3-4 hours
**Prerequisites:** Phase 1 complete, AWS account configured
**Risk Level:** Low

### Objectives
- Provision AWS Lightsail instance
- Configure networking and security groups
- Set up S3 buckets for storage
- Configure IAM roles and policies

### Tasks

#### 2.1 AWS CLI Configuration (15 minutes)
```bash
# Verify AWS credentials
aws sts get-caller-identity

# Set default region
aws configure set region us-east-1

# Test access
aws lightsail get-regions
```

**Success Check:** Command returns account 788159322332

#### 2.2 Lightsail Instance Provisioning (30 minutes)
```bash
# Create instance
aws lightsail create-instances \
  --instance-names presgen-prod \
  --availability-zone us-east-1a \
  --blueprint-id ubuntu_22_04 \
  --bundle-id medium_2_0

# Allocate static IP
aws lightsail allocate-static-ip \
  --static-ip-name presgen-prod-ip

# Attach static IP
aws lightsail attach-static-ip \
  --static-ip-name presgen-prod-ip \
  --instance-name presgen-prod
```

**Instance Specs:**
- **Bundle:** medium_2_0 ($20/month)
- **RAM:** 2GB
- **vCPUs:** 2
- **Storage:** 60GB SSD
- **Transfer:** 3TB/month

**Deliverable:** Static IP address documented

#### 2.3 Networking and Security Groups (30 minutes)
```bash
# Open required ports
aws lightsail open-instance-public-ports \
  --instance-name presgen-prod \
  --port-info fromPort=80,toPort=80,protocol=tcp

aws lightsail open-instance-public-ports \
  --instance-name presgen-prod \
  --port-info fromPort=443,toPort=443,protocol=tcp

aws lightsail open-instance-public-ports \
  --instance-name presgen-prod \
  --port-info fromPort=22,toPort=22,protocol=tcp
```

**Deliverable:** Security group configuration documented

#### 2.4 S3 Bucket Setup (30 minutes)
```bash
# Create buckets
aws s3 mb s3://presgen-prod-uploads --region us-east-1
aws s3 mb s3://presgen-prod-backups --region us-east-1
aws s3 mb s3://presgen-prod-exports --region us-east-1

# Configure lifecycle policies
aws s3api put-bucket-lifecycle-configuration \
  --bucket presgen-prod-backups \
  --lifecycle-configuration file://backup-lifecycle.json

# Enable versioning for backups
aws s3api put-bucket-versioning \
  --bucket presgen-prod-backups \
  --versioning-configuration Status=Enabled
```

**Deliverable:** S3 bucket URLs and access configuration

#### 2.5 IAM Roles and Policies (1 hour)
```bash
# Create EC2 instance role for Lightsail
aws iam create-role \
  --role-name PresGenLightsailRole \
  --assume-role-policy-document file://trust-policy.json

# Attach policies for S3 access
aws iam attach-role-policy \
  --role-name PresGenLightsailRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

# Attach policies for CloudWatch
aws iam attach-role-policy \
  --role-name PresGenLightsailRole \
  --policy-arn arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy
```

**Deliverable:** IAM role ARN documented

#### 2.6 CloudWatch Setup (30 minutes)
```bash
# Create log groups
aws logs create-log-group --log-group-name /presgen/nginx
aws logs create-log-group --log-group-name /presgen/core
aws logs create-log-group --log-group-name /presgen/assess
aws logs create-log-group --log-group-name /presgen/avatar
aws logs create-log-group --log-group-name /presgen/ui

# Set retention to 7 days
aws logs put-retention-policy \
  --log-group-name /presgen/nginx \
  --retention-in-days 7
```

**Deliverable:** CloudWatch log groups created

### Success Criteria
- [ ] Lightsail instance running and accessible via SSH
- [ ] Static IP attached
- [ ] All ports open and verified
- [ ] S3 buckets created with proper policies
- [ ] IAM roles configured
- [ ] CloudWatch logs configured

---

## Phase 3: Initial Deployment
**Duration:** 3-4 hours
**Prerequisites:** Phase 2 complete
**Risk Level:** Medium

### Objectives
- Install Docker and Docker Compose on Lightsail
- Transfer application code and secrets
- Deploy containers
- Verify basic functionality

### Tasks

#### 3.1 Server Setup (1 hour)
```bash
# SSH into instance
ssh -i lightsail-key.pem ubuntu@<STATIC_IP>

# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

**Deliverable:** Docker and Docker Compose installed

#### 3.2 Application Transfer (1 hour)
```bash
# On local machine, create deployment package
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs
tar -czf presgen-deploy.tar.gz \
  --exclude='.git' \
  --exclude='node_modules' \
  --exclude='__pycache__' \
  --exclude='data/*' \
  --exclude='logs/*' \
  --exclude='output/*' \
  .

# Transfer to Lightsail
scp -i lightsail-key.pem presgen-deploy.tar.gz ubuntu@<STATIC_IP>:/home/ubuntu/

# On server, extract
ssh -i lightsail-key.pem ubuntu@<STATIC_IP>
mkdir -p /home/ubuntu/presgen
cd /home/ubuntu/presgen
tar -xzf ../presgen-deploy.tar.gz
```

**Deliverable:** Application code on server

#### 3.3 Secrets Configuration (30 minutes)
```bash
# Create secrets directory
mkdir -p /home/ubuntu/presgen/secrets
chmod 700 /home/ubuntu/presgen/secrets

# Transfer secrets (from local machine)
scp -i lightsail-key.pem secrets/google-creds.json ubuntu@<STATIC_IP>:/home/ubuntu/presgen/secrets/
scp -i lightsail-key.pem secrets/token.json ubuntu@<STATIC_IP>:/home/ubuntu/presgen/secrets/
scp -i lightsail-key.pem secrets/oauth_slides_client.json ubuntu@<STATIC_IP>:/home/ubuntu/presgen/secrets/

# Set permissions
chmod 600 /home/ubuntu/presgen/secrets/*
```

**Deliverable:** All secrets transferred securely

#### 3.4 Environment Configuration (30 minutes)
```bash
# Update .env file with AWS-specific settings
cat > /home/ubuntu/presgen/.env <<EOF
# Service Ports
PRESGEN_ASSESS_PORT=8000
PRESGEN_CORE_PORT=8080
PRESGEN_UI_PORT=3000

# AWS Configuration
AWS_REGION=us-east-1
STORAGE_PROVIDER=s3
S3_BUCKET=presgen-prod-uploads

# Google Cloud
GOOGLE_CLOUD_PROJECT=presgen
GOOGLE_CLOUD_REGION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/secrets/google-creds.json
GOOGLE_QUOTA_PROJECT=presgen
GOOGLE_DRIVE_FOLDER_ID=14eRckmEzL-4FgXU4mn3u3-EP2GKNJX2p

# API Keys (use secrets manager)
OPENAI_API_KEY=\${OPENAI_API_KEY}
ELEVENLABS_API_KEY=\${ELEVENLABS_API_KEY}

# Feature Flags
PRESGEN_USE_MOCK=false
PRESGEN_USE_CACHE=true
PRESGEN_DEV_MODE=false
PRESGEN_CORE_MAX_SLIDES=40

# Service Account
FORCE_SERVICE_ACCOUNT=false
IMPERSONATE_USER=presgen-service@presgen.net

# Database (PostgreSQL for production)
DATABASE_URL=postgresql://presgen:password@localhost:5432/presgen_assess
EOF
```

**Deliverable:** Environment configured for AWS

#### 3.5 Initial Container Deployment (1 hour)
```bash
# Start services
cd /home/ubuntu/presgen
docker-compose up -d

# Monitor logs
docker-compose logs -f

# Verify all containers running
docker-compose ps
```

**Expected Output:**
```
NAME                COMMAND                  SERVICE             STATUS              PORTS
presgen-nginx       "/docker-entrypoint.…"   nginx               running             0.0.0.0:80->80/tcp
presgen-core        "uvicorn src.service…"   presgen-core        running             8080/tcp
presgen-assess      "sh -c 'alembic upgr…"   presgen-assess      running             8000/tcp
presgen-avatar      "uvicorn app.main:ap…"   presgen-avatar      running             8002/tcp
presgen-ui          "docker-entrypoint.s…"   presgen-ui          running             3000/tcp
redis               "docker-entrypoint.s…"   redis               running             6379/tcp
```

**Deliverable:** All containers running

### Success Criteria
- [ ] All Docker containers started successfully
- [ ] Health checks passing
- [ ] nginx responding on port 80
- [ ] Can access UI at http://<STATIC_IP>
- [ ] Basic Auth working (demo_user / AllCloud2024!)

---

## Phase 4: Functional Validation
**Duration:** 2-3 hours
**Prerequisites:** Phase 3 complete
**Risk Level:** Medium

### Objectives
- Test all critical workflows
- Verify Google Cloud integration
- Validate data persistence
- Test file uploads to S3
- Performance testing

### Tasks

#### 4.1 Health Check Validation (15 minutes)
```bash
# Test all health endpoints
curl http://<STATIC_IP>/api/presgen/health
curl http://<STATIC_IP>/api/presgen-assess/health

# Check nginx
curl -I http://<STATIC_IP>

# Check logs for errors
docker-compose logs --tail=100 | grep -i error
```

**Success Check:** All health endpoints return 200 OK

#### 4.2 Presentation Generation Test (30 minutes)
```bash
# Simple presentation (5 slides)
curl -u demo_user:AllCloud2024! \
  -X POST http://<STATIC_IP>/api/presgen/generate \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Introduction to AWS",
    "slides": 5,
    "use_ai_images": true
  }'

# Monitor progress
docker logs -f presgen-core
```

**Success Criteria:**
- [ ] Presentation created in Google Slides
- [ ] Images generated via Vertex AI Imagen
- [ ] Link returned to Google Drive
- [ ] Generation completed in < 5 minutes

#### 4.3 Complex Presentation Test (45 minutes)
```bash
# Complex presentation (30 slides) - tests timeout fix
curl -u demo_user:AllCloud2024! \
  -X POST http://<STATIC_IP>/api/presgen/generate \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Advanced AWS Solutions Architecture",
    "slides": 30,
    "use_ai_images": true
  }'
```

**Success Criteria:**
- [ ] Generation completes without timeout (< 10 minutes)
- [ ] All 30 slides created
- [ ] No timeout errors in logs

#### 4.4 Assessment Workflow Test (1 hour)
```bash
# Create workflow
curl -u demo_user:AllCloud2024! \
  -X POST http://<STATIC_IP>/api/presgen-assess/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "certification_id": "<cert_id>",
    "workflow_type": "gap_analysis"
  }'

# Upload exam guide
curl -u demo_user:AllCloud2024! \
  -X POST http://<STATIC_IP>/api/presgen-assess/files/upload \
  -F "file=@exam_guide.pdf" \
  -F "file_type=exam_guides"

# Generate assessment
# Submit responses
# Check gap analysis
# Generate recommended course
```

**Success Criteria:**
- [ ] Workflow created
- [ ] File uploaded to S3
- [ ] Assessment generated
- [ ] Gap analysis completed
- [ ] Course recommendations returned

#### 4.5 Video Generation Test (30 minutes)
```bash
# Generate course with video
curl -u demo_user:AllCloud2024! \
  -X POST http://<STATIC_IP>/api/presgen-assess/workflows/{id}/skills/{skill_id}/generate-course

# Poll for status
watch -n 2 'curl -u demo_user:AllCloud2024! \
  http://<STATIC_IP>/api/presgen-assess/workflows/{id}/courses/{course_id}/status'
```

**Success Criteria:**
- [ ] Course generation starts
- [ ] Video uploaded to Google Drive
- [ ] video_url returned in response
- [ ] drive_download_url returned in response (BUG FIX VERIFIED)
- [ ] Video playable in UI
- [ ] Download link visible and functional

### Success Criteria
- [ ] All baseline tests passing
- [ ] Performance within acceptable range
- [ ] No critical errors in logs
- [ ] Google Cloud integration working
- [ ] S3 storage working
- [ ] Video embedding and download link working (Issue #2 RESOLVED)

---

## Phase 5: Security Hardening
**Duration:** 4-5 hours
**Prerequisites:** Phase 4 complete
**Risk Level:** Low

### Objectives
- Implement SSL/TLS with Let's Encrypt
- Configure advanced rate limiting
- Set up Web Application Firewall (WAF)
- Harden nginx configuration
- Implement secrets management

### Tasks

#### 5.1 SSL Certificate (1 hour)
```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx -y

# Obtain certificate (requires domain)
sudo certbot --nginx -d presgen.yourdomain.com

# Auto-renewal
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

**Update nginx config:**
```nginx
server {
    listen 443 ssl http2;
    server_name presgen.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/presgen.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/presgen.yourdomain.com/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # ... rest of config
}
```

**Deliverable:** SSL certificate installed and auto-renewing

#### 5.2 Advanced Rate Limiting (1 hour)
```nginx
# Add to nginx.conf
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=upload:10m rate=1r/s;
limit_req_zone $binary_remote_addr zone=generate:10m rate=1r/m;

server {
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        limit_req_status 429;
    }

    location /api/presgen-assess/files/upload {
        limit_req zone=upload burst=3 nodelay;
    }

    location /api/presgen/generate {
        limit_req zone=generate burst=2 nodelay;
    }
}
```

**Deliverable:** Rate limiting configured per endpoint

#### 5.3 AWS WAF Setup (1 hour)
```bash
# Create WAF Web ACL
aws wafv2 create-web-acl \
  --name presgen-waf \
  --scope REGIONAL \
  --default-action Allow={} \
  --region us-east-1 \
  --rules file://waf-rules.json

# Associate with ALB (if using)
aws wafv2 associate-web-acl \
  --web-acl-arn <WAF_ARN> \
  --resource-arn <ALB_ARN>
```

**WAF Rules:**
- SQL injection protection
- XSS protection
- Rate-based rule (2000 req/5min per IP)
- Geo-blocking (if needed)
- Known bad inputs

**Deliverable:** WAF protecting the application

#### 5.4 Secrets Management (1 hour)
```bash
# Install and configure AWS Secrets Manager
aws secretsmanager create-secret \
  --name presgen/prod/google-creds \
  --secret-string file://secrets/google-creds.json \
  --region us-east-1

aws secretsmanager create-secret \
  --name presgen/prod/openai-api-key \
  --secret-string "$OPENAI_API_KEY" \
  --region us-east-1

# Update docker-compose to fetch secrets
# Use entrypoint script to fetch from Secrets Manager
```

**Deliverable:** Secrets in AWS Secrets Manager

#### 5.5 Security Headers (30 minutes)
```nginx
# Add to nginx.conf
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "no-referrer-when-downgrade" always;
add_header Content-Security-Policy "default-src 'self' https:; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';" always;
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
```

**Deliverable:** Security headers configured

### Success Criteria
- [ ] SSL certificate active and valid
- [ ] HTTPS working (http redirects to https)
- [ ] Rate limiting tested and working
- [ ] WAF rules active
- [ ] Security headers verified
- [ ] Secrets removed from .env file

---

## Phase 6: CI/CD Pipeline Setup
**Duration:** 3-4 hours
**Prerequisites:** Phase 5 complete
**Risk Level:** Low

### Objectives
- Set up GitHub Actions for automated deployment
- Implement automated testing
- Configure deployment workflows
- Set up staging environment

### Tasks

#### 6.1 GitHub Actions Workflow (2 hours)

Create `.github/workflows/deploy-production.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches: [ main ]
  workflow_dispatch:

env:
  AWS_REGION: us-east-1
  LIGHTSAIL_INSTANCE: presgen-prod
  DEPLOY_PATH: /home/ubuntu/presgen

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r presgen-assess/requirements.txt
          pip install -r requirements.txt

      - name: Run tests
        run: |
          pytest presgen-assess/tests/ -v
          pytest tests/ -v

      - name: Lint code
        run: |
          flake8 src/ presgen-assess/src/ --max-line-length=120

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build Docker images
        run: |
          docker-compose build

      - name: Test containers
        run: |
          docker-compose up -d
          sleep 30
          docker-compose ps
          curl http://localhost/health || exit 1
          docker-compose down

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Create deployment package
        run: |
          tar -czf presgen-deploy.tar.gz \
            --exclude='.git' \
            --exclude='node_modules' \
            --exclude='__pycache__' \
            --exclude='data/*' \
            --exclude='logs/*' \
            .

      - name: Upload to S3
        run: |
          aws s3 cp presgen-deploy.tar.gz s3://presgen-prod-backups/deployments/$(date +%Y%m%d-%H%M%S).tar.gz

      - name: Deploy to Lightsail
        run: |
          # SSH and deploy
          ssh -i ${{ secrets.LIGHTSAIL_SSH_KEY }} ubuntu@${{ secrets.LIGHTSAIL_IP }} << 'EOF'
            cd /home/ubuntu/presgen
            docker-compose pull
            docker-compose up -d --build
            docker-compose ps
          EOF

      - name: Health check
        run: |
          sleep 30
          curl -f http://${{ secrets.LIGHTSAIL_IP }}/health || exit 1

      - name: Notify on failure
        if: failure()
        run: |
          aws sns publish \
            --topic-arn ${{ secrets.SNS_TOPIC_ARN }} \
            --message "Deployment failed for commit ${{ github.sha }}"
```

**Deliverable:** GitHub Actions workflow configured

#### 6.2 Automated Testing (1 hour)

Create `tests/integration/test_deployment.py`:

```python
import pytest
import requests
import time

BASE_URL = "http://localhost"  # Override with production URL
AUTH = ("demo_user", "AllCloud2024!")

def test_health_endpoints():
    """Test all service health endpoints"""
    endpoints = [
        "/api/presgen/health",
        "/api/presgen-assess/health",
    ]
    for endpoint in endpoints:
        response = requests.get(f"{BASE_URL}{endpoint}", auth=AUTH)
        assert response.status_code == 200

def test_presentation_generation():
    """Test simple presentation generation"""
    payload = {
        "topic": "Test Presentation",
        "slides": 3,
        "use_ai_images": False
    }
    response = requests.post(
        f"{BASE_URL}/api/presgen/generate",
        json=payload,
        auth=AUTH
    )
    assert response.status_code in [200, 202]

def test_file_upload():
    """Test file upload to S3"""
    with open("test_file.pdf", "rb") as f:
        files = {"file": f}
        data = {"file_type": "exam_guides"}
        response = requests.post(
            f"{BASE_URL}/api/presgen-assess/files/upload",
            files=files,
            data=data,
            auth=AUTH
        )
    assert response.status_code == 200

def test_course_generation_with_video():
    """Test course generation and verify video URLs"""
    # This test verifies Issue #2 fix
    workflow_id = "test-workflow-id"
    skill_id = "test-skill-id"

    # Trigger generation
    response = requests.post(
        f"{BASE_URL}/api/presgen-assess/workflows/{workflow_id}/skills/{skill_id}/generate-course",
        auth=AUTH
    )
    assert response.status_code in [200, 202]

    # Poll for completion
    max_attempts = 60
    for _ in range(max_attempts):
        status_response = requests.get(
            f"{BASE_URL}/api/presgen-assess/workflows/{workflow_id}/courses/{response.json()['course_id']}/status",
            auth=AUTH
        )
        status_data = status_response.json()

        if status_data['status'] == 'completed':
            # VERIFY BUG FIX: Check that drive_download_url is present
            assert 'drive_download_url' in status_data
            assert status_data['drive_download_url'] is not None
            assert 'video_url' in status_data
            break

        time.sleep(2)
```

**Deliverable:** Integration tests passing

#### 6.3 Staging Environment (Optional, 1 hour)
```bash
# Create staging instance
aws lightsail create-instances \
  --instance-names presgen-staging \
  --availability-zone us-east-1a \
  --blueprint-id ubuntu_22_04 \
  --bundle-id small_2_0

# Deploy to staging first
# Run smoke tests
# Promote to production if tests pass
```

**Deliverable:** Staging environment (optional)

### Success Criteria
- [ ] GitHub Actions workflow running
- [ ] Automated tests passing
- [ ] Deployment automated
- [ ] Rollback procedure documented
- [ ] Notifications configured

---

## Phase 7: Monitoring and Observability
**Duration:** 3-4 hours
**Prerequisites:** Phase 6 complete
**Risk Level:** Low

### Objectives
- Configure CloudWatch dashboards
- Set up alarms and notifications
- Implement application metrics
- Configure log aggregation
- Set up cost monitoring

### Tasks

#### 7.1 CloudWatch Dashboard (1 hour)
```bash
# Create dashboard
aws cloudwatch put-dashboard \
  --dashboard-name PresGen-Production \
  --dashboard-body file://dashboard-config.json
```

**Dashboard Metrics:**
- System: CPU, Memory, Disk, Network
- Application: Request rate, error rate, response time
- Google APIs: Quota usage, error rate
- Database: Connections, query time
- Costs: Daily spend

**Deliverable:** CloudWatch dashboard

#### 7.2 Alarms and Notifications (1 hour)
```bash
# Create SNS topic
aws sns create-topic --name presgen-alerts

# Subscribe email
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:788159322332:presgen-alerts \
  --protocol email \
  --notification-endpoint ymeirovich@gmail.com

# Create alarms
aws cloudwatch put-metric-alarm \
  --alarm-name presgen-high-cpu \
  --alarm-description "Alert when CPU > 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/Lightsail \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:us-east-1:788159322332:presgen-alerts

# Memory alarm
# Disk alarm
# Error rate alarm
# Google API quota alarm
```

**Deliverable:** Alarms configured

#### 7.3 Application Metrics (1 hour)
```python
# Add to presgen-assess/src/service/middleware.py
from prometheus_client import Counter, Histogram, Gauge

# Metrics
request_count = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'])
active_workflows = Gauge('active_workflows', 'Number of active workflows')
google_api_calls = Counter('google_api_calls_total', 'Google API calls', ['api', 'status'])

# Middleware to track metrics
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    request_count.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()

    request_duration.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)

    return response
```

**Deliverable:** Application metrics exported

#### 7.4 Log Aggregation (1 hour)
```bash
# Install CloudWatch Logs agent
sudo wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i amazon-cloudwatch-agent.deb

# Configure agent
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config \
  -m ec2 \
  -s \
  -c file:///opt/aws/amazon-cloudwatch-agent/etc/config.json
```

**config.json:**
```json
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/home/ubuntu/presgen/logs/nginx/*.log",
            "log_group_name": "/presgen/nginx",
            "log_stream_name": "{instance_id}"
          },
          {
            "file_path": "/home/ubuntu/presgen/logs/presgen-core/*.log",
            "log_group_name": "/presgen/core",
            "log_stream_name": "{instance_id}"
          }
        ]
      }
    }
  }
}
```

**Deliverable:** Logs aggregated in CloudWatch

### Success Criteria
- [ ] Dashboard showing all key metrics
- [ ] Alarms triggering correctly
- [ ] Email notifications received
- [ ] Application metrics visible
- [ ] Logs searchable in CloudWatch

---

## Phase 8: Production Hardening and Optimization
**Duration:** 4-6 hours
**Prerequisites:** All previous phases complete
**Risk Level:** Low

### Objectives
- Performance optimization
- Database optimization
- Backup and disaster recovery
- Cost optimization
- Documentation finalization

### Tasks

#### 8.1 Performance Optimization (2 hours)

**8.1.1 Database Optimization**
```bash
# If using PostgreSQL
# Tune postgresql.conf
shared_buffers = 512MB
effective_cache_size = 1536MB
maintenance_work_mem = 128MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 2621kB
min_wal_size = 1GB
max_wal_size = 4GB

# Create indexes
CREATE INDEX idx_workflow_status ON workflows(status);
CREATE INDEX idx_course_skill_id ON generated_courses(skill_id);
CREATE INDEX idx_course_workflow_id ON generated_courses(workflow_id);
```

**8.1.2 Redis Optimization**
```bash
# Tune redis.conf
maxmemory 512mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

**8.1.3 nginx Optimization**
```nginx
# nginx.conf
worker_processes auto;
worker_connections 2048;
keepalive_timeout 65;
client_max_body_size 500M;
client_body_buffer_size 128k;
gzip on;
gzip_types text/plain text/css application/json application/javascript;
```

**Deliverable:** System tuned for performance

#### 8.2 Backup and Disaster Recovery (2 hours)

**8.2.1 Automated Backups**
```bash
# Create backup script
cat > /home/ubuntu/backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR=/tmp/presgen-backup-$DATE

# Stop services
cd /home/ubuntu/presgen
docker-compose stop

# Backup database
docker-compose exec -T postgres pg_dump -U presgen presgen_assess > $BACKUP_DIR/database.sql

# Backup data
tar -czf $BACKUP_DIR/data.tar.gz data/

# Upload to S3
aws s3 sync $BACKUP_DIR/ s3://presgen-prod-backups/$DATE/

# Restart services
docker-compose start

# Clean up
rm -rf $BACKUP_DIR

# Verify backup
aws s3 ls s3://presgen-prod-backups/$DATE/
EOF

chmod +x /home/ubuntu/backup.sh

# Schedule daily backups
crontab -e
# Add: 0 2 * * * /home/ubuntu/backup.sh
```

**8.2.2 Disaster Recovery Plan**
```bash
# Document recovery procedure
cat > /home/ubuntu/DISASTER_RECOVERY.md << 'EOF'
# Disaster Recovery Procedure

## Scenario 1: Instance Failure
1. Create new instance from latest snapshot
2. Attach static IP
3. Verify services

## Scenario 2: Data Corruption
1. Stop all services
2. Download latest backup from S3
3. Restore database
4. Restore data directory
5. Restart services

## Scenario 3: Complete AWS Failure
1. Run locally with Docker Compose
2. Use ngrok for public access
3. Point DNS to ngrok URL
EOF
```

**Deliverable:** Backups automated, DR plan documented

#### 8.3 Cost Optimization (1 hour)

**8.3.1 S3 Lifecycle Policies**
```json
{
  "Rules": [
    {
      "Id": "ArchiveOldBackups",
      "Status": "Enabled",
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "GLACIER"
        }
      ],
      "Expiration": {
        "Days": 90
      }
    }
  ]
}
```

**8.3.2 CloudWatch Log Retention**
```bash
# Set retention to 7 days for all log groups
for log_group in $(aws logs describe-log-groups --query 'logGroups[*].logGroupName' --output text); do
  aws logs put-retention-policy --log-group-name $log_group --retention-in-days 7
done
```

**8.3.3 Right-sizing**
```bash
# Monitor resource usage over 1 week
# Consider downgrading to small_2_0 if:
# - CPU < 40% average
# - Memory < 60% average
# - No performance issues

# Estimated savings: $10/month
```

**Deliverable:** Monthly cost reduced to minimum

#### 8.4 Documentation Finalization (1 hour)

**Update all documentation:**
- [x] CURRENT_ARCHITECTURE.md
- [ ] DEPLOYMENT_RUNBOOK.md
- [ ] OPERATIONS_MANUAL.md
- [ ] TROUBLESHOOTING_GUIDE.md
- [ ] COST_REPORT.md

**Deliverable:** Complete documentation suite

### Success Criteria
- [ ] System optimized for performance
- [ ] Backups running and verified
- [ ] DR plan tested
- [ ] Costs optimized
- [ ] Documentation complete and accurate

---

## Post-Deployment Operations

### Daily Tasks
- [ ] Check CloudWatch dashboard
- [ ] Review error logs
- [ ] Verify backups completed

### Weekly Tasks
- [ ] Review cost reports
- [ ] Check SSL certificate expiry
- [ ] Review security logs
- [ ] Test key workflows

### Monthly Tasks
- [ ] Test disaster recovery procedure
- [ ] Review and update documentation
- [ ] Check Google API quotas
- [ ] Review access logs for anomalies
- [ ] Rotate secrets (every 90 days)

### Quarterly Tasks
- [ ] Performance review and optimization
- [ ] Security audit
- [ ] Update dependencies
- [ ] Review and update DR plan

---

## Rollback Procedures

### Phase 3-4 Rollback (Deployment Issues)
```bash
# Stop AWS services
docker-compose down

# Run locally
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs
docker-compose up -d

# Verify local deployment
curl http://localhost/health
```

### Phase 5-8 Rollback (Configuration Issues)
```bash
# SSH to instance
ssh -i lightsail-key.pem ubuntu@<STATIC_IP>

# Restore from backup
cd /home/ubuntu/presgen
docker-compose down

# Download and restore last known good config
aws s3 cp s3://presgen-prod-backups/configs/last-good.tar.gz .
tar -xzf last-good.tar.gz

docker-compose up -d
```

---

## Success Metrics

### Technical Metrics
- **Uptime:** >99.5%
- **Response Time:** <2s average
- **Error Rate:** <1%
- **Deployment Time:** <15 minutes
- **Recovery Time Objective (RTO):** <1 hour
- **Recovery Point Objective (RPO):** <24 hours

### Business Metrics
- **Monthly Cost:** <$50
- **User Satisfaction:** >4/5
- **Demo Success Rate:** >95%

---

## Risk Assessment

| Phase | Risk Level | Mitigation |
|-------|-----------|------------|
| Phase 1 | Very Low | Documentation only |
| Phase 2 | Low | AWS infrastructure, easy to delete |
| Phase 3 | Medium | Can rollback to local immediately |
| Phase 4 | Medium | Comprehensive testing before Phase 5 |
| Phase 5 | Low | Non-breaking changes |
| Phase 6 | Low | Automated with safeguards |
| Phase 7 | Low | Monitoring only |
| Phase 8 | Low | Optimization and documentation |

---

## Timeline Summary

**Conservative Estimate:**
- Phase 1: 6 hours
- Phase 2: 4 hours
- Phase 3: 4 hours
- Phase 4: 3 hours
- Phase 5: 5 hours
- Phase 6: 4 hours
- Phase 7: 4 hours
- Phase 8: 6 hours

**Total: 36 hours (4-5 days)**

**Aggressive Estimate (with shortcuts):**
- Phases 1-4: 1 day
- Phases 5-6: 1 day
- Phases 7-8: 1 day

**Total: 20 hours (2.5 days)**

---

## Conclusion

This phased migration plan provides a structured, low-risk approach to moving PresGen to AWS Lightsail. Each phase has clear objectives, detailed tasks, and success criteria. The plan includes comprehensive rollback procedures and emphasizes testing at every stage.

**Next Steps:**
1. Review and approve this plan
2. Begin Phase 1 (Pre-Migration Preparation)
3. Execute phases sequentially
4. Document any deviations or issues
5. Update this plan based on learnings

**Questions or concerns?** Contact: ymeirovich@gmail.com

---

*Document Version: 3.0*
*Last Updated: November 12, 2025*
*Author: Claude (Senior Solutions Architect & DevOps Engineer)*
