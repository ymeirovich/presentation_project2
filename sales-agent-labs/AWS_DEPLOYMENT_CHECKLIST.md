# AWS Deployment Readiness Checklist

**Date:** October 30, 2025
**Status:** Pre-Deployment Review
**Target:** AWS Lightsail ($80/month instance)

---

## ✅ Completed Items

### 1. Database Migrations
- [x] All Alembic migrations idempotent
- [x] Database-agnostic (SQLite local, PostgreSQL production)
- [x] Migrations tested locally
- [x] Data preservation verified
- [x] Migration fixes committed to git (commit f710d6f)

### 2. Docker Configuration
- [x] All Docker images build successfully
- [x] presgen-core: Healthy and tested
- [x] presgen-assess: Healthy with working migrations
- [x] presgen-redis: Healthy
- [x] Health checks configured correctly
- [x] Multi-service stack tested locally

### 3. Google Cloud Authentication
- [x] OAuth 2.0 configured
- [x] Service Account created
- [x] Google Slides API enabled
- [x] Google Forms API enabled
- [x] Credentials files ready (`google-creds.json`, `google-oauth-token.json`)
- [x] 403 error resolution documented

### 4. Documentation
- [x] Migration fix summary created
- [x] Local testing results documented
- [x] AWS migration plan complete
- [x] Deployment guide available
- [x] Troubleshooting runbooks ready

---

## 🔄 In Progress

### 5. Frontend Testing
- [ ] presgen-ui health check needs fixing (container running, health check failing)
- [ ] nginx reverse proxy needs UI to be healthy
- [ ] End-to-end UI testing pending
- [ ] Frontend-to-backend connectivity verification

**Action Required:** Debug presgen-ui health check (Next.js is running, issue is likely health check path/tool)

---

## ⚠️ Pending - Must Complete Before AWS Deployment

### 6. Environment Configuration

#### A. Production Environment Variables
```bash
# Core Configuration
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Database (PostgreSQL on AWS)
DATABASE_URL=postgresql://presgen:${DB_PASSWORD}@localhost:5432/presgen_assess

# OpenAI API
OPENAI_API_KEY=${YOUR_OPENAI_KEY}  # ⚠️ REQUIRED

# ElevenLabs (Optional)
ELEVENLABS_API_KEY=${YOUR_ELEVENLABS_KEY}

# AWS S3 Storage
STORAGE_PROVIDER=s3
AWS_REGION=us-east-1
S3_BUCKET=${YOUR_S3_BUCKET}  # ⚠️ REQUIRED
AWS_ACCESS_KEY_ID=${YOUR_AWS_KEY}  # ⚠️ REQUIRED
AWS_SECRET_ACCESS_KEY=${YOUR_AWS_SECRET}  # ⚠️ REQUIRED

# Google Cloud
GOOGLE_APPLICATION_CREDENTIALS=/secrets/google-creds.json
OAUTH_TOKEN_PATH=/secrets/google-oauth-token.json
```

**Action Required:**
- [ ] Create `.env.production` file with actual values
- [ ] Verify all API keys are valid
- [ ] Test S3 bucket access
- [ ] Confirm database connection string

#### B. Secrets Management
- [ ] Upload `google-creds.json` to `/secrets/` on AWS
- [ ] Upload `google-oauth-token.json` to `/secrets/` on AWS
- [ ] Create nginx `.htpasswd` file with production credentials
- [ ] Store all sensitive values securely (not in git)

**Command to create .htpasswd:**
```bash
htpasswd -c nginx/auth/.htpasswd demo_user
```

### 7. AWS Infrastructure Setup

#### A. Lightsail Instance
- [ ] Launch Ubuntu 22.04 LTS instance ($80/month or higher)
- [ ] Assign static IP address
- [ ] Open ports: 80 (HTTP), 443 (HTTPS), 22 (SSH)
- [ ] Configure firewall rules
- [ ] Set up SSH key authentication

#### B. Domain & SSL
- [ ] Register domain or use Lightsail DNS
- [ ] Point DNS A record to static IP
- [ ] Install Let's Encrypt SSL certificate
- [ ] Configure nginx for HTTPS
- [ ] Enable automatic SSL renewal

