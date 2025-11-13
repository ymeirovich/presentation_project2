# Phase 2: AWS Infrastructure Setup - COMPLETE ✅

**Date Completed:** November 14, 2025
**Duration:** ~45 minutes
**Status:** ✅ All tasks completed successfully

---

## Summary

Phase 2 infrastructure setup completed successfully. All AWS resources have been provisioned and configured.

---

## Infrastructure Details

### Lightsail Instance

| Property | Value |
|----------|-------|
| **Name** | presgen-prod |
| **Static IP** | **35.175.156.231** |
| **Region** | us-east-1a (Virginia) |
| **Bundle** | medium_2_0 |
| **RAM** | 4GB |
| **vCPUs** | 2 |
| **Storage** | 80GB SSD |
| **Data Transfer** | 3TB/month included |
| **Monthly Cost** | $20.00 |

**Access URL:** http://35.175.156.231

---

## Network Configuration

### Open Ports

| Port | Protocol | Purpose |
|------|----------|---------|
| 22 | TCP | SSH access |
| 80 | TCP | HTTP web traffic |
| 443 | TCP | HTTPS (for future SSL) |

**Firewall Status:** ✅ All required ports open

---

## IAM Configuration

| Resource | ARN |
|----------|-----|
| **Role Name** | PresGenLightsailRole |
| **Role ARN** | arn:aws:iam::788159322332:role/PresGenLightsailRole |
| **Policies** | CloudWatchAgentServerPolicy |

**Permissions:** ✅ CloudWatch logging enabled

---

## CloudWatch Logs

| Log Group | Retention | Purpose |
|-----------|-----------|---------|
| /presgen/nginx | 7 days | Web server logs |
| /presgen/core | 7 days | Presentation generation |
| /presgen/assess | 7 days | Assessment/course generation |
| /presgen/avatar | 7 days | Video generation |
| /presgen/ui | 7 days | Frontend logs |

**Cost:** ~$0.50/month for log storage

---

## Storage Strategy

**Decision:** Using **local storage only** (no S3)

**Rationale:**
- Minimizes monthly costs (~$0.50-2/month savings)
- 80GB SSD provides ample space
- SQLite database performance better with local storage
- Backups handled via Lightsail snapshots

**Can add S3 later if needed for:**
- Off-instance backups
- Long-term file archival
- Multi-region redundancy

---

## Cost Management Scripts

### Stop Instance (Save $20/month)
```bash
./aws_migration/scripts/stop-lightsail.sh
```

**Features:**
- Creates snapshot before stopping
- Stops instance gracefully
- Verifies stopped state
- Shows cost savings

### Start Instance (Resume Work)
```bash
./aws_migration/scripts/start-lightsail.sh
```

**Features:**
- Starts instance
- Waits for full boot (~2 minutes)
- Retrieves static IP
- Tests SSH connectivity
- Verifies application readiness

---

## Monthly Cost Breakdown

| Component | Cost | Notes |
|-----------|------|-------|
| **Lightsail Instance** | $20.00 | medium_2_0 bundle |
| **Static IP** | $0.00 | Free while attached |
| **CloudWatch Logs** | $0.50 | 7-day retention |
| **IAM Roles** | $0.00 | No charge |
| **Data Transfer** | $0.00 | 3TB included |
| **S3 Storage** | $0.00 | Not using S3 |
| **Snapshots** | $0.00* | Created on demand (~$4 per snapshot) |
| | | |
| **Total (Running 24/7)** | **$20.50/month** | |
| **Total (10hrs/week)** | **~$3.60/month** | Using stop/start scripts |

---

## Phase 2 Success Criteria

- [x] Lightsail instance running and accessible
- [x] Static IP allocated: **35.175.156.231**
- [x] All ports open and verified (22, 80, 443)
- [x] S3 buckets evaluated (skipped for cost savings)
- [x] IAM roles configured for CloudWatch
- [x] CloudWatch log groups created with 7-day retention
- [x] Stop/start scripts available and documented
- [x] Cost management strategy documented

---

## Next Steps: Phase 3

Phase 3 will install Docker and deploy the application:

1. **SSH Key Setup** - Download and configure Lightsail SSH key
2. **Server Setup** - Install Docker, Docker Compose, dependencies
3. **Application Transfer** - Deploy code to server
4. **Secrets Configuration** - Upload Service Account credentials
5. **Environment Configuration** - Create .env with production settings
6. **Container Deployment** - Start all Docker services
7. **Verification** - Test presentation generation

**Estimated Duration:** 3-4 hours

---

## Quick Reference Commands

### Check Instance Status
```bash
aws lightsail get-instance --instance-name presgen-prod --query 'instance.state.name' --output text
```

### Get Static IP
```bash
aws lightsail get-static-ip --static-ip-name presgen-prod-ip --query 'staticIp.ipAddress' --output text
```

### View Open Ports
```bash
aws lightsail get-instance-port-states --instance-name presgen-prod
```

### List Log Groups
```bash
aws logs describe-log-groups --log-group-name-prefix /presgen
```

### Create Snapshot
```bash
aws lightsail create-instance-snapshot \
  --instance-name presgen-prod \
  --instance-snapshot-name presgen-prod-snapshot-$(date +%Y%m%d-%H%M%S)
```

---

## Important Notes

1. **Instance is RUNNING** - You're now being charged $20/month
   - To save costs when not in use: `./aws_migration/scripts/stop-lightsail.sh`
   - To resume work: `./aws_migration/scripts/start-lightsail.sh`

2. **No Application Deployed Yet** - Instance is a blank Ubuntu server
   - Phase 3 will install Docker and deploy PresGen

3. **Static IP Remains Yours** - Even when instance is stopped
   - URL http://35.175.156.231 will always work (after Phase 3 deployment)

4. **Data Persists** - All data on 80GB disk survives stop/start
   - Only memory (Redis cache) is cleared on restart

5. **SSH Access** - Need to download SSH key from Lightsail console
   - AWS Console → Lightsail → Account → SSH Keys → Download

---

## Files Created

1. **aws_migration/trust-policy.json** - IAM trust policy for Lightsail
2. **aws_migration/PHASE2_COMPLETE.md** - This document
3. **aws_migration/scripts/stop-lightsail.sh** - Stop instance script
4. **aws_migration/scripts/start-lightsail.sh** - Start instance script

---

## Troubleshooting

### Can't SSH to Instance
- Download SSH key from Lightsail console
- Set permissions: `chmod 400 lightsail-key.pem`
- Wait 3-5 minutes after instance creation
- Command: `ssh -i lightsail-key.pem ubuntu@35.175.156.231`

### Instance Not Starting
- Check status: `aws lightsail get-instance --instance-name presgen-prod`
- View operations: `aws lightsail get-instance --instance-name presgen-prod --query 'instance.state'`
- Restart: `aws lightsail reboot-instance --instance-name presgen-prod`

### Ports Not Accessible
- Verify open: `aws lightsail get-instance-port-states --instance-name presgen-prod`
- Re-open if needed: See section 2.3 in PHASED_MIGRATION_PLAN.md

---

**Phase 2 Status:** ✅ COMPLETE
**Ready for Phase 3:** ✅ YES
**Infrastructure Cost:** $20.50/month (running) or $3.60/month (10hrs/week with stop/start)

---

*Documentation generated: November 14, 2025*
