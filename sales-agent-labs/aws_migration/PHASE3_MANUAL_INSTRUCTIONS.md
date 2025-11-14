# Phase 3: Initial Deployment - Manual Instructions

**Duration:** 3-4 hours
**Prerequisites:** Phase 2 complete, browser access to AWS Console
**Instance IP:** 35.175.156.231

---

## Overview

Phase 3 installs Docker on the Lightsail instance and deploys the PresGen application. Due to SSH key complexity, these steps are performed manually through the AWS Console's browser-based SSH terminal.

---

## Step-by-Step Instructions

### 3.1 Access Instance via Browser SSH

1. **Open AWS Lightsail Console:**
   - URL: https://lightsail.aws.amazon.com/ls/webapp/us-east-1/instances/presgen-prod/connect
   - Or navigate to: AWS Console → Lightsail → Instances → presgen-prod → Connect tab

2. **Click "Connect using SSH"**
   - A browser-based terminal will open
   - You'll be logged in as `ubuntu` user

3. **Verify you're connected:**
   ```bash
   echo "Connected to $(hostname)"
   whoami  # Should show: ubuntu
   pwd     # Should show: /home/ubuntu
   ```

---

### 3.2 Install Docker and Docker Compose (1 hour)

Copy and paste these commands into the browser SSH terminal:

```bash
# Update system
echo "📦 Updating system packages..."
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
echo "🐳 Installing Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add ubuntu user to docker group
sudo usermod -aG docker ubuntu

# Install Docker Compose
echo "🔧 Installing Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installations
docker --version
docker-compose --version

# Enable Docker to start on boot
sudo systemctl enable docker
sudo systemctl start docker

echo "✅ Docker installation complete!"
```

**Important:** After installation, **log out and log back in** to the SSH terminal for Docker group permissions to take effect:
```bash
exit  # Log out
# Click "Connect using SSH" again to log back in
```

**Verify Docker works without sudo:**
```bash
docker ps  # Should work without "permission denied"
```

---

### 3.3 Create Directory Structure (5 minutes)

```bash
# Create application directory
mkdir -p /home/ubuntu/presgen
cd /home/ubuntu/presgen

# Create subdirectories
mkdir -p data/assess
mkdir -p data/core
mkdir -p secrets
mkdir -p logs
mkdir -p out/images

# Verify structure
tree -L 2 /home/ubuntu/presgen || ls -la /home/ubuntu/presgen
```

---

### 3.4 Transfer Application Code (1 hour)

Since we can't easily SCP to the instance, we'll use git to clone the repository:

**Option A: Clone from GitHub (if repository is pushed)**

```bash
cd /home/ubuntu/presgen

# Clone repository
git clone https://github.com/ymeirovich/presentation_project2.git presgen-app
cd presgen-app

# Checkout the deployment branch
git checkout 001-read-specification-md

# Copy files to parent directory
cp -r * ../
cd ..
rm -rf presgen-app

# Verify files copied
ls -la
```

**Option B: Manual file creation (if needed)**

If the repository isn't accessible, I'll provide the essential files below that you can create manually.

---

### 3.5 Upload Service Account Credentials (15 minutes)

You need to upload your Google Service Account JSON file to the instance.

**Method 1: Use AWS S3 as intermediary (recommended)**

On your **local machine:**
```bash
# Upload service account to S3
aws s3 cp presgen-service-account.json s3://temp-presgen-files/google-creds.json
```

On the **Lightsail instance:**
```bash
# Download from S3
aws s3 cp s3://temp-presgen-files/google-creds.json /home/ubuntu/presgen/secrets/google-creds.json
chmod 600 /home/ubuntu/presgen/secrets/google-creds.json

# Clean up S3 (delete the file)
aws s3 rm s3://temp-presgen-files/google-creds.json
```

**Method 2: Create temp S3 bucket**

On your **local machine:**
```bash
# Create temporary bucket
aws s3 mb s3://presgen-temp-$(date +%s)

# Upload service account
aws s3 cp presgen-service-account.json s3://presgen-temp-XXXXX/google-creds.json

# Note the bucket name for use on instance
```

On the **Lightsail instance:**
```bash
# Download from temp bucket
aws s3 cp s3://presgen-temp-XXXXX/google-creds.json /home/ubuntu/presgen/secrets/google-creds.json
chmod 600 /home/ubuntu/presgen/secrets/google-creds.json
```

