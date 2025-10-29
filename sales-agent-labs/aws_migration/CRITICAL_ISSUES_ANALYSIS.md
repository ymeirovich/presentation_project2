# Critical Issues Analysis - PresGen AWS Migration

**Date:** October 29, 2025
**AWS Account:** 788159322332
**User:** presgen_user (Administrator Access)
**AWS CLI:** ✅ Configured and working

---

## ✅ What You've Already Considered

Based on the migration and deployment plans, you've already addressed:

- ✅ Google Cloud authentication (service account + OAuth)
- ✅ Cost optimization (Lightsail vs EC2)
- ✅ Security (HTTP Basic Auth)
- ✅ Backup strategy
- ✅ Monitoring and alerts
- ✅ Database limitations (SQLite)
- ✅ GPU workarounds for video/avatar generation
- ✅ Storage strategy (S3 + local)

---

## ⚠️ Critical Issues You HAVEN'T Considered

### 1. **OAuth Token Expiry on Headless Server** 🔴 CRITICAL

**The Problem:**
Your `token.json` OAuth token will eventually expire (refresh token expires after ~6 months of inactivity or if revoked). When this happens on a headless AWS server, there's **no way to regenerate it** because the OAuth flow requires:
- Interactive browser
- User consent screen
- Redirect to localhost