**Commands:**
```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Test auto-renewal
sudo certbot renew --dry-run
```

#### C. Database Setup
- [ ] Install PostgreSQL 14+
- [ ] Create `presgen_assess` database
- [ ] Create `presgen` database user with password
- [ ] Configure PostgreSQL for remote connections (if needed)
- [ ] Set up automated backups

**Commands:**
```bash
# Install PostgreSQL
sudo apt-get install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql
CREATE DATABASE presgen_assess;
CREATE USER presgen WITH PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE presgen_assess TO presgen;
\q

# Run migrations
alembic upgrade head
```

#### D. Storage Setup
- [ ] Create S3 bucket for generated presentations
- [ ] Configure bucket CORS policy
- [ ] Set up lifecycle rules (auto-delete old files)
- [ ] Create IAM user with S3-only permissions
- [ ] Generate access keys for application

**S3 Bucket Policy Example:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::788159322332:user/presgen-app"
      },
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::your-bucket-name/*"
    }
  ]
}
```

### 8. Monitoring & Logging

#### A. Application Monitoring
- [ ] Set up Prometheus metrics collection
- [ ] Configure log rotation (`logrotate`)
- [ ] Set up disk space alerts
- [ ] Monitor Docker container health
- [ ] Track API rate limits

**Docker logs:**
```bash
# View logs
docker-compose logs -f presgen-assess

# Log rotation in docker-compose.yml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

#### B. Backup Strategy
- [ ] Automated PostgreSQL backups (daily)
- [ ] S3 bucket versioning enabled
- [ ] Configuration file backups
- [ ] Database backup retention policy (30 days)

**Backup script:**
```bash
#!/bin/bash
pg_dump presgen_assess | gzip > backup-$(date +%Y%m%d).sql.gz
aws s3 cp backup-$(date +%Y%m%d).sql.gz s3://your-backup-bucket/
```

### 9. Security Hardening

#### A. System Security
- [ ] Install fail2ban for SSH brute-force protection
- [ ] Configure UFW firewall
- [ ] Enable automatic security updates
- [ ] Disable root SSH login
- [ ] Set up non-root sudo user
- [ ] Configure SSH key-only authentication

#### B. Application Security
- [ ] Enable nginx rate limiting (already configured)
- [ ] Configure nginx basic auth (already configured)
- [ ] Set secure headers (already configured)
- [ ] Disable debug mode in production
- [ ] Review CORS policies
- [ ] Implement request size limits

#### C. Secret Rotation
- [ ] Document process for rotating API keys
- [ ] Set calendar reminders for credential rotation
- [ ] Test backup OAuth token generation

### 10. Performance Optimization

#### A. Resource Limits
- [ ] Configure Docker memory limits appropriately
- [ ] Set CPU limits per service
- [ ] Monitor resource usage under load
- [ ] Adjust worker/thread counts based on instance size

#### B. Caching
- [ ] Enable nginx caching (already configured)
- [ ] Configure Redis for session/cache storage
- [ ] Set appropriate TTLs for cached content

### 11. Deployment Process

#### A. Pre-Deployment
- [ ] Create deployment checklist specific to this system
- [ ] Test full stack locally one final time
- [ ] Prepare rollback plan
- [ ] Document all configuration changes
- [ ] Schedule deployment window (low-traffic period)

#### B. Deployment Steps
```bash
# 1. SSH into AWS instance
ssh -i your-key.pem ubuntu@your-instance-ip

# 2. Install Docker & Docker Compose
sudo apt-get update
sudo apt-get install docker.io docker-compose-plugin

# 3. Clone repository
git clone https://github.com/your-repo/sales-agent-labs.git
cd sales-agent-labs

# 4. Copy secrets
scp -i your-key.pem google-creds.json ubuntu@your-instance:/path/to/secrets/
scp -i your-key.pem google-oauth-token.json ubuntu@your-instance:/path/to/secrets/

# 5. Create .env file with production values
nano .env

# 6. Build and start services
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 7. Run migrations
docker exec presgen-assess alembic upgrade head

# 8. Verify all services healthy
docker ps
curl http://localhost/health

# 9. Test endpoints
curl -u demo_user:password http://localhost/api/v1/health
```

#### C. Post-Deployment Verification
- [ ] All Docker containers running and healthy
- [ ] Database migrations completed successfully
- [ ] UI accessible via browser
- [ ] API endpoints responding correctly
- [ ] Google authentication working
- [ ] File uploads functional
- [ ] Generated presentations saving to S3
- [ ] SSL certificate valid
- [ ] Monitoring dashboards operational

### 12. Testing & Validation

#### A. Smoke Tests
- [ ] Create test workflow
- [ ] Upload test Excel file
- [ ] Run gap analysis
- [ ] Generate presentation
- [ ] Download results
- [ ] Verify S3 storage

#### B. Load Testing
- [ ] Test with 5 concurrent users
- [ ] Monitor resource usage under load
- [ ] Verify rate limiting works
- [ ] Check database connection pool
- [ ] Monitor response times

### 13. Documentation Updates

#### A. Deployment Documentation
- [ ] Document actual AWS configuration used
- [ ] Update connection strings
- [ ] Record all credential locations
- [ ] Document troubleshooting steps specific to AWS

#### B. User Documentation
- [ ] Create user guide for demo
- [ ] Document API rate limits
- [ ] Provide example workflows
- [ ] Share demo credentials securely

---

## 🚨 Critical Blockers (Must Resolve)

### Immediate Action Required:
1. **Fix presgen-ui health check** - Container is running but health check failing
2. **Obtain OpenAI API Key** - Required for core functionality
3. **Create AWS S3 bucket** - Required for file storage in production
4. **Set up PostgreSQL** - SQLite not suitable for production

### Nice to Have (Can Deploy Without):
- ElevenLabs API (avatar generation feature)
- Custom domain (can use IP initially)
- SSL certificate (can add post-deployment)

---

## 📊 Estimated Timeline

| Task | Time Estimate | Priority |
|------|--------------|----------|
| Fix presgen-ui health check | 30 minutes | 🔴 Critical |
| Configure production .env | 15 minutes | 🔴 Critical |
| Set up AWS Lightsail instance | 30 minutes | 🔴 Critical |
| Install PostgreSQL | 20 minutes | 🔴 Critical |
| Create S3 bucket | 15 minutes | 🔴 Critical |
| Deploy application | 45 minutes | 🔴 Critical |
| Set up SSL/domain | 30 minutes | 🟡 Important |
| Configure monitoring | 45 minutes | 🟡 Important |
| Load testing | 1 hour | 🟢 Optional |

**Total Critical Path:** ~2.5 hours
**Total for Production-Ready:** ~4 hours

---

## 🎯 Recommended Next Steps

### Immediate (Today):
1. Debug and fix presgen-ui health check issue
2. Test full stack end-to-end locally with UI working
3. Obtain OpenAI API key
4. Create production `.env` file template

### Next Session (Before AWS):
1. Launch AWS Lightsail instance
2. Install PostgreSQL
3. Create S3 bucket and IAM user
4. Deploy application to AWS
5. Run smoke tests

### Post-Deployment:
1. Add SSL certificate
2. Configure monitoring
3. Set up automated backups
4. Perform load testing
5. Document lessons learned

---

## 📞 Support Resources

- **AWS Lightsail Docs:** https://lightsail.aws.amazon.com/ls/docs
- **Docker Compose:** https://docs.docker.com/compose/
- **PostgreSQL Setup:** https://www.postgresql.org/docs/
- **Let's Encrypt:** https://letsencrypt.org/getting-started/
- **nginx Configuration:** https://nginx.org/en/docs/

---

## ✅ Sign-Off Checklist

Before deploying to AWS, confirm:
- [ ] All database migrations tested and working
- [ ] Full stack running locally (including UI)
- [ ] All required API keys obtained
- [ ] Production `.env` file ready
- [ ] Secrets uploaded securely
- [ ] Backup/rollback plan documented
- [ ] Team notified of deployment window
- [ ] Monitoring configured
- [ ] Smoke test plan ready

**Deployment Authorization:** _______________  Date: ___________

---

**Last Updated:** October 30, 2025
**Next Review:** Before AWS deployment