On your **local machine** (cleanup):
```bash
# Delete temp bucket
aws s3 rb s3://presgen-temp-XXXXX --force
```

**Method 3: Copy-paste file contents (for small files)**

On your **local machine:**
```bash
# Display service account JSON
cat presgen-service-account.json
```

On the **Lightsail instance:**
```bash
# Create file with nano
nano /home/ubuntu/presgen/secrets/google-creds.json

# Paste the JSON content
# Press Ctrl+X, then Y, then Enter to save

# Verify
cat /home/ubuntu/presgen/secrets/google-creds.json | jq .
chmod 600 /home/ubuntu/presgen/secrets/google-creds.json
```

---

### 3.6 Create Environment Configuration (30 minutes)

Create the `.env` file with production settings:

```bash
cd /home/ubuntu/presgen
nano .env
```

**Paste this content:**

```bash
# ============================================================================
# PRESGEN PRODUCTION CONFIGURATION
# ============================================================================

# Environment
NODE_ENV=production
PYTHON_ENV=production

# Google Cloud Authentication (Service Account only)
GOOGLE_APPLICATION_CREDENTIALS=/secrets/google-creds.json
FORCE_SERVICE_ACCOUNT=true
GOOGLE_CLOUD_PROJECT=presgen
GOOGLE_QUOTA_PROJECT=presgen

# OpenAI API
OPENAI_API_KEY=your-openai-api-key-here

# HTTP Basic Auth
HTTP_BASIC_AUTH_USER=demo_user
HTTP_BASIC_AUTH_PASS=AllCloud2024!

# Database (SQLite for production)
DATABASE_URL=sqlite:////data/assess/presgen_assess.db

# Presgen Core Settings
PRESGEN_MAX_SLIDES=40
PRESGEN_USE_CACHE=true
PRESGEN_DEV_MODE=false

# Redis
REDIS_URL=redis://redis:6379/0

# Ports (internal)
PRESGEN_CORE_PORT=8080
PRESGEN_ASSESS_PORT=8000
PRESGEN_AVATAR_PORT=8002
PRESGEN_UI_PORT=3000

# Logging
LOG_LEVEL=info
```

**Save the file:** Press `Ctrl+X`, then `Y`, then `Enter`

**⚠️ IMPORTANT:** Replace `your-openai-api-key-here` with your actual OpenAI API key!

```bash
# Edit to add your API key
nano .env
# Find OPENAI_API_KEY line and replace with your key
```

---

### 3.7 Create docker-compose.yml (30 minutes)

The docker-compose file should already be in your repository. Verify it exists:

```bash
ls -la /home/ubuntu/presgen/docker-compose.yml
```

If it doesn't exist, you'll need to create it. Let me know and I'll provide the content.

---

### 3.8 Deploy Containers (30 minutes)

```bash
cd /home/ubuntu/presgen

# Pull Docker images (this may take 10-15 minutes)
echo "📦 Pulling Docker images..."
docker-compose pull

# Build custom images if needed
echo "🔨 Building Docker images..."
docker-compose build

# Start all services
echo "🚀 Starting all services..."
docker-compose up -d

# Wait for services to start
sleep 30

# Check status
docker-compose ps

# View logs
docker-compose logs --tail=50

# Check if all services are healthy
docker ps
```

**Expected output:**
```
NAME                COMMAND                  STATUS              PORTS
presgen-nginx       "/docker-entrypoint.…"   Up                  0.0.0.0:80->80/tcp
presgen-core        "python -m src.main"     Up                  8080/tcp
presgen-assess      "uvicorn main:app"       Up                  8000/tcp
presgen-avatar      "python main.py"         Up                  8002/tcp
presgen-ui          "node server.js"         Up                  3000/tcp
presgen-redis       "docker-entrypoint.s…"   Up                  6379/tcp
```

---

### 3.9 Verify Deployment (30 minutes)

**Test 1: Check nginx is serving**
```bash
curl -I http://localhost
# Should return HTTP 200 or 401 (Basic Auth)
```

**Test 2: Test with Basic Auth**
```bash
curl -u demo_user:AllCloud2024! http://localhost/health
# Should return health check response
```

