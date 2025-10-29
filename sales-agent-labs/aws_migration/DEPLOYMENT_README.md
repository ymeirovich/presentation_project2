# PresGen AWS Deployment - Complete Guide

**Version:** 2.0
**Date:** October 28, 2025
**Status:** Production-Ready

This document provides a complete overview of the PresGen AWS deployment solution, including all scripts, configurations, and procedures.

---

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [What's Included](#whats-included)
3. [Prerequisites](#prerequisites)
4. [Deployment Steps](#deployment-steps)
5. [Security & Reliability Enhancements](#security--reliability-enhancements) ⭐ **NEW**
6. [Maintenance Operations](#maintenance-operations)
7. [Troubleshooting](#troubleshooting)
8. [Cost Management](#cost-management)
9. [Security Best Practices](#security-best-practices)

---

## 🚀 Quick Start

### Deploy in 30 Minutes

```bash
# 1. Navigate to project root
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs

# 2. Configure environment
cp .env.template .env
# Edit .env with your API keys

# 3. Make scripts executable
chmod +x deployment/*.sh
chmod +x scripts/*.sh

# 4. Run deployment
./deployment/deploy-to-lightsail.sh presgen-demo small_2_0

# 5. Access application
# URL will be shown at end of deployment: http://YOUR_STATIC_IP
# Credentials: demo_user / AllCloud2024!
```

**Total Time:** 30-45 minutes
**Cost:** $10-15/month
**Complexity:** Low

---

## 📦 What's Included

### Docker Configuration

```
sales-agent-labs/
├── Dockerfile.core              # Core API (MCP Orchestrator)
├── presgen-assess/
│   └── Dockerfile               # Assessment API
├── presgen-ui/
│   └── Dockerfile               # Next.js Frontend
├── docker-compose.yml           # Multi-service orchestration
└── nginx/
    └── nginx.conf               # Reverse proxy + Basic Auth
```

**Features:**
- ✅ Multi-stage builds (optimized image sizes)
- ✅ Non-root users (security)
- ✅ Health checks (automatic recovery)
- ✅ Resource limits (prevent OOM)
- ✅ Volume persistence (data safety)

### Deployment Scripts

#### 1. [deployment/deploy-to-lightsail.sh](../deployment/deploy-to-lightsail.sh)

**Purpose:** Complete automated deployment to AWS Lightsail

**What it does:**
1. Creates S3 bucket for file storage
2. Creates Lightsail instance (Ubuntu 22.04)
3. Installs Docker, Docker Compose, AWS CLI
4. Uploads application code
5. Configures secrets and environment
6. Sets up HTTP Basic Authentication
7. Deploys all services
8. Verifies deployment

**Usage:**
```bash
./deployment/deploy-to-lightsail.sh [instance-name] [bundle-id]

# Examples:
./deployment/deploy-to-lightsail.sh presgen-demo small_2_0   # 2GB RAM ($10/month)
./deployment/deploy-to-lightsail.sh presgen-demo medium_2_0  # 4GB RAM ($20/month)
```

**Output:**
- `lightsail-key.pem` - SSH key for instance access
- `aws-resources.env` - Resource identifiers (IP, bucket, etc.)

---

### Maintenance Scripts

#### 2. [scripts/backup.sh](../scripts/backup.sh)

**Purpose:** Complete backup solution (database, files, config, volumes)

**Features:**
- SQLite/PostgreSQL database backups
- User uploads and generated files
- Docker volumes
- Configuration files
- Automatic S3 upload
- Retention policy (30 days)
- Lightsail snapshots

**Usage:**
```bash
./scripts/backup.sh [backup-type]

# Full backup (everything)
./scripts/backup.sh full

# Database only
./scripts/backup.sh database

# Files only
./scripts/backup.sh files

# Instance snapshot
./scripts/backup.sh snapshot
```

**Schedule with cron:**
```bash
# Daily database backup at 2 AM
0 2 * * * /home/ubuntu/presgen/scripts/backup.sh database

# Weekly full backup on Sunday at 3 AM
0 3 * * 0 /home/ubuntu/presgen/scripts/backup.sh full
```

**Backup Locations:**
- Local: `/home/ubuntu/presgen/backups/`
- S3: `s3://presgen-demo-files/backups/`
- Snapshots: AWS Lightsail console

---

#### 3. [scripts/update.sh](../scripts/update.sh)

**Purpose:** Safe, reversible application updates

**Features:**
- Automatic pre-update backups
- Code updates (git pull + rebuild)
- Dependency updates (pip, npm)
- Security patches (system packages)
- Database migrations
- Service health verification
- Rollback capability

**Usage:**
```bash
./scripts/update.sh [update-type]

# Update application code
./scripts/update.sh code

# Update Python/Node dependencies
./scripts/update.sh deps

# Update configuration
./scripts/update.sh config

# Security patches
./scripts/update.sh security

# Full update (all of the above)
./scripts/update.sh full

# Rollback to previous version
./scripts/update.sh rollback [timestamp]
```

**Safety Features:**
- ✅ Automatic backup before update
- ✅ Health checks after update
- ✅ One-command rollback
- ✅ Configuration versioning

---

#### 4. [scripts/monitor.sh](../scripts/monitor.sh)

**Purpose:** Real-time monitoring and metrics

**Features:**
- Live dashboard (auto-refresh)
- Service health checks
- Resource usage (CPU, memory, disk)
- Active workflows
- Recent errors
- Request metrics
- Alert detection
- Metrics export (JSON)

**Usage:**
```bash
./scripts/monitor.sh [mode]

# Live dashboard (refreshes every 30 seconds)
./scripts/monitor.sh dashboard

# Service health only
./scripts/monitor.sh health

# Resource usage only
./scripts/monitor.sh resources

# Active workflows
./scripts/monitor.sh workflows

# Recent errors
./scripts/monitor.sh errors

# View logs for specific container
./scripts/monitor.sh logs presgen-core 100

# Export metrics to JSON
./scripts/monitor.sh export
```

**Dashboard Preview:**
```
╔═══════════════════════════════════════════════════════════════╗
║          PresGen Monitoring Dashboard                         ║
║          2025-10-28 14:30:00                                  ║
╚═══════════════════════════════════════════════════════════════╝

=== SERVICE HEALTH ===
Core API (8080):       ✓ Healthy
Assess API (8000):     ✓ Healthy
Frontend (3000):       ✓ Healthy
Redis:                 ✓ Healthy
nginx:                 ✓ Running

=== RESOURCE USAGE ===
Memory: 1.2GB / 2.0GB (60%)
Disk: 12GB / 40GB (30%)
CPU Load: 0.5 (2 CPUs)

=== ACTIVE WORKFLOWS ===
wf_abc123 - Step 5/11 (Gap Analysis)
wf_def456 - Step 2/11 (Generating Assessment)

=== RECENT ERRORS ===
No recent errors

Refreshing in 30 seconds...
```

---

#### 5. [scripts/scale.sh](../scripts/scale.sh)

**Purpose:** Vertical scaling and resource optimization

**Features:**
- Instance size upgrade/downgrade
- Auto-scaling based on metrics
- Resource optimization
- Cost estimation
- Pre-scaling snapshots

**Usage:**
```bash
./scripts/scale.sh [action] [parameters]

# Show current status and recommendations
./scripts/scale.sh status

# Scale up to 4GB RAM
./scripts/scale.sh up medium_2_0

# Scale down to 1GB RAM
./scripts/scale.sh down micro_2_0

# Auto-scale based on current metrics
./scripts/scale.sh auto

# Optimize resources (clean up, restart)
./scripts/scale.sh optimize

# Estimate costs for bundle
./scripts/scale.sh cost medium_2_0
```

**Auto-Scaling Logic:**
- Memory > 85% → Scale up
- Disk > 85% → Scale up
- Memory < 40% AND Disk < 40% → Recommend scale down

---

## 📋 Prerequisites

### Local Machine

- **AWS CLI** (v2+)
  ```bash
  aws --version
  # Install: https://aws.amazon.com/cli/
  ```

- **Docker** (v20+)
  ```bash
  docker --version
  # Install: https://www.docker.com/get-started
  ```

- **SSH Client**
  ```bash
  ssh -V
  ```

- **Git** (optional, for code updates)
  ```bash
  git --version
  ```

### AWS Account

- **IAM User** with permissions:
  - Lightsail (full access)
  - S3 (create buckets, upload files)
  - CloudWatch (create alarms)
  - SNS (publish messages)

- **AWS CLI Configured:**
  ```bash
  aws configure
  # Enter Access Key, Secret Key, Region (us-east-1)
  ```

### API Keys & Credentials

Required environment variables in `.env`:

```bash
# OpenAI API Key (for assessment generation)
OPENAI_API_KEY=sk-...

# Google Cloud Service Account JSON
# Place file in: secrets/google-creds.json

# Google OAuth Token (optional, for user-specific access)
# Place file in: secrets/google-oauth-token.json

# ElevenLabs API Key (optional, for text-to-speech)
ELEVENLABS_API_KEY=...
```

---

## 🚀 Deployment Steps

### Step 1: Configure Environment

```bash
# Copy template
cp .env.template .env

# Edit with your keys
vi .env

# Required fields:
OPENAI_API_KEY=sk-...
AWS_REGION=us-east-1

# Optional but recommended:
USE_AI_IMAGES=true
PRESGEN_USE_MOCK=false
```

### Step 2: Prepare Secrets

```bash
# Create secrets directory
mkdir -p secrets

# Add Google Cloud service account JSON
cp /path/to/your/google-creds.json secrets/

# Verify
ls -lh secrets/
```

### Step 3: Make Scripts Executable

```bash
chmod +x deployment/*.sh
chmod +x scripts/*.sh
```

### Step 4: Run Deployment

```bash
./deployment/deploy-to-lightsail.sh presgen-demo small_2_0
```

**Expected Output:**
```
[INFO] Starting PresGen deployment to AWS Lightsail...
[INFO] Instance: presgen-demo
[INFO] Size: small_2_0
[INFO] Region: us-east-1

[INFO] Checking prerequisites...
[INFO] Prerequisites OK
[INFO] Creating S3 bucket...
[INFO] S3 bucket created: presgen-demo-files-20251028_143000
[INFO] Creating Lightsail instance: presgen-demo...
[INFO] Waiting for instance to be running...
[INFO] Instance created with static IP: 54.123.45.67
...
[INFO] =====================================
[INFO] DEPLOYMENT COMPLETE!
[INFO] =====================================

Access URL: http://54.123.45.67
Credentials:
  demo_user / AllCloud2024!
  cto_user / CTODemo2024!
  yosi_user / YosiDemo2024!

SSH Access:
  ssh -i lightsail-key.pem ubuntu@54.123.45.67
```

### Step 5: Verify Deployment

```bash
# Test health endpoint
curl http://YOUR_STATIC_IP/health
# Expected: healthy

# Test with authentication
curl -u demo_user:AllCloud2024! http://YOUR_STATIC_IP/
# Expected: HTML content

# SSH into instance
ssh -i lightsail-key.pem ubuntu@YOUR_STATIC_IP

# Check services
docker-compose ps
# All services should be "Up"
```

### Step 6: Configure Monitoring (Optional)

```bash
# Set up CloudWatch alarms
# (Done automatically by deployment script)

# Verify alarms
aws cloudwatch describe-alarms \
  --alarm-names presgen-cost-alert presgen-instance-health presgen-high-cpu

# Set up cron jobs for backups
ssh -i lightsail-key.pem ubuntu@YOUR_STATIC_IP
crontab -e

# Add:
0 2 * * * /home/ubuntu/presgen/scripts/backup.sh database
0 3 * * 0 /home/ubuntu/presgen/scripts/backup.sh full
```

---

## 🔒 Security & Reliability Enhancements

**NEW:** Comprehensive security and reliability features to ensure production-ready deployment.

### Overview

Based on critical issues analysis, the following enhancements are recommended for production deployment:

| Enhancement | Priority | Implementation Time | Impact |
|-------------|----------|---------------------|--------|
| Rate Limiting | 🔴 High | 1 hour | Prevent API abuse, control costs |
| SSL/TLS Certificate | 🟡 Medium | 30 min | Security, professional appearance |
| Backup & Restore | 🔴 High | 2 hours | Data protection, disaster recovery |
| API Quota Management | 🟡 Medium | 1 hour | Prevent demo failures |
| Troubleshooting Runbooks | 🟢 Low | Done | Quick issue resolution |

**Total Implementation Time:** ~5 hours for complete production hardening

### Quick Links

- **Complete Guide:** [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) - Detailed step-by-step implementation
- **Critical Issues Analysis:** [CRITICAL_ISSUES_ANALYSIS.md](CRITICAL_ISSUES_ANALYSIS.md) - Full risk assessment
- **Runbooks:**
  - [Docker Container Won't Start](runbooks/DOCKER_CONTAINER_WONT_START.md)
  - [Database Locked Errors](runbooks/DATABASE_LOCKED_ERRORS.md)

### 1. Rate Limiting (RECOMMENDED)

**Problem:** Unlimited API requests can lead to cost overruns and service degradation.

**Solution:** Implement multi-layer rate limiting:

```bash
# Quick setup (30 minutes)
# 1. Copy enhanced nginx config
cp nginx/nginx.conf nginx/nginx.conf.backup
cp aws_migration/IMPLEMENTATION_GUIDE.md:nginx-config nginx/nginx.conf

# 2. Install application-level rate limiting
echo "slowapi==0.1.9" >> presgen-assess/requirements.txt
docker-compose build --no-cache presgen-assess

# 3. Restart services
docker-compose restart nginx presgen-assess

# 4. Test rate limiting
./scripts/test-enhancements.sh
```

**Limits Applied:**
- Presentation generation: 10 requests/minute + burst of 3
- General API calls: 60 requests/minute + burst of 10
- UI page loads: 120 requests/minute + burst of 20
- Max concurrent connections: 10 per IP

**See:** [IMPLEMENTATION_GUIDE.md - Section 1](IMPLEMENTATION_GUIDE.md#1-rate-limiting) for complete implementation

### 2. SSL/TLS Certificate (For presgen.net)

**Problem:** HTTP-only connection is insecure and unprofessional for demos.

**Solution:** Free SSL certificate using Let's Encrypt:

```bash
# Prerequisites: DNS configured for presgen.net → Your Lightsail IP

# Setup (20 minutes)
ssh -i lightsail-key.pem ubuntu@YOUR_IP
cd /home/ubuntu/presgen

# Run SSL setup script
./deployment/setup-ssl.sh

# Certificate will auto-renew every 90 days
```

**Benefits:**
- ✅ HTTPS encryption (protects credentials in transit)
- ✅ Professional appearance (no "Not Secure" warnings)
- ✅ Free forever (Let's Encrypt)
- ✅ Auto-renewal (no maintenance)

**See:** [IMPLEMENTATION_GUIDE.md - Section 2](IMPLEMENTATION_GUIDE.md#2-ssltls-certificate-for-presgennet) for complete setup

### 3. Enhanced Backup & Restore System (CRITICAL)

**Problem:** Current backups aren't verified and may fail silently.

**Solution:** Automated backup system with verification:

```bash
# Setup (30 minutes)
ssh -i lightsail-key.pem ubuntu@YOUR_IP

# 1. Install enhanced backup scripts
cd /home/ubuntu/presgen
chmod +x scripts/backup-with-verification.sh
chmod +x scripts/restore.sh

# 2. Create SNS topic for alerts
./deployment/setup-backups.sh
# Check email and confirm SNS subscription

# 3. Test backup system
./scripts/backup-with-verification.sh

# 4. Verify backup in S3
aws s3 ls s3://presgen-backups-788159322332/backups/

# Backups run automatically at 2 AM daily
```

**Features:**
- ✅ Daily automated backups with verification
- ✅ SHA-256 checksum validation
- ✅ Monthly restore tests (1st of each month)
- ✅ Email alerts on success/failure
- ✅ 30-day retention
- ✅ One-command restore: `./scripts/restore.sh latest`

**See:** [IMPLEMENTATION_GUIDE.md - Section 3](IMPLEMENTATION_GUIDE.md#3-backup-and-restore-system) for complete guide

### 4. Google API Quota Management (RECOMMENDED)

**Problem:** Google APIs have rate limits that can cause demo failures.

**Solution:** Exponential backoff retry + quota monitoring:

```bash
# Setup (45 minutes)

# 1. Add retry logic to codebase
# Copy google_api_retry.py to src/agent/
cp aws_migration/IMPLEMENTATION_GUIDE.md:retry-module src/agent/google_api_retry.py

# 2. Update slides agent to use retry logic
# (See IMPLEMENTATION_GUIDE.md for code changes)

# 3. Request quota increase (DO THIS NOW - takes 2-5 days)
./scripts/request-quota-increase.sh

# 4. Set up quota monitoring
chmod +x scripts/monitor-quotas.sh
./scripts/monitor-quotas.sh  # Run manually to check

# 5. Add to cron for daily checks
echo "0 8 * * * /home/ubuntu/presgen/scripts/monitor-quotas.sh" | crontab -
```

**Features:**
- ✅ Automatic retry on 429 (rate limit exceeded) errors
- ✅ Exponential backoff (1s → 2s → 4s → 8s → 16s → 32s → 60s max)
- ✅ Quota monitoring scripts
- ✅ Email alerts when quota exceeded
- ✅ Request quota increase automation

**See:** [IMPLEMENTATION_GUIDE.md - Section 4](IMPLEMENTATION_GUIDE.md#4-google-cloud-api-quota-management) for complete implementation

### 5. Troubleshooting Runbooks (INCLUDED)

**Problem:** When things break during a demo, you need instant solutions.

**Solution:** Step-by-step runbooks for common issues:

#### Available Runbooks:

**[Docker Container Won't Start](runbooks/DOCKER_CONTAINER_WONT_START.md)**
- Missing environment variables → Fix in 2 minutes
- Port conflicts → Fix in 1 minute
- Missing secrets files → Fix in 5 minutes
- Out of memory → Fix in 10 minutes
- Complete reset procedure

**[Database Locked Errors](runbooks/DATABASE_LOCKED_ERRORS.md)**
- Quick fix (restart service) → 2 minutes
- Enable WAL mode → 5 minutes
- Add retry logic → 30 minutes
- Migrate to PostgreSQL → 2 hours

**Quick Access During Demo:**
```bash
# Print runbooks or keep them open in browser
open aws_migration/runbooks/DOCKER_CONTAINER_WONT_START.md
open aws_migration/runbooks/DATABASE_LOCKED_ERRORS.md
```

### Priority Recommendation

**Before Demo (Essential):**
1. ✅ Request Google API quota increase (do NOW - takes 2-5 days)
2. ✅ Refresh OAuth token (see [CRITICAL_ISSUES_ANALYSIS.md](CRITICAL_ISSUES_ANALYSIS.md))
3. ✅ Set AWS region: `aws configure set region us-east-1`
4. ✅ Set up backup system with verification
5. ✅ Print troubleshooting runbooks for quick reference

**During Deployment (Recommended):**
6. ✅ Implement rate limiting (nginx + application)
7. ✅ Set up SSL certificate (if using presgen.net domain)
8. ✅ Add Google API retry logic
9. ✅ Configure SNS alerts

**After Deployment (Testing):**
10. ✅ Run test suite: `./scripts/test-enhancements.sh`
11. ✅ Test backup and restore manually
12. ✅ Verify rate limits working
13. ✅ Check SSL certificate

### Implementation Checklist

Use this checklist to track your implementation progress:

- [ ] Rate limiting configured (nginx + application)
- [ ] SSL certificate installed and auto-renewing
- [ ] Backup system with verification running daily
- [ ] Restore procedure tested successfully
- [ ] Google API retry logic implemented
- [ ] Google API quota increase requested
- [ ] SNS alerts configured and email confirmed
- [ ] CloudWatch alarms active
- [ ] Troubleshooting runbooks printed/bookmarked
- [ ] Test suite passed: `./scripts/test-enhancements.sh`
- [ ] OAuth token refreshed (within last 7 days)
- [ ] AWS region configured: `us-east-1`
- [ ] Database WAL mode enabled
- [ ] Monitoring scripts in cron
- [ ] Demo credentials documented

### Testing All Enhancements

After implementing enhancements, run the comprehensive test suite:

```bash
# On Lightsail instance
cd /home/ubuntu/presgen
./scripts/test-enhancements.sh
```

**Expected Output:**
```text
TEST: Rate Limiting - API Generation Endpoint
✅ PASS: Rate limiting working - got 429 on request 14

TEST: SSL Certificate
✅ PASS: HTTPS enabled and working

TEST: Backup System
✅ PASS: Backup script is executable
✅ PASS: S3 backup bucket exists
✅ PASS: Backup cron job configured

TEST: Google API Retry Logic
✅ PASS: Google API retry module loaded successfully

TEST: Application-Level Rate Limiting
✅ PASS: slowapi installed in presgen-assess

TEST: Database WAL Mode
✅ PASS: Database using WAL mode (better concurrency)

TEST: SNS Alert Topic
✅ PASS: SNS alert topic exists
✅ PASS: Email subscription configured

TEST: Service Health Checks
✅ PASS: presgen-ui health check passing
✅ PASS: presgen-assess health check passing
✅ PASS: presgen-core health check passing

============================================
TEST SUMMARY
============================================
Passed: 13
Failed: 0
Total:  13

✅ ALL TESTS PASSED!
```

### Cost Impact

**Additional Costs from Enhancements:**

| Enhancement | Monthly Cost | Notes |
|-------------|--------------|-------|
| Rate Limiting | $0 | No additional cost |
| SSL Certificate | $0 | Free (Let's Encrypt) |
| S3 Backups | ~$0.50 | 30 days retention, ~5GB |
| SNS Alerts | ~$0.05 | ~10 emails/month |
| CloudWatch Logs | ~$1 | 5GB ingestion + 30 days retention |
| Google API Retry | $0 | Software only |
| **Total** | **~$1.55/month** | Minimal cost for major reliability improvement |

**Cost vs. Benefit:**
- Investment: ~$1.55/month
- Protection: Prevents data loss, API overuse, demo failures
- ROI: Invaluable for production demo

### Getting Help

If you encounter issues during implementation:

1. **Check the guides:**
   - [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) - Complete implementation steps
   - [CRITICAL_ISSUES_ANALYSIS.md](CRITICAL_ISSUES_ANALYSIS.md) - Issue analysis
   - [Runbooks](runbooks/) - Troubleshooting procedures

2. **Review logs:**
   ```bash
   docker-compose logs --tail=100 presgen-core
   cat /var/log/nginx/error.log
   ```

3. **Contact:** ymeirovich@gmail.com

---

## 🔧 Maintenance Operations

### Daily Operations

#### View Logs

```bash
# SSH into instance
ssh -i lightsail-key.pem ubuntu@YOUR_STATIC_IP

# View all logs
cd /home/ubuntu/presgen
docker-compose logs -f

# View specific service
docker-compose logs -f presgen-assess

# Search for errors
docker-compose logs | grep -i error
```

#### Restart Services

```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart presgen-core

# Full rebuild
docker-compose down
docker-compose up -d --build
```

### Weekly Operations

#### Backup

```bash
# Run full backup
./scripts/backup.sh full

# Verify backups in S3
aws s3 ls s3://presgen-demo-files/backups/ --recursive

# Check Lightsail snapshots
aws lightsail get-instance-snapshots
```

#### Update

```bash
# Check for updates
./scripts/update.sh status

# Apply security patches
./scripts/update.sh security

# Update application code (if changes)
./scripts/update.sh code
```

### Monthly Operations

#### Review Costs

```bash
# Check current month costs
aws ce get-cost-and-usage \
  --time-period Start=$(date +%Y-%m-01),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics BlendedCost

# Check CloudWatch alarms
aws cloudwatch describe-alarms
```

#### Optimize Resources

```bash
# Clean up old data
./scripts/scale.sh optimize

# Review scaling needs
./scripts/scale.sh status
```

#### Rotate Credentials

```bash
# Update Basic Auth passwords
ssh -i lightsail-key.pem ubuntu@YOUR_STATIC_IP
sudo htpasswd /etc/nginx/auth/.htpasswd demo_user
docker-compose restart nginx

# Rotate API keys (update .env and restart)
```

---

## 🐛 Troubleshooting

### Common Issues

#### 1. Service Won't Start

**Symptoms:**
```bash
docker-compose ps
# Shows "Exit 1" or "Restarting"
```

**Solution:**
```bash
# Check logs
docker-compose logs presgen-core | tail -50

# Common causes:
# - Missing environment variables
# - Database connection error
# - Port already in use

# Fix: Rebuild and restart
docker-compose down
docker-compose up -d --build
```

#### 2. Out of Memory

**Symptoms:**
```bash
# Services crash randomly
# "Killed" in logs
```

**Solution:**
```bash
# Check memory usage
./scripts/monitor.sh resources

# Add swap
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# OR scale up instance
./scripts/scale.sh up medium_2_0
```

#### 3. Database Locked Errors

**Symptoms:**
```
sqlite3.OperationalError: database is locked
```

**Solution:**
```bash
# Option A: Add retry logic (already in code)

# Option B: Migrate to PostgreSQL
# Edit docker-compose.yml, uncomment postgres service
docker-compose up -d postgres
# Update .env:
DATABASE_URL=postgresql+asyncpg://presgen:PASSWORD@postgres:5432/presgen_assess
```

#### 4. 502 Bad Gateway

**Symptoms:**
nginx returns 502 error

**Solution:**
```bash
# Check if services are running
docker-compose ps

# Check service health
curl http://localhost:8000/api/v1/health
curl http://localhost:8080/health

# Restart services
docker-compose restart
```

### Emergency Procedures

#### Restore from Backup

```bash
# 1. Stop services
docker-compose down

# 2. Download backup from S3
aws s3 cp s3://presgen-demo-files/backups/database/presgen_assess_TIMESTAMP.sql.gz ./

# 3. Restore database
gunzip presgen_assess_TIMESTAMP.sql.gz
sqlite3 data/assess/presgen_assess.db < presgen_assess_TIMESTAMP.sql

# 4. Start services
docker-compose up -d
```

#### Restore from Lightsail Snapshot

```bash
# 1. Create new instance from snapshot
aws lightsail create-instances-from-snapshot \
  --instance-names presgen-demo-restored \
  --instance-snapshot-name presgen-demo-snapshot-TIMESTAMP \
  --availability-zone us-east-1a \
  --bundle-id small_2_0

# 2. Attach static IP
aws lightsail attach-static-ip \
  --static-ip-name presgen-demo-ip \
  --instance-name presgen-demo-restored

# 3. Verify
ssh -i lightsail-key.pem ubuntu@YOUR_STATIC_IP
docker-compose ps
```

---

## 💰 Cost Management

### Monthly Cost Breakdown

**Minimum Configuration ($10-12/month):**
```
Lightsail 2GB:      $10.00
S3 Storage:         $0.50
CloudWatch Alarms:  $0.50
SNS Notifications:  $0.50
---------------------------
Total:              $11.50/month
```

**Recommended Configuration ($15-20/month):**
```
Lightsail 2GB:      $10.00
S3 Storage:         $1.00
Snapshots (weekly): $1.20
CloudWatch:         $3.00
SNS (Email + SMS):  $1.00
---------------------------
Total:              $16.20/month
```

**Production Configuration ($45-50/month):**
```
Lightsail 4GB:      $20.00
PostgreSQL DB:      $15.00
S3 Storage:         $2.00
Snapshots (daily):  $2.40
CloudWatch Logs:    $5.00
Secrets Manager:    $2.00
---------------------------
Total:              $46.40/month
```

### Cost Optimization Tips

1. **Stop instance when not in use:**
   ```bash
   aws lightsail stop-instance --instance-name presgen-demo
   # Cost while stopped: ~$0.60/month (storage only)
   ```

2. **Disable AI image generation:**
   ```bash
   # Edit .env
   USE_AI_IMAGES=false
   # Save $5-10/month in Vertex AI costs
   ```

3. **Use S3 lifecycle policies:**
   - Delete old uploads after 90 days
   - Move outputs to Glacier after 30 days

4. **Limit log retention:**
   - CloudWatch: 7 days (instead of 30)
   - Local logs: Rotate weekly

---

## 🔐 Security Best Practices

### Access Control

1. **HTTP Basic Authentication** (Implemented)
   - Users: demo_user, cto_user, yosi_user
   - Passwords stored in `/etc/nginx/auth/.htpasswd`

2. **SSH Key Authentication** (Implemented)
   - Key file: `lightsail-key.pem`
   - Disable password authentication

3. **IP Whitelisting** (Optional)
   ```nginx
   # Add to nginx.conf
   allow 1.2.3.4;  # AllCloud office
   deny all;
   ```

### Data Security

1. **Secrets Management**
   - Never commit `.env` to git
   - Use AWS Secrets Manager for production
   - Rotate API keys every 90 days

2. **Database Encryption**
   - SQLite: File-level encryption
   - PostgreSQL: Enable SSL connections

3. **Network Security**
   - HTTPS/SSL (add Let's Encrypt certificate)
   - Close unused ports
   - Use VPC for production

### Monitoring

1. **CloudWatch Alarms** (Configured)
   - Cost > $10/month
   - CPU > 80%
   - Disk > 80%
   - Instance health

2. **Log Analysis**
   - Monitor for failed login attempts
   - Track API error rates
   - Alert on suspicious activity

---

## 📞 Support & Contact

### Documentation

- [AWS Migration Plan](./AWS_MIGRATION_PLAN.md) - Full migration strategy
- [Detailed Deployment Plan](./DETAILED_DEPLOYMENT_PLAN.md) - Critical questions & considerations
- [Docker Configuration](../docker-compose.yml) - Container orchestration

### Scripts Reference

| Script | Purpose | Location |
|--------|---------|----------|
| deploy-to-lightsail.sh | Full deployment automation | `deployment/` |
| backup.sh | Backup all data | `scripts/` |
| update.sh | Safe updates & rollback | `scripts/` |
| monitor.sh | Real-time monitoring | `scripts/` |
| scale.sh | Instance scaling | `scripts/` |

### Contact Information

- **Email:** ymeirovich@gmail.com
- **Phone:** +972527563792
- **Alerts:** Configured via SNS (email + SMS)

---

## ✅ Deployment Checklist

Use this checklist to track your deployment progress:

### Pre-Deployment
- [ ] AWS CLI installed and configured
- [ ] Docker installed on local machine
- [ ] API keys obtained (OpenAI, Google Cloud)
- [ ] `.env` file configured
- [ ] Google service account JSON added to `secrets/`
- [ ] Scripts made executable

### Deployment
- [ ] S3 bucket created
- [ ] Lightsail instance created
- [ ] Static IP allocated
- [ ] Application deployed
- [ ] Basic authentication configured
- [ ] Services verified (all healthy)

### Post-Deployment
- [ ] Backup cron jobs configured
- [ ] CloudWatch alarms verified
- [ ] SNS email confirmed
- [ ] Monitoring dashboard tested
- [ ] Documentation reviewed
- [ ] Demo credentials shared with team

### First Week
- [ ] Monitor costs daily
- [ ] Check service health daily
- [ ] Review logs for errors
- [ ] Test backup/restore procedure
- [ ] Load test with expected demo traffic

---

**Deployment Status:** ✅ Ready for Production
**Last Updated:** October 28, 2025
**Maintainer:** Yitz Meirovich (ymeirovich@gmail.com)

---

*This documentation is part of the PresGen AWS Migration project. For questions or issues, contact the maintainer.*
