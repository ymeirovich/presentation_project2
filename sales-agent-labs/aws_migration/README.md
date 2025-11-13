# PresGen AWS Migration - Complete Documentation

**Version:** 2.0
**Date:** October 29, 2025
**Status:** ✅ Production-Ready
**AWS Account:** 788159322332 (presgen_user)

---

## 📚 Documentation Index

This directory contains complete documentation for deploying PresGen to AWS Lightsail with production-grade security and reliability.

### Core Documentation

| Document | Purpose | When to Use |
|----------|---------|-------------|
| **[AWS_MIGRATION_PLAN.md](AWS_MIGRATION_PLAN.md)** | Complete migration strategy | Planning phase |
| **[DETAILED_DEPLOYMENT_PLAN.md](DETAILED_DEPLOYMENT_PLAN.md)** | Deep dive with 10 critical questions | Architecture decisions |
| **[DEPLOYMENT_README.md](DEPLOYMENT_README.md)** | Step-by-step deployment guide | During deployment |
| **[IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)** ⭐ | Security & reliability enhancements | Production hardening |

### Configuration & Setup

| Document | Purpose | When to Use |
|----------|---------|-------------|
| **[GOOGLE_AUTH_CONFIGURATION.md](GOOGLE_AUTH_CONFIGURATION.md)** | Google Cloud authentication | Setup Google APIs |
| **[GOOGLE_AUTH_SUMMARY.md](GOOGLE_AUTH_SUMMARY.md)** | Quick reference for Google auth | Quick lookup |
| **[FINAL_SOLUTION_403.md](FINAL_SOLUTION_403.md)** | Fix Google API 403 errors | Troubleshooting auth |
| **[FILE_UPLOAD_FIXES.md](FILE_UPLOAD_FIXES.md)** ⭐ | File upload API fixes & deployment | File upload issues |
| **[DEMO_CREDENTIALS.md](DEMO_CREDENTIALS.md)** | Access credentials & rate limits | Share with demo users |

### Issues & Troubleshooting

| Document | Purpose | When to Use |
|----------|---------|-------------|
| **[CRITICAL_ISSUES_ANALYSIS.md](CRITICAL_ISSUES_ANALYSIS.md)** ⚠️ | 7 critical issues you must address | Before deployment |
| **[FILE_UPLOAD_FIXES.md](FILE_UPLOAD_FIXES.md)** | File upload HTTP 500/405 errors | File upload problems |
| **[runbooks/DOCKER_CONTAINER_WONT_START.md](runbooks/DOCKER_CONTAINER_WONT_START.md)** | Fix Docker container issues | Container won't start |
| **[runbooks/DATABASE_LOCKED_ERRORS.md](runbooks/DATABASE_LOCKED_ERRORS.md)** | Fix database lock issues | "Database is locked" errors |

---

## 🚀 Quick Start (30 Minutes)

### Prerequisites

```bash
# 1. Verify AWS CLI configured
aws sts get-caller-identity
# Should show: User: presgen_user, Account: 788159322332

# 2. Set AWS region
aws configure set region us-east-1

# 3. Prepare secrets (Service Account only - no OAuth needed for headless)
mkdir -p secrets
cp presgen-service-account.json secrets/google-creds.json

# Note: OAuth is NOT required for headless deployment
# Service Account works for all Google APIs including Slides
# Set FORCE_SERVICE_ACCOUNT=true in environment
```

### Deploy

```bash
# 1. Make scripts executable
chmod +x deployment/*.sh
chmod +x scripts/*.sh

# 2. Deploy to AWS
./deployment/deploy-to-lightsail.sh presgen-demo small_2_0

# 3. Access application
# URL shown at end: http://YOUR_STATIC_IP
# Login: demo_user / AllCloud2024!
```

**Deployment Time:** 30-45 minutes
**Monthly Cost:** $22-24 (Lightsail medium_2_0 + S3 + CloudWatch)

---

## 📋 Complete Workflow

### Phase 1: Planning (READ THESE FIRST)

1. **[AWS_MIGRATION_PLAN.md](AWS_MIGRATION_PLAN.md)** - Understand the architecture
   - Cost analysis: $5-50/month options
   - Security implementation (HTTP Basic Auth)
   - Google Cloud authentication setup
   - Monitoring & alerts

2. **[DETAILED_DEPLOYMENT_PLAN.md](DETAILED_DEPLOYMENT_PLAN.md)** - Answer critical questions
   - Data persistence strategy
   - API secrets management
   - Database scaling plan
   - Google authentication strategy
   - Backup & disaster recovery