**Test 3: Access from your local machine**

Open in browser: http://35.175.156.231

- Username: `demo_user`
- Password: `AllCloud2024!`

You should see the PresGen UI!

**Test 4: Generate a simple presentation**

Via browser:
1. Navigate to http://35.175.156.231
2. Log in with credentials above
3. Try generating a simple 3-slide presentation
4. Topic: "Test Deployment"

Via curl:
```bash
curl -u demo_user:AllCloud2024! \
  -X POST http://localhost/api/presgen/generate \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "AWS Lightsail Deployment Test",
    "slides": 3,
    "use_ai_images": false
  }'
```

**Expected:** You should get back a job ID, and within 1-2 minutes, a Google Slides URL.

---

### 3.10 Troubleshooting

#### Issue: Docker permission denied
**Solution:**
```bash
# Log out and log back in
exit
# Reconnect via browser SSH
```

#### Issue: Containers won't start
```bash
# Check logs for specific service
docker-compose logs presgen-core
docker-compose logs presgen-assess

# Restart problematic service
docker-compose restart presgen-core
```

#### Issue: Can't access from browser
```bash
# Check nginx is running
docker ps | grep nginx

# Check nginx logs
docker logs presgen-nginx

# Verify port 80 is open
sudo netstat -tlnp | grep :80
```

#### Issue: Google API authentication errors
```bash
# Verify service account file exists
ls -la /home/ubuntu/presgen/secrets/google-creds.json

# Check it's valid JSON
cat /home/ubuntu/presgen/secrets/google-creds.json | jq .

# Verify environment variable in container
docker exec presgen-core env | grep GOOGLE

# Should show:
# GOOGLE_APPLICATION_CREDENTIALS=/secrets/google-creds.json
# FORCE_SERVICE_ACCOUNT=true
```

#### Issue: Database errors
```bash
# Check database file exists
ls -la /home/ubuntu/presgen/data/assess/

# If missing, create directory and restart
mkdir -p /home/ubuntu/presgen/data/assess
docker-compose restart presgen-assess

# Check logs
docker-compose logs presgen-assess | tail -50
```

---

### 3.11 Monitor Services

```bash
# View all container logs
docker-compose logs -f

# View specific service
docker-compose logs -f presgen-core

# Check resource usage
docker stats

# Check disk space
df -h

# Check memory usage
free -h
```

---

### 3.12 Stop Services (When Needed)

```bash
# Stop all services
docker-compose down

# Stop but keep data
docker-compose stop

# Restart all services
docker-compose restart

# Stop instance to save costs
# (Use from your local machine)
./aws_migration/scripts/stop-lightsail.sh
```

---

## Phase 3 Success Criteria

- [ ] Docker and Docker Compose installed and working
- [ ] Application directory structure created
- [ ] Application code deployed
- [ ] Service Account credentials uploaded and secured
- [ ] Environment configuration created with correct settings
- [ ] All Docker containers running and healthy
- [ ] Can access PresGen UI at http://35.175.156.231
- [ ] Can log in with Basic Auth credentials
- [ ] Can generate a test presentation successfully
- [ ] Google Slides API working with Service Account
- [ ] Database initialized and working

---

## Important Security Notes

1. **Never commit .env file** - Contains API keys
2. **Secure secrets directory:**
   ```bash
   chmod 700 /home/ubuntu/presgen/secrets
   chmod 600 /home/ubuntu/presgen/secrets/*
   ```
3. **Change default passwords** if exposing publicly
4. **Monitor costs** - Instance is running at $0.67/day

---

## Next Steps After Phase 3

1. **Test thoroughly** - Generate presentations, courses, assessments
2. **Monitor performance** - Check CPU, memory, disk usage
3. **Set up monitoring** - CloudWatch dashboards
4. **Create snapshots** - Before making changes
5. **Document any issues** - For troubleshooting guide

---

## Quick Reference

**Instance:** presgen-prod
**IP:** 35.175.156.231
**URL:** http://35.175.156.231
**Username:** demo_user
**Password:** AllCloud2024!
**SSH Access:** https://lightsail.aws.amazon.com/ls/webapp/us-east-1/instances/presgen-prod/connect

---

**Need help?** Check the troubleshooting section above or review Docker logs for specific errors.
