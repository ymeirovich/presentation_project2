# PresGen AWS Migration - Rollback Procedures

**Version:** 1.0
**Date:** November 13, 2025
**Status:** 🚨 Emergency Response Plan
**Purpose:** Quick recovery procedures for each migration phase

---

## Emergency Contact Information

**Primary Contact:** Yitzchak Meirovich
**Email:** ymeirovich@gmail.com
**Phone:** _______________________________

**Escalation:**
- AWS Support: [Premium Support Console](https://console.aws.amazon.com/support)
- Google Cloud Support: [Support Console](https://console.cloud.google.com/support)

---

## Rollback Philosophy

**Golden Rule:** *"Always have a working fallback"*

1. **Keep local environment running** during initial deployment
2. **Test rollback procedures** before they're needed
3. **Document every step** as you migrate
4. **Take snapshots** before major changes
5. **Have backups** of everything critical

---

## Quick Rollback Decision Tree

```
Is the system completely down?
├─ YES → Use Emergency Fallback (Local + ngrok)
└─ NO → Identify which phase failed
         │
         ├─ Phase 2 (Infrastructure) → Delete AWS resources, costs already incurred are minimal
         ├─ Phase 3 (Deployment) → Rollback to local Docker Compose
         ├─ Phase 4 (Validation) → Fix issues or rollback to local
         ├─ Phase 5 (Security) → Revert configuration changes
         ├─ Phase 6 (CI/CD) → Disable pipeline, manual deploy
         ├─ Phase 7 (Monitoring) → Non-critical, fix without rollback
         └─ Phase 8 (Optimization) → Revert specific optimizations
```

---

## Phase 1: Pre-Migration Preparation

**Rollback Risk:** ❌ None (documentation phase only)

**No rollback needed** - this phase is read-only exploration and documentation.

---

## Phase 2: AWS Infrastructure Setup

**Rollback Risk:** 🟢 Very Low (no application impact)

### What Was Created

- Lightsail instance (`presgen-prod`)
- Static IP
- S3 buckets (optional)
- IAM roles
- CloudWatch log groups
- Security groups

### Rollback Procedure

**Estimated Time:** 15 minutes

```bash
# 1. Delete Lightsail instance
aws lightsail delete-instance --instance-name presgen-prod

# 2. Release static IP
aws lightsail release-static-ip --static-ip-name presgen-prod-ip

# 3. Delete S3 buckets (if created and empty)
aws s3 rb s3://presgen-prod-uploads --force
aws s3 rb s3://presgen-prod-backups --force
aws s3 rb s3://presgen-prod-exports --force

# 4. Delete CloudWatch log groups
aws logs delete-log-group --log-group-name /presgen/nginx
aws logs delete-log-group --log-group-name /presgen/core
aws logs delete-log-group --log-group-name /presgen/assess
aws logs delete-log-group --log-group-name /presgen/avatar
aws logs delete-log-group --log-group-name /presgen/ui

# 5. Delete IAM role (optional - can keep for next attempt)
# aws iam delete-role --role-name PresGenLightsailRole
```

**Cost Impact:** ~$0.50-2.00 for partial month

**Data Loss:** None (application not deployed yet)

**Decision:** Continue working locally, retry Phase 2 when ready

---

## Phase 3: Initial Deployment

**Rollback Risk:** 🟡 Medium (application deployed but may be broken)

### What Was Deployed

- Docker and Docker Compose on Lightsail
- Application code
- Secrets
- Containers running

### Rollback Procedure A: Fix AWS Deployment

**Estimated Time:** 30-60 minutes

```bash
# SSH to instance
ssh -i ~/.ssh/lightsail-presgen-prod.pem ubuntu@<STATIC_IP>

# Check what's wrong
cd /home/ubuntu/presgen
docker-compose ps
docker-compose logs --tail=100

# Common fixes:
# 1. Restart containers
docker-compose restart

# 2. Rebuild and restart
docker-compose down
docker-compose build
docker-compose up -d

# 3. Check environment variables
cat .env
# Verify all required variables present

# 4. Check secrets
ls -la secrets/
# Verify google-creds.json, token.json present with correct permissions

# 5. View specific service logs
docker-compose logs -f presgen-assess
```

### Rollback Procedure B: Return to Local Environment

**Estimated Time:** 5 minutes

```bash
# On local machine
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs

# Ensure Docker running
docker-compose ps

# If not running, start it
docker-compose up -d

# Verify working
curl -u demo_user:AllCloud2024! http://localhost/api/presgen-assess/health

# Test in browser
open http://localhost
```

**Decision:**
- **If demo is urgent:** Use local environment
- **If time permits:** Debug AWS deployment
- **Use ngrok for emergency public access:** (see Emergency Fallback section)

---

## Phase 4: Functional Validation

**Rollback Risk:** 🟡 Medium (bugs discovered in production)

### Issue: Tests Failing on AWS

**Rollback to Local:**

```bash
# 1. Redirect users to local environment
# (Update any shared links to use ngrok URL)

# 2. On local machine
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs
docker-compose up -d

# 3. Start ngrok for public access
ngrok http 80
# Share ngrok URL: https://abc123.ngrok.io

# 4. Fix issues on AWS without time pressure
ssh -i ~/.ssh/lightsail-presgen-prod.pem ubuntu@<STATIC_IP>
cd /home/ubuntu/presgen
# Debug and fix...
```

**Data Recovery:**

If data was created on AWS that you need locally:

```bash
# Copy SQLite database from AWS to local
scp -i ~/.ssh/lightsail-presgen-prod.pem \
    ubuntu@<STATIC_IP>:/home/ubuntu/presgen/data/assess/presgen_assess.db \
    ./data/assess/presgen_assess-aws-backup.db

# Merge data if needed (manual SQL)
```

---

## Phase 5: Security Hardening

**Rollback Risk:** 🟢 Low (can revert configurations)

### Issue: SSL Certificate Problems

**Rollback to HTTP:**

```bash
ssh -i ~/.ssh/lightsail-presgen-prod.pem ubuntu@<STATIC_IP>

# Restore nginx config to HTTP only
cd /home/ubuntu/presgen
cp nginx/nginx.conf.backup nginx/nginx.conf

# Restart nginx
docker-compose restart nginx

# Verify
curl -I http://<STATIC_IP>/
```

### Issue: Rate Limiting Too Strict

**Adjust or Disable:**

```bash
# Edit nginx config
sudo nano /home/ubuntu/presgen/nginx/nginx.conf

# Comment out rate limiting lines
# limit_req zone=api burst=20 nodelay;

# Restart nginx
docker-compose restart nginx
```

### Issue: WAF Blocking Legitimate Traffic

**Disable WAF:**

```bash
# Disassociate WAF from resource
aws wafv2 disassociate-web-acl --resource-arn <ALB_ARN> --region us-east-1
```

---

## Phase 6: CI/CD Pipeline

**Rollback Risk:** 🟢 Very Low (pipeline is optional)

### Issue: GitHub Actions Deployment Failing

**Rollback to Manual Deployment:**

```bash
# 1. Disable GitHub Actions workflow
# Comment out .github/workflows/deploy-production.yml

# 2. Deploy manually
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs

# Create deployment package
tar -czf presgen-deploy.tar.gz \
    --exclude='.git' \
    --exclude='node_modules' \
    --exclude='__pycache__' \
    .

# Transfer and deploy
scp -i ~/.ssh/lightsail-presgen-prod.pem presgen-deploy.tar.gz ubuntu@<STATIC_IP>:/tmp/
ssh -i ~/.ssh/lightsail-presgen-prod.pem ubuntu@<STATIC_IP>

cd /home/ubuntu/presgen
tar -xzf /tmp/presgen-deploy.tar.gz
docker-compose pull
docker-compose up -d --build
```

**No rollback needed** - just revert to manual deployment process.

---

## Phase 7: Monitoring & Observability

**Rollback Risk:** ❌ None (monitoring doesn't affect application)

### Issue: Too Many Alerts

**Adjust Thresholds:**

```bash
# Update CloudWatch alarm thresholds
aws cloudwatch put-metric-alarm \
    --alarm-name presgen-high-cpu \
    --threshold 90  # Was 80, increased to reduce noise
    --region us-east-1
```

**No application rollback needed.**

---

## Phase 8: Production Hardening

**Rollback Risk:** 🟡 Medium (optimizations may cause issues)

### Issue: Performance Degradation After Optimization

**Revert Specific Changes:**

#### Database Optimization Rollback

```bash
# Restore original postgresql.conf
ssh -i ~/.ssh/lightsail-presgen-prod.pem ubuntu@<STATIC_IP>
sudo cp /etc/postgresql/15/main/postgresql.conf.backup \
       /etc/postgresql/15/main/postgresql.conf
sudo systemctl restart postgresql
```

#### nginx Optimization Rollback

```bash
# Restore original nginx.conf
cd /home/ubuntu/presgen
cp nginx/nginx.conf.backup nginx/nginx.conf
docker-compose restart nginx
```

#### Application Configuration Rollback

```bash
# Restore previous .env file
cd /home/ubuntu/presgen
cp .env.backup .env
docker-compose restart presgen-assess presgen-core
```

---

## Emergency Fallback: Local + ngrok

**Use When:** AWS completely unavailable, demo happening NOW

**Estimated Time:** 5 minutes

### Step 1: Start Local Environment

```bash
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs

# Ensure latest code
git pull

# Start services
docker-compose up -d

# Wait 30 seconds for startup
sleep 30

# Verify health
curl -u demo_user:AllCloud2024! http://localhost/api/presgen-assess/health
```

### Step 2: Expose via ngrok

```bash
# Install ngrok (if not installed)
# brew install ngrok (macOS)

# Start ngrok
ngrok http 80

# You'll get a public URL like: https://abc123.ngrok.io
```

### Step 3: Share Access

**Send to users:**
```
Demo URL: https://abc123.ngrok.io
Username: demo_user
Password: AllCloud2024!

Note: This is running on a local server through ngrok.
Performance may vary based on internet connection.
```

**Limitations:**
- Depends on your internet connection
- Limited to ngrok free tier (if using free)
- Your computer must stay on

**Advantages:**
- Works in 5 minutes
- No AWS costs during outage
- Full functionality (all data local)

---

## Data Recovery Procedures

### Recover SQLite Database from AWS

```bash
# Download database
scp -i ~/.ssh/lightsail-presgen-prod.pem \
    ubuntu@<STATIC_IP>:/home/ubuntu/presgen/data/assess/presgen_assess.db \
    ./data/assess/presgen_assess-recovered.db

# Verify integrity
sqlite3 presgen_assess-recovered.db "PRAGMA integrity_check;"

# If healthy, use it
mv presgen_assess-recovered.db presgen_assess.db
```

### Recover from S3 Backup

```bash
# List available backups
aws s3 ls s3://presgen-prod-backups/sqlite/ --region us-east-1

# Download latest backup
aws s3 cp s3://presgen-prod-backups/sqlite/presgen_assess-20251113-020000.db.gz ./

# Extract
gunzip presgen_assess-20251113-020000.db.gz

# Restore
cp presgen_assess-20251113-020000.db data/assess/presgen_assess.db
```

### Recover from Lightsail Snapshot

```bash
# List snapshots
aws lightsail get-instance-snapshots --region us-east-1

# Create new instance from snapshot
aws lightsail create-instance-from-snapshot \
    --instance-snapshot-name presgen-prod-20251113 \
    --instance-name presgen-prod-restored \
    --availability-zone us-east-1a \
    --bundle-id medium_2_0

# Attach static IP to restored instance
aws lightsail attach-static-ip \
    --static-ip-name presgen-prod-ip \
    --instance-name presgen-prod-restored
```

---

## Testing Rollback Procedures

### Monthly Rollback Drill

**Schedule:** First Monday of each month

```bash
# 1. Create test snapshot of production
aws lightsail create-instance-snapshot \
    --instance-snapshot-name presgen-prod-test-$(date +%Y%m%d) \
    --instance-name presgen-prod

# 2. Practice rollback to local
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs
docker-compose down
docker-compose up -d
# Verify working

# 3. Practice ngrok emergency fallback
ngrok http 80
# Test access via ngrok URL

# 4. Practice database recovery
scp -i ~/.ssh/lightsail-presgen-prod.pem \
    ubuntu@<STATIC_IP>:/home/ubuntu/presgen/data/assess/presgen_assess.db \
    ./test-recovery.db
sqlite3 test-recovery.db "PRAGMA integrity_check;"

# 5. Document time taken for each step
# Update this procedure with actual times
```

---

## Rollback Success Criteria

### Verify System Working After Rollback

**Checklist:**

- [ ] All services responding to health checks
- [ ] Can log in with credentials
- [ ] Can create new assessment
- [ ] Can view existing data
- [ ] No errors in logs
- [ ] Performance acceptable (<2s response time)
- [ ] Users notified of rollback (if necessary)

**Test Script:**

```bash
#!/bin/bash
# rollback-verification.sh

BASE_URL="http://localhost"  # or AWS URL
AUTH="demo_user:AllCloud2024!"

echo "Testing health checks..."
curl -f -u "$AUTH" "$BASE_URL/api/presgen-assess/health" || exit 1

echo "Testing authentication..."
curl -f -u "$AUTH" "$BASE_URL/" || exit 1

echo "All tests passed! Rollback successful."
```

---

## Post-Rollback Actions

### Communication

**Internal Team:**
```
Subject: PresGen Rolled Back to [Local/Previous Version]

Team,

The PresGen AWS deployment has been rolled back to [local environment/previous version].

Reason: [Brief explanation]
Impact: [User impact, if any]
Timeline: [Expected fix timeline]
Access: [New access URL if changed]

We'll notify when the system is restored to AWS.
```

**Users (if applicable):**
```
Subject: PresGen Service Update

The PresGen demo is temporarily running on a backup system.

Access: [URL]
Credentials: [Same as before]

You may experience slightly different performance, but all functionality is available.

We apologize for any inconvenience.
```

### Investigation

**Document what went wrong:**

1. **What failed:** [Specific component/service]
2. **When:** [Exact timestamp]
3. **Error messages:** [Copy/paste errors]
4. **Actions taken:** [Steps attempted before rollback]
5. **Rollback method used:** [Which procedure from this doc]
6. **Time to recover:** [Minutes from failure to working]

**Save to:** `aws_migration/incidents/YYYY-MM-DD-incident.md`

### Prevention

**Update procedures:**
- Add specific fix to troubleshooting section
- Update rollback procedure with lessons learned
- Add new monitoring/alerts to prevent recurrence
- Schedule post-mortem meeting (if significant)

---

## Rollback Quick Reference Card

Print this and keep handy:

```
╔════════════════════════════════════════════════════════╗
║           PRESGEN EMERGENCY ROLLBACK CARD              ║
╠════════════════════════════════════════════════════════╣
║ 🚨 AWS COMPLETELY DOWN → Use Local + ngrok             ║
║                                                        ║
║ 1. cd ~/Documents/.../sales-agent-labs                 ║
║ 2. docker-compose up -d                                ║
║ 3. ngrok http 80                                       ║
║ 4. Share ngrok URL                                     ║
║                                                        ║
║ Time: 5 minutes                                        ║
╠════════════════════════════════════════════════════════╣
║ ⚡ AWS PARTIALLY WORKING → Debug on AWS                ║
║                                                        ║
║ ssh -i ~/.ssh/lightsail-presgen-prod.pem ubuntu@IP    ║
║ cd /home/ubuntu/presgen                                ║
║ docker-compose logs -f                                 ║
║ docker-compose restart                                 ║
╠════════════════════════════════════════════════════════╣
║ 💾 NEED DATA FROM AWS → Copy database                  ║
║                                                        ║
║ scp -i ~/.ssh/lightsail-presgen-prod.pem \             ║
║     ubuntu@IP:/home/ubuntu/presgen/data/assess/*.db .  ║
╠════════════════════════════════════════════════════════╣
║ 📞 Emergency Contact: ymeirovich@gmail.com             ║
║ 🔗 AWS Console: console.aws.amazon.com                 ║
╚════════════════════════════════════════════════════════╝
```

---

## Rollback Checklist

**Before attempting rollback:**

- [ ] Identify which phase failed
- [ ] Assess urgency (demo happening vs routine maintenance)
- [ ] Review relevant rollback procedure above
- [ ] Ensure local environment is available
- [ ] Have AWS credentials accessible
- [ ] Have SSH key for Lightsail
- [ ] Take snapshot/backup before rollback (if time permits)

**During rollback:**

- [ ] Follow procedure step-by-step
- [ ] Document each action taken
- [ ] Note any errors encountered
- [ ] Track time spent on each step

**After rollback:**

- [ ] Run verification tests
- [ ] Notify affected users (if any)
- [ ] Document incident
- [ ] Schedule post-mortem (if needed)
- [ ] Update rollback procedures with learnings

---

## Appendix: Lightsail Snapshot Management

### Create Pre-Migration Snapshot

```bash
# Before any major change
aws lightsail create-instance-snapshot \
    --instance-snapshot-name presgen-prod-pre-[CHANGE] \
    --instance-name presgen-prod \
    --region us-east-1

# Example:
aws lightsail create-instance-snapshot \
    --instance-snapshot-name presgen-prod-pre-ssl-cert \
    --instance-name presgen-prod \
    --region us-east-1
```

### Restore from Snapshot

```bash
# Stop current instance (optional)
aws lightsail stop-instance --instance-name presgen-prod

# Create new instance from snapshot
aws lightsail create-instance-from-snapshot \
    --instance-snapshot-name presgen-prod-pre-ssl-cert \
    --instance-name presgen-prod-restored \
    --availability-zone us-east-1a \
    --bundle-id medium_2_0

# Move static IP
aws lightsail detach-static-ip --static-ip-name presgen-prod-ip
aws lightsail attach-static-ip \
    --static-ip-name presgen-prod-ip \
    --instance-name presgen-prod-restored

# Delete old instance (after verification)
aws lightsail delete-instance --instance-name presgen-prod
```

---

**Document Status:** ✅ Complete
**Last Updated:** November 13, 2025
**Last Tested:** [Test monthly and update date]
**Next Test Date:** [First Monday of next month]

---

*"Hope for the best, plan for the worst"*
*- Anonymous DevOps Engineer*