3. **[CRITICAL_ISSUES_ANALYSIS.md](CRITICAL_ISSUES_ANALYSIS.md)** ⚠️ - **MUST READ**
   - 7 critical issues you haven't considered
   - OAuth token expiry on headless server
   - Missing AWS region configuration
   - No rate limiting or DDoS protection
   - No SSL/TLS certificate
   - No backup verification
   - No API quota monitoring
   - No disaster recovery plan

### Phase 2: Pre-Deployment Setup

4. **[GOOGLE_AUTH_CONFIGURATION.md](GOOGLE_AUTH_CONFIGURATION.md)** - Set up Google Cloud
   - Service Account authentication (headless deployment)
   - Enable required APIs
   - Configure environment variables with FORCE_SERVICE_ACCOUNT=true
   - Test authentication locally

5. **Fix Critical Issues:**
   ```bash
   # Issue 1: Set AWS region
   aws configure set region us-east-1

   # Issue 2: Request Google API quota increase (DO NOW - takes 2-5 days)
   ./scripts/request-quota-increase.sh

   # Note: OAuth token refresh no longer required - using Service Account only
   ```

### Phase 3: Deployment

6. **[DEPLOYMENT_README.md](DEPLOYMENT_README.md)** - Execute deployment
   - Step-by-step deployment guide
   - Verification procedures
   - Maintenance operations
   - Security & reliability enhancements section

### Phase 4: Production Hardening

7. **[IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)** - Implement enhancements
   - **Rate Limiting** (1 hour) - Prevent API abuse
   - **SSL Certificate** (30 min) - Free Let's Encrypt for presgen.net
   - **Backup & Restore** (2 hours) - Verified backups with monthly tests
   - **API Quota Management** (1 hour) - Exponential backoff retry
   - **Troubleshooting Runbooks** - Quick fix guides

8. **Test Everything:**
   ```bash
   # Run comprehensive test suite
   ./scripts/test-enhancements.sh

   # Should pass all 13 tests
   ```

### Phase 5: Ongoing Operations

9. **Monitor & Maintain:**
   - Daily: Check CloudWatch dashboard
   - Weekly: Review backup logs
   - Monthly: Verify restore test passed
   - Every 90 days: Rotate service account keys
   - Before demo: Verify OAuth token not expired

10. **Troubleshooting:**
    - Docker issues: [runbooks/DOCKER_CONTAINER_WONT_START.md](runbooks/DOCKER_CONTAINER_WONT_START.md)
    - Database issues: [runbooks/DATABASE_LOCKED_ERRORS.md](runbooks/DATABASE_LOCKED_ERRORS.md)
    - Auth issues: [FINAL_SOLUTION_403.md](FINAL_SOLUTION_403.md)

---

## ⚡ Critical Actions (Do NOW)

These actions must be completed BEFORE deploying:

### 1. Set AWS Region (1 minute)

```bash
aws configure set region us-east-1
```

### 2. Request Google API Quota Increase (5 minutes, but takes 2-5 days to process)

```bash
./scripts/request-quota-increase.sh
```

**Why:** Default quotas may be insufficient for demos with multiple users. Request increases NOW.

**Note:** OAuth token refresh is no longer required. Service Account authentication works for all Google APIs including Slides in headless environments. Set `FORCE_SERVICE_ACCOUNT=true`.

---

## 🎯 Recommended Implementation Path

### Minimal Viable Deployment (30 minutes)

For quick demo deployment:

✅ Core deployment
✅ Google authentication
✅ Basic Auth security
⚠️ Skip enhancements (accept risks)

**Use case:** Quick internal demo, low usage, short-term

### Recommended Production Deployment (6 hours)

For reliable, secure demo:

✅ Core deployment
✅ Google authentication
✅ Rate limiting (nginx + application)
✅ SSL certificate (Let's Encrypt)
✅ Backup & restore with verification
✅ API quota management with retry
✅ CloudWatch monitoring

**Use case:** CTO demo, multiple users, medium-term (weeks-months)

### Complete Production Deployment (8 hours)

For mission-critical production:

✅ All recommended features above
✅ PostgreSQL instead of SQLite
✅ Multi-region backups
✅ Custom domain with SSL
✅ Enhanced monitoring & alerting
✅ Load testing & optimization
✅ Disaster recovery plan tested

**Use case:** Long-term production, SLA requirements, high usage

---

## 💰 Cost Breakdown

### Base Deployment (SQLite + Service Account)

| Component | Monthly Cost | Notes |
|-----------|--------------|-------|
| Lightsail (medium_2_0) | $20 | 2GB RAM, 2 vCPU, 60GB SSD |
| S3 Storage (optional) | $0.50 | ~5GB for backups (optional) |
| CloudWatch Logs | $1 | 5GB ingestion + retention |
| SNS Notifications | $0.05 | ~10 alerts/month |
| Data Transfer | $1 | First 1TB free, then $0.09/GB |
| **Subtotal** | **$22.55/month** | Local storage: $22/month |

### With Enhancements

| Enhancement | Additional Cost | Notes |
|-------------|-----------------|-------|
| SSL Certificate | $0 | Free (Let's Encrypt) |
| Rate Limiting | $0 | Software only |
| Backup Verification | $0 | Included in base cost |
| API Retry Logic | $0 | Software only |
| Image Cleanup Script | $0 | Automated cleanup (7-day retention) |
| **Total** | **$22.55/month** | No additional cost! |

### Optional Upgrades

| Upgrade | Additional Cost | When Needed |
|---------|-----------------|-------------|
| PostgreSQL (NOT RECOMMENDED) | +$15/month | Only if SQLite insufficient (>20 concurrent users) |
| Google Workspace | +$6-18/user/month | Service account for Workspace APIs |
| Custom domain | +$12/year | Professional URL |

**Note:** Staying on SQLite for simplicity. PostgreSQL migration path documented but not recommended unless necessary.

---

## 🔐 Security Checklist

Before going live with demo:

- [ ] AWS region configured: `us-east-1`
- [ ] Service account JSON deployed to `/secrets/google-creds.json`
- [ ] Environment variables configured with `FORCE_SERVICE_ACCOUNT=true`
- [ ] HTTP Basic Auth passwords set (htpasswd)
- [ ] Rate limiting configured (nginx + application)
- [ ] SSL certificate installed (if using custom domain)
- [ ] Secrets file permissions: `chmod 600 secrets/*`
- [ ] `.gitignore` includes `secrets/`, `token.json`, `*.pem`
- [ ] CloudWatch alarms active
- [ ] SNS email alerts confirmed
- [ ] Backup system tested and verified
- [ ] Restore procedure tested successfully
- [ ] Google APIs enabled (Slides, Drive, Forms, Sheets, Vertex AI)
- [ ] API quota increases requested (2-5 days before demo)
- [ ] Image cleanup cron job configured (7-day retention)
- [ ] SQLite backup script configured with optional S3 upload
- [ ] Troubleshooting runbooks printed/accessible

---

## 📊 Monitoring Dashboard

### Key Metrics to Watch

**System Health:**
- CPU Usage: Should be <60% average
- Memory Usage: Should be <80%
- Disk Usage: Should be <70%
- Network: Watch for unusual spikes

**Application Health:**
- Request Rate: Normal ~10-50 req/min
- Error Rate: Should be <1%
- Response Time: Average <2s
- Active Connections: <50

**Google Cloud:**
- API Quota Usage: <80% of limit
- API Errors: Should be 0
- Auth Failures: Should be 0

**Costs:**
- Daily: <$0.75
- Weekly: <$5.25
- Monthly: <$24

### Alerts to Set Up

```bash
# High CPU (>80% for 10 minutes)
aws cloudwatch put-metric-alarm \
  --alarm-name presgen-high-cpu \
  --metric-name CPUUtilization \
  --namespace AWS/Lightsail \
  --statistic Average \
  --period 600 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold

# High Memory (>90%)
# Database Locked Errors (>5 in 5 minutes)
# API Rate Limit Errors (>10 in 1 minute)
# Backup Failures
# Image Storage >5GB (cleanup needed)
# Cost Threshold ($30/month)
```

---

## 🆘 Emergency Procedures

### Demo Day Emergency Contacts

**Primary:** Yosi Meirovich (ymeirovich@gmail.com)
**AWS Support:** Premium support ticket
**Google Cloud Support:** <https://console.cloud.google.com/support>

### Common Emergency Scenarios

#### 1. Website Down During Demo

```bash
# Quick diagnosis (30 seconds)
curl -I http://YOUR_IP
ssh -i lightsail-key.pem ubuntu@YOUR_IP "docker-compose ps"

# Quick fix (1 minute)
ssh -i lightsail-key.pem ubuntu@YOUR_IP
docker-compose restart

# If still down, restore from snapshot (5 minutes)
aws lightsail create-instance-from-snapshot \
  --instance-snapshot-name presgen-pre-demo \
  --instance-name presgen-demo-restored
```

#### 2. Google API 403 Errors

```bash
# Check auth
docker logs presgen-core | grep -i "auth\|credential"

# Verify Service Account authentication
# Should see FORCE_SERVICE_ACCOUNT=true in environment
docker exec presgen-core env | grep FORCE_SERVICE_ACCOUNT

# If auth fails, use local fallback
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs
docker-compose up -d
ngrok http 3000  # Instant public URL
```

#### 3. Database Locked Errors

```bash
# Quick fix (30 seconds)
docker-compose restart presgen-assess
```

#### 4. Out of Memory

```bash
# Immediate (1 minute)
docker-compose restart

# If persistent (5 minutes)
# Reduce memory limits in docker-compose.yml
# OR upgrade instance to medium_2_0
```

### Fallback Plan

If AWS fails completely during demo:

```bash
# Run locally with ngrok (2 minutes)
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs
docker-compose -f docker-compose.local.yml up -d
ngrok http 3000

# Share ngrok URL: https://abc123.ngrok.io
# Use same credentials: demo_user / AllCloud2024!
```

---

## 📞 Support & Resources

### Documentation

- AWS Lightsail Docs: <https://docs.aws.amazon.com/lightsail/>
- Docker Docs: <https://docs.docker.com/>
- Google Cloud Auth: <https://cloud.google.com/docs/authentication>
- Let's Encrypt: <https://letsencrypt.org/docs/>

### Tools

- **AWS Console:** <https://console.aws.amazon.com/>
- **Google Cloud Console:** <https://console.cloud.google.com/>
- **Docker Hub:** <https://hub.docker.com/>

### Community

- **GitHub Issues:** Report bugs and issues
- **Email Support:** ymeirovich@gmail.com

---

## 📝 Version History

### v2.0 (October 29, 2025)

- ✅ Complete migration plan for AWS Lightsail
- ✅ Google Cloud dual authentication (service account + OAuth)
- ✅ Critical issues analysis (7 issues identified)
- ✅ Production-ready security enhancements
- ✅ Comprehensive implementation guide
- ✅ Troubleshooting runbooks
- ✅ Automated backup with verification
- ✅ Rate limiting (nginx + application)
- ✅ SSL/TLS setup guide for presgen.net
- ✅ API quota management with retry logic
- ✅ Complete testing framework

### v1.0 (October 28, 2025)

- Initial migration plan
- Basic deployment scripts
- Docker configuration
- nginx setup with Basic Auth

---

## ✅ Final Checklist

Before considering deployment complete:

### Planning Phase

- [ ] Read AWS_MIGRATION_PLAN.md
- [ ] Read DETAILED_DEPLOYMENT_PLAN.md
- [ ] Read CRITICAL_ISSUES_ANALYSIS.md
- [ ] Understand cost implications ($12-50/month)
- [ ] Understand Google auth requirements (dual authentication)
- [ ] Identify which enhancements to implement
- [ ] Schedule implementation time (3-8 hours)

### Pre-Deployment Phase

- [ ] AWS CLI configured with region us-east-1
- [ ] Service Account JSON file prepared locally
- [ ] Google API quota increases requested (2-5 days ahead)
- [ ] Domain DNS configured (if using SSL)
- [ ] Demo credentials documented
- [ ] Image cleanup script tested locally

### Deployment Phase

- [ ] Core deployment completed successfully
- [ ] All services running (`docker-compose ps`)
- [ ] Health checks passing
- [ ] Basic Auth working
- [ ] Google Service Account authentication tested
- [ ] Static IP allocated and documented
- [ ] SQLite database initialized

### Production Hardening Phase

- [ ] Rate limiting implemented and tested
- [ ] SSL certificate installed (if applicable)
- [ ] Backup system configured with verification
- [ ] Restore procedure tested successfully
- [ ] API retry logic implemented
- [ ] Monitoring and alerts configured
- [ ] SNS notifications confirmed

### Post-Deployment Phase

- [ ] Test suite passed: `./scripts/test-enhancements.sh`
- [ ] End-to-end demo tested successfully
- [ ] Troubleshooting runbooks printed/accessible
- [ ] Emergency procedures documented
- [ ] Monitoring dashboard configured
- [ ] Cost alerts configured
- [ ] Demo credentials shared with team

### Documentation Phase

- [ ] All documentation read and understood
- [ ] Team trained on accessing the demo
- [ ] Emergency contacts documented
- [ ] Maintenance schedule established
- [ ] Escalation procedures defined

---

**Status:** ✅ Ready for Production Deployment

**Next Steps:**
1. Review this README completely
2. Follow the workflow outlined above
3. Execute deployment with confidence
4. Monitor and maintain regularly

**Questions?** Contact ymeirovich@gmail.com

---

*Generated with precision by Claude Code* 🤖