**Impact:**
- ✅ Service account APIs work (Vertex AI, Gemini)
- ❌ Workspace APIs fail (can't create Slides, Forms, Sheets)
- **Demo breaks completely** - no way to generate presentations

**Current Risk Level:**
- Token generated: Recently (October 2025)
- Expected expiry: ~April 2026 (6 months)
- Risk: **HIGH** if demo runs beyond April 2026

**Solutions:**

#### Option A: Pre-Deployment Token Refresh (RECOMMENDED)
```bash
# Before deploying, ensure token is fresh
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs

# Force token refresh
rm token.json

# Regenerate (opens browser for OAuth flow)
python3 -m src.cli.main generate --topic "Test" --slides 3

# Verify token has refresh_token
cat token.json | jq '.refresh_token'
# Should show: "1//0gXY..."

# Now deploy to AWS
./deployment/deploy-to-lightsail.sh presgen-demo small_2_0
```

#### Option B: Token Refresh Service (Long-term Solution)
```python
# Add to src/agent/slides_google.py

import time
from google.auth.transport.requests import Request

def ensure_fresh_token():
    """Proactively refresh OAuth token before expiry."""
    token_path = os.getenv("OAUTH_TOKEN_PATH", "token.json")

    if not pathlib.Path(token_path).exists():
        return False

    creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    # Check if token expires in next 7 days
    if creds.expired or (creds.expiry and
        (creds.expiry - datetime.now()).days < 7):

        if creds.refresh_token:
            creds.refresh(Request())
            # Save refreshed token
            with open(token_path, 'w') as f:
                f.write(creds.to_json())
            return True

    return False

# Add cron job on AWS server
# 0 2 * * * docker exec presgen-core python3 -c "from src.agent.slides_google import ensure_fresh_token; ensure_fresh_token()"
```

#### Option C: Google Workspace Subscription + Service Account
```bash
# Cost: $6-18/month per user
# Benefit: No token expiry issues
# Setup: Domain-Wide Delegation

# Only consider if:
# - Demo runs longer than 6 months
# - Budget allows $6-18/month extra
# - You have a custom domain (not @gmail.com)
```

**Recommendation:**
- **Before Demo (Now):** Use Option A - refresh token before deployment
- **For Production (If needed):** Use Option B - automated token refresh
- **Last Resort:** Option C - Workspace subscription

**Action Items:**
- [ ] Refresh OAuth token before deploying (Option A)
- [ ] Set calendar reminder 3 months from now to check token status
- [ ] Monitor CloudWatch for OAuth authentication errors
- [ ] Document token refresh procedure for future maintenance

---

### 2. **AWS Region Not Configured** 🟡 MEDIUM

**The Problem:**
```bash
$ aws configure list
region     : <not set>                : None             : None
```

Your AWS CLI has no default region set. This means:
- Lightsail deployment script will fail (no region specified)
- S3 bucket creation might default to us-east-1
- CloudWatch logs may go to wrong region
- Higher latency if region is far from users

**Impact:**
- Deployment script will fail on first run
- Inconsistent resource locations
- Potential compliance issues (data residency)

**Solution:**

```bash
# Set default region
aws configure set region us-east-1

# Or choose region closest to your demo audience:
# us-east-1 (N. Virginia) - Default, cheapest, most services
# us-west-2 (Oregon) - West Coast
# eu-west-1 (Ireland) - Europe
# ap-southeast-1 (Singapore) - Asia

# Verify
aws configure get region

# Update deployment script with explicit region
# Edit: deployment/deploy-to-lightsail.sh
# Add: REGION="us-east-1" at the top
```

**Recommendation:**
- **For AllCloud demo:** Use `us-east-1` (N. Virginia) - most reliable, cheapest
- **For Israel audience:** Consider `eu-west-1` (Ireland) - lower latency to Middle East

**Action Items:**
- [ ] Set default AWS region: `aws configure set region us-east-1`
- [ ] Update deployment script with hardcoded region
- [ ] Verify all AWS resources will be in same region

---

### 3. **No Rate Limiting or DDoS Protection** 🟡 MEDIUM

**The Problem:**
Your nginx configuration has no rate limiting. If someone discovers your demo URL:
- Could spam API requests
- Generate hundreds of presentations (costs money on Google Cloud)
- Exhaust Lightsail CPU/memory
- Max out Google Cloud API quotas

**Current Protection:**
- ✅ HTTP Basic Auth (prevents casual abuse)
- ❌ No rate limiting per user
- ❌ No request throttling
- ❌ No cost ceiling on Google Cloud

**Example Attack:**
```bash
# Someone with credentials could run:
for i in {1..1000}; do
  curl -u demo_user:AllCloud2024! \
    http://YOUR_IP/api/generate \
    -d '{"topic":"Test","slides":10}'
done

# Result:
# - 1,000 presentations created in Google Drive
# - ~$200 in Google Cloud API costs
# - Server CPU at 100%
# - Demo unusable for others
```

**Solutions:**

#### Add Rate Limiting to nginx

```nginx
# /etc/nginx/nginx.conf

http {
    # Define rate limiting zones
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/m;
    limit_req_zone $binary_remote_addr zone=ui_limit:10m rate=60r/m;

    # Limit concurrent connections
    limit_conn_zone $binary_remote_addr zone=conn_limit:10m;

    server {
        # Apply to API endpoints
        location /api/generate {
            limit_req zone=api_limit burst=5 nodelay;
            limit_conn conn_limit 3;

            proxy_pass http://presgen-assess:8000;
        }

        # Apply to UI
        location / {
            limit_req zone=ui_limit burst=20 nodelay;
            proxy_pass http://presgen-ui:3000;
        }
    }
}
```

#### Add Application-Level Rate Limiting

```python
# src/service/http.py

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/generate")
@limiter.limit("10/minute")  # Max 10 presentations per minute per IP
async def generate_presentation(request: Request):
    pass
```

#### Set Google Cloud Budget Alert

```bash
# Create budget alert
gcloud billing budgets create \
  --billing-account=YOUR_BILLING_ACCOUNT_ID \
  --display-name="PresGen Demo Budget Alert" \
  --budget-amount=50 \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=90 \
  --threshold-rule=percent=100

# Alert will email you at 50%, 90%, 100% of $50 budget
```

**Recommendation:**
- Add nginx rate limiting (10 requests/min per IP for /api/generate)
- Set Google Cloud budget alert at $50/month
- Monitor CloudWatch for suspicious request patterns

**Action Items:**
- [ ] Add rate limiting to nginx configuration
- [ ] Install slowapi for Python rate limiting: `pip install slowapi`
- [ ] Set Google Cloud budget alert
- [ ] Document rate limits in demo credentials email

---

### 4. **No SSL/TLS Certificate (HTTP Only)** 🟡 MEDIUM

**The Problem:**
Your current plan uses HTTP only (no HTTPS). This means:
- Credentials sent in plain text (Basic Auth)
- API keys visible in transit
- OAuth tokens transmitted unencrypted
- Browser warnings: "Not Secure"
- Some browsers block HTTP uploads

**Impact:**
- **Security:** Credentials can be intercepted on network
- **UX:** Browser shows "Not Secure" warning (looks unprofessional for CTO demo)
- **Compliance:** May violate data protection policies
- **API Issues:** Some APIs require HTTPS callbacks

**Solutions:**

#### Option A: Let's Encrypt (Free, Requires Domain)

**Requirements:**
- Domain name (e.g., presgen-demo.yourdomain.com)
- DNS A record pointing to Lightsail static IP

```bash
# On Lightsail instance
sudo apt-get update
sudo apt-get install -y certbot python3-certbot-nginx

# Get certificate (automatic nginx config)
sudo certbot --nginx -d presgen-demo.yourdomain.com

# Auto-renewal (certbot adds cron job automatically)
sudo certbot renew --dry-run

# Update nginx config is automatic
# Certificate auto-renews every 90 days
```

**Cost:** Free
**Setup Time:** 10 minutes
**Maintenance:** Automatic

#### Option B: Self-Signed Certificate (Quick, Browser Warnings)

```bash
# Generate self-signed cert
sudo openssl req -x509 -nodes -days 365 \
  -newkey rsa:2048 \
  -keyout /etc/ssl/private/presgen-selfsigned.key \
  -out /etc/ssl/certs/presgen-selfsigned.crt

# Update nginx
server {
    listen 443 ssl;
    ssl_certificate /etc/ssl/certs/presgen-selfsigned.crt;
    ssl_certificate_key /etc/ssl/private/presgen-selfsigned.key;

    # Rest of config...
}
```

**Cost:** Free
**Setup Time:** 5 minutes
**Downside:** Browser shows "Not Trusted" warning (bad for demo)

#### Option C: No HTTPS (Accept Risk)

For internal demo only, you might accept:
- ✅ Traffic is on AWS internal network (relatively safe)
- ✅ Basic Auth provides some protection
- ✅ Demo duration is short (low risk window)
- ❌ Still vulnerable to MITM attacks on public WiFi
- ❌ Looks unprofessional in demo

**Recommendation:**
- **If you have a domain:** Use Let's Encrypt (Option A) - professional, free, secure
- **If no domain available:** Use self-signed (Option B) - warn demo participants about browser warning
- **If demo is truly internal only:** Accept HTTP risk (Option C) - but monitor network

**Action Items:**
- [ ] Decide: Do you have a domain name for the demo?
- [ ] If yes: Set up Let's Encrypt SSL certificate
- [ ] If no: Decide between self-signed cert or HTTP-only risk
- [ ] Update deployment script to configure SSL

---

### 5. **No Backup Verification or Restore Testing** 🟡 MEDIUM

**The Problem:**
Your backup script (`scripts/backup.sh`) creates backups, but:
- Never tests if backups can be restored
- No verification that S3 uploads succeed
- No checksum validation
- No automated restore procedure

**What Could Go Wrong:**
```bash
# Backup runs daily but fails silently
2025-11-01: Backup fails (S3 bucket deleted) - no alert sent
2025-11-15: Lightsail instance crashes
2025-11-15: Try to restore backup - realize backups haven't worked for 2 weeks
2025-11-15: ALL DATA LOST (presentations, assessments, user uploads)
```

**Impact:**
- False sense of security
- Complete data loss if backup actually failed
- No way to know backup is working until disaster strikes

**Solution:**

#### Add Backup Verification

```bash
# Enhanced backup script: scripts/backup-with-verification.sh

backup_with_verification() {
    BACKUP_DATE=$(date +%Y%m%d-%H%M%S)
    BACKUP_FILE="backup-${BACKUP_DATE}.tar.gz"

    # 1. Create backup
    tar -czf /tmp/${BACKUP_FILE} \
        /home/ubuntu/presgen/data \
        /home/ubuntu/presgen/secrets \
        /home/ubuntu/presgen/.env

    # 2. Calculate checksum
    CHECKSUM=$(sha256sum /tmp/${BACKUP_FILE} | awk '{print $1}')
    echo "${CHECKSUM}" > /tmp/${BACKUP_FILE}.sha256

    # 3. Upload to S3
    aws s3 cp /tmp/${BACKUP_FILE} s3://presgen-backups/backups/${BACKUP_FILE}
    aws s3 cp /tmp/${BACKUP_FILE}.sha256 s3://presgen-backups/backups/${BACKUP_FILE}.sha256

    # 4. Verify upload
    REMOTE_CHECKSUM=$(aws s3 cp s3://presgen-backups/backups/${BACKUP_FILE}.sha256 - | cat)

    if [ "${CHECKSUM}" = "${REMOTE_CHECKSUM}" ]; then
        echo "✅ Backup verified: ${BACKUP_FILE}"

        # Send success notification
        aws sns publish \
            --topic-arn arn:aws:sns:us-east-1:788159322332:presgen-alerts \
            --subject "Backup Success" \
            --message "Backup completed and verified: ${BACKUP_FILE}"
    else
        echo "❌ Backup verification FAILED!"

        # Send failure alert
        aws sns publish \
            --topic-arn arn:aws:sns:us-east-1:788159322332:presgen-alerts \
            --subject "⚠️ BACKUP FAILED" \
            --message "Backup verification failed for ${BACKUP_FILE}. Immediate attention required!"

        exit 1
    fi

    # 5. Test restore (monthly)
    DAY_OF_MONTH=$(date +%d)
    if [ "${DAY_OF_MONTH}" = "01" ]; then
        test_restore
    fi
}

test_restore() {
    echo "Testing backup restore..."

    # Download latest backup
    LATEST_BACKUP=$(aws s3 ls s3://presgen-backups/backups/ | sort | tail -n 1 | awk '{print $4}')
    aws s3 cp s3://presgen-backups/backups/${LATEST_BACKUP} /tmp/test-restore.tar.gz

    # Extract to temp location
    mkdir -p /tmp/restore-test
    tar -xzf /tmp/test-restore.tar.gz -C /tmp/restore-test

    # Verify critical files exist
    if [ -f "/tmp/restore-test/home/ubuntu/presgen/.env" ] && \
       [ -d "/tmp/restore-test/home/ubuntu/presgen/secrets" ]; then
        echo "✅ Restore test passed"
        rm -rf /tmp/restore-test
    else
        echo "❌ Restore test FAILED - backup is corrupted"
        aws sns publish \
            --topic-arn arn:aws:sns:us-east-1:788159322332:presgen-alerts \
            --subject "⚠️ RESTORE TEST FAILED" \
            --message "Monthly restore test failed. Backup may be corrupted!"
    fi
}
```

#### Create Restore Procedure

```bash
# scripts/restore.sh

#!/bin/bash
set -e

# Restore from S3 backup

if [ -z "$1" ]; then
    echo "Usage: ./restore.sh [backup-filename or 'latest']"
    echo ""
    echo "Available backups:"
    aws s3 ls s3://presgen-backups/backups/ | grep backup-
    exit 1
fi

BACKUP_NAME=$1

# Get backup file
if [ "${BACKUP_NAME}" = "latest" ]; then
    BACKUP_FILE=$(aws s3 ls s3://presgen-backups/backups/ | sort | tail -n 1 | awk '{print $4}')
else
    BACKUP_FILE=${BACKUP_NAME}
fi

echo "Restoring from: ${BACKUP_FILE}"

# Download backup
aws s3 cp s3://presgen-backups/backups/${BACKUP_FILE} /tmp/restore.tar.gz

# Verify checksum
aws s3 cp s3://presgen-backups/backups/${BACKUP_FILE}.sha256 /tmp/restore.sha256
EXPECTED_CHECKSUM=$(cat /tmp/restore.sha256)
ACTUAL_CHECKSUM=$(sha256sum /tmp/restore.tar.gz | awk '{print $1}')

if [ "${EXPECTED_CHECKSUM}" != "${ACTUAL_CHECKSUM}" ]; then
    echo "❌ Checksum mismatch! Backup may be corrupted."
    exit 1
fi

# Stop services
docker-compose down

# Backup current state (just in case)
mv /home/ubuntu/presgen /home/ubuntu/presgen.old.$(date +%s)

# Restore
mkdir -p /home/ubuntu/presgen
tar -xzf /tmp/restore.tar.gz -C /

# Restart services
cd /home/ubuntu/presgen
docker-compose up -d

echo "✅ Restore complete!"
echo "Previous state backed up to: /home/ubuntu/presgen.old.*"
```

**Recommendation:**
- Add backup verification to existing backup script
- Test restore procedure NOW (before disaster)
- Schedule monthly automated restore tests
- Set up SNS alerts for backup failures

**Action Items:**
- [ ] Enhance backup.sh with verification
- [ ] Create restore.sh script
- [ ] Test restore procedure manually
- [ ] Add monthly restore test to cron
- [ ] Document restore procedure

---

### 6. **No Monitoring for Google Cloud API Quotas** 🟡 MEDIUM

**The Problem:**
Google Cloud APIs have quotas:
- Slides API: 100 requests/100 seconds per user
- Vertex AI: Rate limits on token/image generation
- Drive API: 1,000 requests/100 seconds

If quota exceeded during demo:
- API calls fail with 429 (Too Many Requests)
- Demo breaks mid-presentation
- No advance warning
- No automatic backoff/retry

**Real-World Scenario:**
```bash
# Demo day: 5 people testing simultaneously
# Each creates 10 presentations in 5 minutes
# Total: 50 presentations = ~500 Slides API requests in 300 seconds
# Quota: 100 requests/100 seconds = max 300 requests in 300 seconds
# Result: QUOTA EXCEEDED after ~30 presentations
# Error shown to CTO: "429 Too Many Requests" ❌
```

**Solutions:**

#### Add Quota Monitoring

```python
# src/agent/slides_google.py

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from googleapiclient.errors import HttpError
import logging

log = logging.getLogger(__name__)

def is_quota_error(exception):
    """Check if error is quota-related."""
    if isinstance(exception, HttpError):
        return exception.resp.status in [429, 403] and \
               'quota' in str(exception).lower()
    return False

@retry(
    retry=retry_if_exception_type(HttpError),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    stop=stop_after_attempt(5),
    before_sleep=lambda retry_state: log.warning(
        f"API quota exceeded, retrying in {retry_state.next_action.sleep} seconds..."
    )
)
def create_presentation_with_retry(service, title):
    """Create presentation with automatic retry on quota errors."""
    try:
        return service.presentations().create(body={'title': title}).execute()
    except HttpError as e:
        if is_quota_error(e):
            log.error(f"Google API quota exceeded: {e}")
            # Send alert
            send_quota_alert(e)
        raise
```

#### Monitor Quota Usage

```bash
# Add to scripts/monitor.sh

check_google_quotas() {
    echo "📊 Google Cloud API Quotas:"

    # Slides API quota
    SLIDES_QUOTA=$(gcloud services quota list \
        --service=slides.googleapis.com \
        --consumer="project:presgen" \
        --filter="metric.type:slides.googleapis.com/quota/read/requests" \
        --format="value(currentUsage,effectiveLimit)")

    echo "  Slides API: ${SLIDES_QUOTA}"

    # Vertex AI quota
    VERTEX_QUOTA=$(gcloud services quota list \
        --service=aiplatform.googleapis.com \
        --consumer="project:presgen" \
        --filter="metric.type:aiplatform.googleapis.com/online_prediction_requests_per_base_model" \
        --format="value(currentUsage,effectiveLimit)")

    echo "  Vertex AI: ${VERTEX_QUOTA}"
}
```

#### Request Quota Increase (Preventive)

```bash
# Before demo, request quota increase

gcloud alpha services quota update \
  --service=slides.googleapis.com \
  --consumer="project:presgen" \
  --metric="slides.googleapis.com/quota/read/requests" \
  --value=1000 \
  --unit=1/min/{project}

# Note: Quota increase requests can take 2-5 business days
# Do this BEFORE demo, not during!
```

**Recommendation:**
- Add exponential backoff retry for all Google API calls
- Monitor quota usage in real-time during demo
- Request quota increase 1 week before demo
- Limit concurrent demo users to avoid quota exhaustion

**Action Items:**
- [ ] Add retry logic with exponential backoff
- [ ] Request Google Cloud quota increase (do this NOW)
- [ ] Add quota monitoring to dashboard
- [ ] Set alert for 80% quota usage

---

### 7. **No Disaster Recovery Plan** 🟡 MEDIUM

**The Problem:**
What happens if:
- Lightsail instance crashes during demo?
- AWS region has outage?
- Docker container won't start?
- Database gets corrupted?

Current plan:
- ❌ No standby instance
- ❌ No multi-region deployment
- ❌ No quick rollback procedure
- ❌ No runbook for common failures

**Impact:**
- Demo fails in front of CTO
- No way to quickly recover
- Potential loss of credibility

**Solution:**

#### Create Disaster Recovery Runbook

```markdown
# DISASTER RECOVERY RUNBOOK

## Scenario 1: Instance Crashes During Demo

**Detection:**
- Website not loading
- SSH connection refused

**Recovery (5 minutes):**
1. Check instance status:
   aws lightsail get-instance --instance-name presgen-demo
2. If stopped, restart:
   aws lightsail start-instance --instance-name presgen-demo
3. Wait 2 minutes for boot
4. Verify: curl http://STATIC_IP
5. If still down, restore from snapshot:
   aws lightsail create-instance-from-snapshot \
     --instance-snapshot-name presgen-backup-latest \
     --instance-name presgen-demo-restored

## Scenario 2: Docker Container Won't Start

**Detection:**
- curl returns "502 Bad Gateway"
- docker ps shows exited containers

**Recovery (3 minutes):**
1. SSH into instance
2. Check logs: docker-compose logs presgen-core
3. Restart services: docker-compose restart
4. If still failing, rebuild:
   docker-compose down && docker-compose up -d --build

## Scenario 3: Database Locked Errors

**Detection:**
- API returns "Database is locked"

**Recovery (1 minute):**
1. SSH into instance
2. Restart assess service: docker-compose restart presgen-assess
3. If persistent, restore from backup:
   ./scripts/restore.sh latest

## Scenario 4: Google API Authentication Fails

**Detection:**
- "403 Permission Denied" or "401 Unauthorized"

**Recovery (5 minutes):**
1. Check which auth failed:
   docker logs presgen-core | grep -i "auth\|credential"
2. If service account: verify file exists
   docker exec presgen-core ls -lh /secrets/google-creds.json
3. If OAuth: token may be expired
   # Upload fresh token from local machine
   scp -i lightsail-key.pem token.json ubuntu@IP:/home/ubuntu/presgen/secrets/
   docker-compose restart presgen-core

## Scenario 5: AWS Region Outage

**Detection:**
- All AWS services in region unavailable

**Recovery (30 minutes):**
1. This is worst-case scenario
2. Option A: Wait for AWS to restore (1-4 hours typically)
3. Option B: Demo from local machine:
   cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs
   docker-compose -f docker-compose.local.yml up
   # Expose to internet via ngrok
   ngrok http 3000

## Emergency Contacts
- AWS Support: Premium support ticket
- Google Cloud Support: https://console.cloud.google.com/support
- Your mobile: Keep phone charged and nearby during demo
```

#### Create Standby Snapshot

```bash
# Before demo, create snapshot
aws lightsail create-instance-snapshot \
  --instance-snapshot-name presgen-pre-demo-$(date +%Y%m%d) \
  --instance-name presgen-demo

# Can restore in 5 minutes if needed
```

#### Have Local Fallback Ready

```bash
# On your Mac, keep local version ready
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs

# Test local deployment works
docker-compose -f docker-compose.local.yml up -d

# Install ngrok for emergency internet exposure
brew install ngrok
ngrok http 3000  # Creates public URL instantly

# If AWS fails during demo, switch to local + ngrok
```

**Recommendation:**
- Create disaster recovery runbook (provided above)
- Take snapshot before demo
- Have local deployment ready as backup
- Test recovery procedures before demo day

**Action Items:**
- [ ] Create and print disaster recovery runbook
- [ ] Create pre-demo Lightsail snapshot
- [ ] Test local deployment as fallback
- [ ] Install and configure ngrok
- [ ] Do a "fire drill" - simulate failure and practice recovery

---

## Summary: Risk Matrix

| Issue | Severity | Likelihood | Impact | Mitigation Effort |
|-------|----------|------------|--------|-------------------|
| OAuth token expiry | 🔴 Critical | High (6 months) | Demo breaks | Low (10 min) |
| No AWS region set | 🟡 Medium | High (will fail) | Deployment fails | Low (1 min) |
| No rate limiting | 🟡 Medium | Low (requires abuse) | Cost overrun | Medium (30 min) |
| No HTTPS | 🟡 Medium | N/A (design choice) | Security/UX | Medium (30 min) |
| No backup verification | 🟡 Medium | Medium (silent failure) | Data loss | Medium (1 hour) |
| No quota monitoring | 🟡 Medium | Medium (heavy usage) | Demo fails | Low (30 min) |
| No disaster recovery | 🟡 Medium | Low (AWS reliable) | Demo fails | Medium (2 hours) |

---

## Recommended Action Plan (Priority Order)

### Before Deploying (Do NOW):

1. **Set AWS Region** (1 minute)
   ```bash
   aws configure set region us-east-1
   ```

2. **Refresh OAuth Token** (10 minutes)
   ```bash
   cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs
   rm token.json
   python3 -m src.cli.main generate --topic "Test" --slides 3
   ```

3. **Request Google Cloud Quota Increase** (5 minutes)
   ```bash
   # Do this NOW - takes 2-5 business days to approve
   gcloud alpha services quota update \
     --service=slides.googleapis.com \
     --consumer="project:presgen" \
     --metric="slides.googleapis.com/quota/read/requests" \
     --value=1000
   ```

### During Deployment:

4. **Add Rate Limiting to nginx** (30 minutes)
   - Edit nginx.conf to add rate limits
   - Test with curl to verify limits work

5. **Set Google Cloud Budget Alert** (10 minutes)
   ```bash
   gcloud billing budgets create \
     --billing-account=YOUR_BILLING_ACCOUNT \
     --display-name="PresGen Demo Alert" \
     --budget-amount=50
   ```

### After Deployment:

6. **Test Backup and Restore** (1 hour)
   - Run backup script
   - Verify S3 upload
   - Test restore procedure

7. **Create Disaster Recovery Runbook** (30 minutes)
   - Print and keep accessible during demo
   - Practice recovery scenarios

8. **Optional: Set Up HTTPS** (30 minutes if you have domain)
   - Only if you have domain name
   - Skip if demo is truly internal

### Before Demo Day:

9. **Create Pre-Demo Snapshot** (5 minutes)
   ```bash
   aws lightsail create-instance-snapshot \
     --instance-snapshot-name presgen-pre-demo-$(date +%Y%m%d) \
     --instance-name presgen-demo
   ```

10. **Fire Drill** (30 minutes)
    - Simulate instance crash and practice recovery
    - Verify all monitoring alerts work
    - Test local fallback deployment

---

## Final Checklist

Before going live with demo:

- [ ] AWS region configured: `aws configure get region`
- [ ] OAuth token refreshed within last 7 days
- [ ] Google Cloud quota increase requested (2-5 days before demo)
- [ ] Rate limiting added to nginx
- [ ] Google Cloud budget alert set at $50
- [ ] Backup script enhanced with verification
- [ ] Restore procedure tested successfully
- [ ] Disaster recovery runbook printed and accessible
- [ ] Pre-demo Lightsail snapshot created
- [ ] Local fallback deployment tested
- [ ] ngrok installed for emergency failover
- [ ] All tests passing (auth, API, end-to-end)
- [ ] Calendar reminder set for token refresh in 3 months

---

**Status:** ⚠️ REVIEW REQUIRED
**Recommended Actions:** 10 items (see Action Plan above)
**Estimated Effort:** 4-6 hours total
**Critical Actions:** 3 (OAuth refresh, AWS region, quota increase)

---

**Next Steps:**

1. Review this document with your team
2. Execute "Before Deploying" actions immediately
3. Schedule time for "During Deployment" actions
4. Plan "After Deployment" testing and validation
5. Conduct fire drill 1 day before demo
