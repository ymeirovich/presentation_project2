# Implementation Guide - Security & Reliability Enhancements

**Date:** October 29, 2025
**For:** PresGen AWS Lightsail Deployment
**Based on:** CRITICAL_ISSUES_ANALYSIS.md

This guide provides step-by-step implementation for all security and reliability enhancements identified in the critical issues analysis.

---

## Table of Contents

1. [Rate Limiting (nginx + Application)](#1-rate-limiting)
2. [SSL/TLS Certificate (presgen.net)](#2-ssltls-certificate-for-presgennet)
3. [Backup and Restore System](#3-backup-and-restore-system)
4. [Google Cloud API Quota Management](#4-google-cloud-api-quota-management)
5. [Troubleshooting Runbooks](#5-troubleshooting-runbooks)
6. [Testing & Verification](#6-testing--verification)

---

## 1. Rate Limiting

### 1.1 Nginx Rate Limiting

**File:** `nginx/nginx.conf`

Replace the existing nginx configuration with this enhanced version:

```nginx
# nginx/nginx.conf - Enhanced with Rate Limiting

user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for" '
                    'rt=$request_time uct="$upstream_connect_time" '
                    'uht="$upstream_header_time" urt="$upstream_response_time"';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 100M;

    # ============================================================================
    # RATE LIMITING CONFIGURATION
    # ============================================================================

    # Zone 1: API Generation Endpoints (Most restrictive)
    # 10 requests per minute per IP for presentation generation
    limit_req_zone $binary_remote_addr zone=api_generate:10m rate=10r/m;

    # Zone 2: General API Endpoints (Moderate)
    # 60 requests per minute per IP for other API calls
    limit_req_zone $binary_remote_addr zone=api_general:10m rate=60r/m;

    # Zone 3: UI/Static Content (Lenient)
    # 120 requests per minute per IP for page loads and assets
    limit_req_zone $binary_remote_addr zone=ui_zone:10m rate=120r/m;

    # Zone 4: Connection Limiting
    # Max 10 concurrent connections per IP
    limit_conn_zone $binary_remote_addr zone=conn_limit:10m;

    # Rate limit status code (return 429 Too Many Requests)
    limit_req_status 429;
    limit_conn_status 429;

    # ============================================================================
    # UPSTREAM DEFINITIONS
    # ============================================================================

    upstream presgen_ui {
        server presgen-ui:3000;
        keepalive 32;
    }

    upstream presgen_assess {
        server presgen-assess:8000;
        keepalive 16;
    }

    upstream presgen_core {
        server presgen-core:8080;
        keepalive 16;
    }

    # ============================================================================
    # SERVER CONFIGURATION
    # ============================================================================

    server {
        listen 80;
        server_name _;

        # Security headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;

        # Enable Basic Authentication (except for health checks)
        auth_basic "PresGen Demo - Authorized Access Only";
        auth_basic_user_file /etc/nginx/auth/.htpasswd;

        # Global connection limit
        limit_conn conn_limit 10;

        # ========================================================================
        # HEALTH CHECK ENDPOINT (No Auth, No Rate Limit)
        # ========================================================================
        location /health {
            auth_basic off;
            limit_req off;
            limit_conn off;

            proxy_pass http://presgen_assess/health;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;

            access_log off;
        }

        # ========================================================================
        # PRESENTATION GENERATION ENDPOINTS (Strictest Rate Limiting)
        # ========================================================================
        location ~ ^/api/(generate|assess/workflows) {
            # Rate limit: 10 requests/min, allow burst of 3
            limit_req zone=api_generate burst=3 nodelay;

            proxy_pass http://presgen_assess;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # Extended timeouts for long-running operations
            proxy_read_timeout 600s;
            proxy_connect_timeout 60s;
            proxy_send_timeout 600s;

            # WebSocket support for SSE
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";

            # Disable buffering for SSE
            proxy_buffering off;
            proxy_cache off;
        }

        # ========================================================================
        # GENERAL API ENDPOINTS (Moderate Rate Limiting)
        # ========================================================================
        location /api/ {
            # Rate limit: 60 requests/min, allow burst of 10
            limit_req zone=api_general burst=10 nodelay;

            proxy_pass http://presgen_assess/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            proxy_read_timeout 300s;
            proxy_connect_timeout 60s;
            proxy_send_timeout 300s;
        }

        # ========================================================================
        # CORE SERVICE ENDPOINTS
        # ========================================================================
        location /core/ {
            # Rate limit: 60 requests/min, allow burst of 10
            limit_req zone=api_general burst=10 nodelay;

            proxy_pass http://presgen_core/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            proxy_read_timeout 300s;
            proxy_connect_timeout 60s;
            proxy_send_timeout 300s;
        }

        # ========================================================================
        # FRONTEND UI (Lenient Rate Limiting)
        # ========================================================================
        location / {
            # Rate limit: 120 requests/min, allow burst of 20
            limit_req zone=ui_zone burst=20 nodelay;

            proxy_pass http://presgen_ui;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # Next.js specific headers
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }

        # ========================================================================
        # STATIC FILES (No Rate Limit)
        # ========================================================================
        location /static/ {
            limit_req off;

            alias /home/ubuntu/presgen/static/;
            expires 7d;
            add_header Cache-Control "public, immutable";
        }

        # ========================================================================
        # ERROR PAGES
        # ========================================================================
        error_page 429 /429.html;
        location = /429.html {
            auth_basic off;
            limit_req off;
            root /usr/share/nginx/html;
            internal;
        }
    }
}
```

**Create custom 429 error page:**

```bash
# Create 429.html for rate limit errors
cat > nginx/429.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>Rate Limit Exceeded</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 600px;
            margin: 100px auto;
            text-align: center;
            padding: 20px;
        }
        h1 { color: #e74c3c; }
        p { color: #555; line-height: 1.6; }
        .code { background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }
    </style>
</head>
<body>
    <h1>⏱️ Rate Limit Exceeded</h1>
    <p>You've made too many requests in a short period.</p>
    <p><strong>Limits:</strong></p>
    <ul style="list-style: none; padding: 0;">
        <li>Presentation Generation: <span class="code">10 requests/minute</span></li>
        <li>General API Calls: <span class="code">60 requests/minute</span></li>
        <li>Page Loads: <span class="code">120 requests/minute</span></li>
    </ul>
    <p>Please wait a moment and try again.</p>
    <p style="font-size: 0.9em; color: #888; margin-top: 40px;">
        If you need higher limits, contact: ymeirovich@gmail.com
    </p>
</body>
</html>
EOF
```

### 1.2 Application-Level Rate Limiting

**Install dependencies:**

```bash
# Add to presgen-assess/requirements.txt
slowapi==0.1.9
```

**File:** `presgen-assess/src/service/app.py`

```python
# Add these imports at the top
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# After creating FastAPI app
app = FastAPI(title="PresGen Assess API")

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["60/minute"],  # Default for all endpoints
    storage_uri="memory://",  # Use Redis in production: "redis://redis:6379"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Apply strict limits to expensive endpoints
@app.post("/api/generate")
@limiter.limit("10/minute")  # Override default with stricter limit
async def generate_presentation(request: Request, data: GenerateRequest):
    """Generate presentation with rate limiting."""
    pass

@app.post("/api/assess/workflows")
@limiter.limit("10/minute")
async def create_workflow(request: Request, workflow: WorkflowCreate):
    """Create assessment workflow with rate limiting."""
    pass

# Exempt health check from rate limiting
@app.get("/health")
@limiter.exempt
async def health_check():
    """Health check endpoint (no rate limit)."""
    return {"status": "healthy"}
```

**For production with Redis:**

```yaml
# docker-compose.yml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    restart: unless-stopped

  presgen-assess:
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis

volumes:
  redis_data:
```

### 1.3 Update Demo Credentials Document

**File:** `aws_migration/DEMO_CREDENTIALS.md`

```markdown
# PresGen Demo Access Credentials

## Access Information

**URL:** http://presgen.net (or http://STATIC_IP)

## User Credentials

### Demo User
- **Username:** `demo_user`
- **Password:** `AllCloud2024!`
- **Purpose:** General demo access

### CTO User
- **Username:** `cto_user`
- **Password:** `CTODemo2024!`
- **Purpose:** CTO exclusive access

### Yosi User
- **Username:** `yosi_user`
- **Password:** `YosiDemo2024!`
- **Purpose:** Yosi Frankel access

## Rate Limits

**Please be aware of the following rate limits to ensure optimal demo experience:**

### Presentation Generation
- **Limit:** 10 requests per minute per user
- **Burst:** Up to 3 requests can be made immediately
- **Affected endpoints:**
  - `/api/generate` (presentation generation)
  - `/api/assess/workflows` (assessment creation)

### General API Calls
- **Limit:** 60 requests per minute per user
- **Burst:** Up to 10 requests can be made immediately
- **Affected endpoints:** All other `/api/*` endpoints

### Page Loads
- **Limit:** 120 requests per minute per user
- **Burst:** Up to 20 requests can be made immediately
- **Affected:** UI page navigation and asset loading

### Connection Limit
- **Maximum:** 10 concurrent connections per IP address

## If You Exceed Rate Limits

You'll see a "Rate Limit Exceeded" message with details. Simply:
1. Wait 60 seconds
2. Try your request again
3. Pace your requests to stay within limits

**For higher limits or issues:** Contact ymeirovich@gmail.com

## Browser Notes

- First visit will prompt for username/password
- Credentials are cached for your browser session
- To logout: Clear browser cache or use private/incognito mode

## Support

For technical issues during the demo: ymeirovich@gmail.com
```

---

## 2. SSL/TLS Certificate for presgen.net

### 2.1 Domain Setup

**DNS Configuration (Do this first):**

```bash
# In your domain registrar (where presgen.net is registered):
# Add an A record:

Type: A
Name: @ (or blank for root domain)
Value: YOUR_LIGHTSAIL_STATIC_IP
TTL: 300 (5 minutes)

# Optional: Add www subdomain
Type: A
Name: www
Value: YOUR_LIGHTSAIL_STATIC_IP
TTL: 300

# Verify DNS propagation (may take 5-60 minutes)
dig presgen.net +short
# Should show your Lightsail static IP
```

### 2.2 Free SSL with Let's Encrypt (Certbot)

**Installation script:**

```bash
# File: deployment/setup-ssl.sh
#!/bin/bash
set -e

DOMAIN="presgen.net"
EMAIL="ymeirovich@gmail.com"

echo "🔒 Setting up SSL certificate for ${DOMAIN}"

# 1. Install Certbot
echo "📦 Installing Certbot..."
sudo apt-get update
sudo apt-get install -y certbot python3-certbot-nginx

# 2. Stop nginx temporarily
echo "⏸️  Stopping nginx..."
docker-compose stop nginx

# 3. Get certificate
echo "🔐 Obtaining SSL certificate..."
sudo certbot certonly --standalone \
    --non-interactive \
    --agree-tos \
    --email ${EMAIL} \
    --domains ${DOMAIN},www.${DOMAIN} \
    --preferred-challenges http

# 4. Create nginx SSL configuration
echo "⚙️  Configuring nginx for SSL..."
sudo tee /home/ubuntu/presgen/nginx/ssl.conf > /dev/null << 'EOF'
# SSL Configuration
ssl_certificate /etc/letsencrypt/live/presgen.net/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/presgen.net/privkey.pem;
ssl_protocols TLSv1.2 TLSv1.3;
ssl_prefer_server_ciphers on;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;
ssl_stapling on;
ssl_stapling_verify on;
EOF

# 5. Update docker-compose to mount certificates
echo "🐳 Updating docker-compose..."
cat >> /home/ubuntu/presgen/docker-compose.yml << 'EOF'

  nginx:
    volumes:
      - /etc/letsencrypt:/etc/letsencrypt:ro
EOF

# 6. Setup auto-renewal
echo "🔄 Setting up automatic certificate renewal..."
sudo tee /etc/cron.d/certbot-renew > /dev/null << 'EOF'
# Renew certificates twice daily
0 0,12 * * * root certbot renew --quiet --deploy-hook "cd /home/ubuntu/presgen && docker-compose restart nginx"
EOF

echo "✅ SSL certificate installed successfully!"
echo "Certificate location: /etc/letsencrypt/live/${DOMAIN}/"
echo "Auto-renewal configured in: /etc/cron.d/certbot-renew"
```

### 2.3 Update Nginx for HTTPS

**File:** `nginx/nginx-ssl.conf`

```nginx
# nginx/nginx-ssl.conf - HTTPS-enabled configuration

# Include rate limiting and upstream definitions from nginx.conf
# ... (same as before) ...

http {
    # ... (all previous http config) ...

    # ========================================================================
    # HTTP SERVER - Redirect to HTTPS
    # ========================================================================
    server {
        listen 80;
        server_name presgen.net www.presgen.net;

        # Allow Let's Encrypt validation
        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
            auth_basic off;
        }

        # Redirect all other HTTP traffic to HTTPS
        location / {
            return 301 https://$server_name$request_uri;
        }
    }

    # ========================================================================
    # HTTPS SERVER - Main Application
    # ========================================================================
    server {
        listen 443 ssl http2;
        server_name presgen.net www.presgen.net;

        # SSL Configuration
        include /etc/nginx/ssl.conf;

        # Security headers (enhanced for HTTPS)
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;

        # Basic Authentication
        auth_basic "PresGen Demo - Authorized Access Only";
        auth_basic_user_file /etc/nginx/auth/.htpasswd;

        # Global connection limit
        limit_conn conn_limit 10;

        # ... (all location blocks from previous config) ...
        # (Copy all location blocks from the HTTP-only config)
    }
}
```

### 2.4 Deployment Steps

```bash
# On Lightsail instance:

# 1. Setup DNS first (wait for propagation)
dig presgen.net +short
# Verify it shows your Lightsail IP

# 2. Run SSL setup script
chmod +x deployment/setup-ssl.sh
./deployment/setup-ssl.sh

# 3. Replace nginx config
cd /home/ubuntu/presgen
mv nginx/nginx.conf nginx/nginx-http-only.conf.backup
mv nginx/nginx-ssl.conf nginx/nginx.conf

# 4. Restart nginx
docker-compose restart nginx

# 5. Verify HTTPS
curl -I https://presgen.net
# Should show: HTTP/2 200

# 6. Test auto-renewal
sudo certbot renew --dry-run
# Should show: Congratulations, all simulated renewals succeeded
```

---

## 3. Backup and Restore System

### 3.1 Enhanced Backup Script

**File:** `scripts/backup-with-verification.sh`

```bash
#!/bin/bash
set -e

# Enhanced Backup Script with Verification
# Location: /home/ubuntu/presgen/scripts/backup-with-verification.sh

# Configuration
BACKUP_DIR="/home/ubuntu/presgen/backups"
S3_BUCKET="presgen-backups-788159322332"  # Must be globally unique
AWS_REGION="us-east-1"
RETENTION_DAYS=30
SNS_TOPIC_ARN="arn:aws:sns:us-east-1:788159322332:presgen-alerts"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

send_notification() {
    local subject="$1"
    local message="$2"

    aws sns publish \
        --topic-arn "${SNS_TOPIC_ARN}" \
        --subject "${subject}" \
        --message "${message}" \
        --region "${AWS_REGION}" 2>/dev/null || log_warning "Failed to send SNS notification"
}

# ============================================================================
# Backup Functions
# ============================================================================

backup_database() {
    log_info "📊 Backing up database..."

    local db_backup="${BACKUP_DIR}/database-${TIMESTAMP}.sql"

    # Export SQLite database
    docker exec presgen-assess sqlite3 /app/data/presgen_assess.db .dump | gzip > "${db_backup}.gz"

    if [ -f "${db_backup}.gz" ]; then
        local size=$(du -h "${db_backup}.gz" | cut -f1)
        log_info "✅ Database backup created: ${db_backup}.gz (${size})"
        echo "${db_backup}.gz"
    else
        log_error "❌ Database backup failed"
        return 1
    fi
}

backup_secrets() {
    log_info "🔐 Backing up secrets..."

    local secrets_backup="${BACKUP_DIR}/secrets-${TIMESTAMP}.tar.gz"

    tar -czf "${secrets_backup}" -C /home/ubuntu/presgen secrets/

    if [ -f "${secrets_backup}" ]; then
        log_info "✅ Secrets backup created: ${secrets_backup}"
        echo "${secrets_backup}"
    else
        log_error "❌ Secrets backup failed"
        return 1
    fi
}

backup_config() {
    log_info "⚙️  Backing up configuration..."

    local config_backup="${BACKUP_DIR}/config-${TIMESTAMP}.tar.gz"

    tar -czf "${config_backup}" \
        /home/ubuntu/presgen/.env \
        /home/ubuntu/presgen/docker-compose.yml \
        /home/ubuntu/presgen/nginx/ \
        /etc/nginx/auth/.htpasswd 2>/dev/null || true

    if [ -f "${config_backup}" ]; then
        log_info "✅ Configuration backup created: ${config_backup}"
        echo "${config_backup}"
    else
        log_error "❌ Configuration backup failed"
        return 1
    fi
}

backup_volumes() {
    log_info "💾 Backing up Docker volumes..."

    local volumes_backup="${BACKUP_DIR}/volumes-${TIMESTAMP}.tar.gz"

    docker run --rm \
        -v presgen_assess_data:/data \
        -v presgen_redis_data:/redis \
        -v "${BACKUP_DIR}:/backup" \
        alpine tar -czf "/backup/volumes-${TIMESTAMP}.tar.gz" /data /redis 2>/dev/null || true

    if [ -f "${volumes_backup}" ]; then
        log_info "✅ Volumes backup created: ${volumes_backup}"
        echo "${volumes_backup}"
    else
        log_warning "⚠️  Volumes backup skipped (may not exist)"
        return 0
    fi
}

create_full_backup() {
    log_info "🎯 Creating full backup..."

    local full_backup="${BACKUP_DIR}/full-backup-${TIMESTAMP}.tar.gz"

    # Backup individual components
    local db_file=$(backup_database)
    local secrets_file=$(backup_secrets)
    local config_file=$(backup_config)
    local volumes_file=$(backup_volumes)

    # Create manifest
    cat > "${BACKUP_DIR}/manifest-${TIMESTAMP}.txt" << EOF
PresGen Backup Manifest
======================
Timestamp: ${TIMESTAMP}
Hostname: $(hostname)
IP Address: $(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)

Components:
- Database: ${db_file}
- Secrets: ${secrets_file}
- Config: ${config_file}
- Volumes: ${volumes_file}

Docker Images:
$(docker images --format "{{.Repository}}:{{.Tag}} ({{.Size}})")

System Info:
- Disk Usage: $(df -h /home/ubuntu | tail -1)
- Memory: $(free -h | grep Mem | awk '{print $3 "/" $2}')
- Uptime: $(uptime -p)
EOF

    # Combine all backups
    tar -czf "${full_backup}" \
        "${db_file}" \
        "${secrets_file}" \
        "${config_file}" \
        "${BACKUP_DIR}/manifest-${TIMESTAMP}.txt" 2>/dev/null

    if [ -f "${full_backup}" ]; then
        log_info "✅ Full backup created: ${full_backup}"
        echo "${full_backup}"
    else
        log_error "❌ Full backup creation failed"
        return 1
    fi
}

calculate_checksum() {
    local file="$1"
    sha256sum "${file}" | awk '{print $1}'
}

upload_to_s3() {
    local file="$1"
    local s3_path="s3://${S3_BUCKET}/backups/$(basename ${file})"

    log_info "☁️  Uploading to S3: ${s3_path}"

    # Upload file
    if aws s3 cp "${file}" "${s3_path}" --region "${AWS_REGION}"; then
        log_info "✅ Uploaded: ${file}"

        # Upload checksum
        local checksum=$(calculate_checksum "${file}")
        echo "${checksum}" | aws s3 cp - "${s3_path}.sha256" --region "${AWS_REGION}"

        return 0
    else
        log_error "❌ Upload failed: ${file}"
        return 1
    fi
}

verify_backup() {
    local file="$1"
    local s3_path="s3://${S3_BUCKET}/backups/$(basename ${file})"

    log_info "🔍 Verifying backup..."

    # Get local checksum
    local local_checksum=$(calculate_checksum "${file}")

    # Get remote checksum
    local remote_checksum=$(aws s3 cp "${s3_path}.sha256" - --region "${AWS_REGION}" 2>/dev/null | tr -d '\n')

    if [ "${local_checksum}" = "${remote_checksum}" ]; then
        log_info "✅ Backup verified: checksums match"
        return 0
    else
        log_error "❌ Backup verification FAILED: checksums don't match"
        log_error "   Local:  ${local_checksum}"
        log_error "   Remote: ${remote_checksum}"
        return 1
    fi
}

cleanup_old_backups() {
    log_info "🧹 Cleaning up old backups..."

    # Local cleanup
    find "${BACKUP_DIR}" -name "*.tar.gz" -mtime +${RETENTION_DAYS} -delete
    find "${BACKUP_DIR}" -name "*.sql.gz" -mtime +${RETENTION_DAYS} -delete
    find "${BACKUP_DIR}" -name "*.txt" -mtime +${RETENTION_DAYS} -delete

    # S3 cleanup (backups older than retention days)
    local cutoff_date=$(date -d "${RETENTION_DAYS} days ago" +%Y-%m-%d)
    aws s3 ls "s3://${S3_BUCKET}/backups/" --region "${AWS_REGION}" | while read -r line; do
        local backup_date=$(echo $line | awk '{print $1}')
        local backup_file=$(echo $line | awk '{print $4}')

        if [[ "${backup_date}" < "${cutoff_date}" ]]; then
            log_info "Deleting old backup: ${backup_file}"
            aws s3 rm "s3://${S3_BUCKET}/backups/${backup_file}" --region "${AWS_REGION}"
        fi
    done

    log_info "✅ Cleanup complete"
}

test_restore() {
    log_info "🧪 Testing restore procedure (monthly check)..."

    # Download latest backup
    local latest_backup=$(aws s3 ls "s3://${S3_BUCKET}/backups/" --region "${AWS_REGION}" | \
                         grep "full-backup-" | sort | tail -n 1 | awk '{print $4}')

    if [ -z "${latest_backup}" ]; then
        log_warning "⚠️  No backups found for restore test"
        return 0
    fi

    log_info "Testing restore of: ${latest_backup}"

    # Download to temp location
    local test_dir="/tmp/restore-test-$(date +%s)"
    mkdir -p "${test_dir}"

    aws s3 cp "s3://${S3_BUCKET}/backups/${latest_backup}" "${test_dir}/" --region "${AWS_REGION}"

    # Extract
    tar -xzf "${test_dir}/${latest_backup}" -C "${test_dir}/" 2>/dev/null || {
        log_error "❌ Restore test FAILED: cannot extract backup"
        rm -rf "${test_dir}"
        return 1
    }

    # Verify critical files exist
    if ls "${test_dir}"/*database*.sql.gz >/dev/null 2>&1 && \
       ls "${test_dir}"/*secrets*.tar.gz >/dev/null 2>&1 && \
       ls "${test_dir}"/*config*.tar.gz >/dev/null 2>&1; then
        log_info "✅ Restore test PASSED: all components present"
        rm -rf "${test_dir}"
        return 0
    else
        log_error "❌ Restore test FAILED: missing components"
        rm -rf "${test_dir}"
        return 1
    fi
}

# ============================================================================
# Main Execution
# ============================================================================

main() {
    TIMESTAMP=$(date +%Y%m%d-%H%M%S)

    log_info "🚀 Starting PresGen backup process..."

    # Create backup directory
    mkdir -p "${BACKUP_DIR}"

    # Create S3 bucket if it doesn't exist
    if ! aws s3 ls "s3://${S3_BUCKET}" --region "${AWS_REGION}" 2>/dev/null; then
        log_info "Creating S3 bucket: ${S3_BUCKET}"
        aws s3 mb "s3://${S3_BUCKET}" --region "${AWS_REGION}"

        # Enable versioning
        aws s3api put-bucket-versioning \
            --bucket "${S3_BUCKET}" \
            --versioning-configuration Status=Enabled \
            --region "${AWS_REGION}"
    fi

    # Create full backup
    backup_file=$(create_full_backup)

    if [ -z "${backup_file}" ]; then
        send_notification \
            "⚠️ PresGen Backup FAILED" \
            "Backup creation failed at $(date). Please investigate immediately."
        exit 1
    fi

    # Upload to S3
    if ! upload_to_s3 "${backup_file}"; then
        send_notification \
            "⚠️ PresGen Backup Upload FAILED" \
            "Backup created but S3 upload failed at $(date). Backup is available locally at: ${backup_file}"
        exit 1
    fi

    # Verify backup
    if ! verify_backup "${backup_file}"; then
        send_notification \
            "⚠️ PresGen Backup Verification FAILED" \
            "Backup uploaded but verification failed at $(date). Backup may be corrupted."
        exit 1
    fi

    # Cleanup old backups
    cleanup_old_backups

    # Test restore (on 1st of each month)
    if [ "$(date +%d)" = "01" ]; then
        if ! test_restore; then
            send_notification \
                "⚠️ PresGen Restore Test FAILED" \
                "Monthly restore test failed at $(date). Backup integrity may be compromised."
        else
            send_notification \
                "✅ PresGen Restore Test PASSED" \
                "Monthly restore test completed successfully at $(date)."
        fi
    fi

    # Success notification
    local backup_size=$(du -h "${backup_file}" | cut -f1)
    send_notification \
        "✅ PresGen Backup Successful" \
        "Backup completed successfully at $(date).\n\nFile: $(basename ${backup_file})\nSize: ${backup_size}\nLocation: s3://${S3_BUCKET}/backups/\n\nAll verification checks passed."

    log_info "✅ Backup process completed successfully!"
    log_info "📦 Backup file: ${backup_file}"
    log_info "📊 Backup size: ${backup_size}"
}

# Run main function
main "$@"
```

### 3.2 Restore Script

**File:** `scripts/restore.sh`

```bash
#!/bin/bash
set -e

# Restore Script
# Location: /home/ubuntu/presgen/scripts/restore.sh

S3_BUCKET="presgen-backups-788159322332"
AWS_REGION="us-east-1"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

usage() {
    echo "Usage: $0 [backup-filename | 'latest' | 'list']"
    echo ""
    echo "Commands:"
    echo "  list    - List available backups"
    echo "  latest  - Restore from most recent backup"
    echo "  <file>  - Restore from specific backup file"
    echo ""
    echo "Examples:"
    echo "  $0 list"
    echo "  $0 latest"
    echo "  $0 full-backup-20251029-120000.tar.gz"
}

list_backups() {
    log_info "📋 Available backups in S3:"
    echo ""
    aws s3 ls "s3://${S3_BUCKET}/backups/" --region "${AWS_REGION}" | \
        grep "full-backup-" | \
        awk '{printf "  %s %s - %s (%s)\n", $1, $2, $4, $3}'
}

restore_from_backup() {
    local backup_file="$1"
    local restore_dir="/tmp/presgen-restore-$(date +%s)"

    log_info "🔄 Starting restore process..."
    log_info "📦 Backup file: ${backup_file}"

    # Create restore directory
    mkdir -p "${restore_dir}"

    # Download backup from S3
    log_info "⬇️  Downloading backup from S3..."
    if ! aws s3 cp "s3://${S3_BUCKET}/backups/${backup_file}" "${restore_dir}/" --region "${AWS_REGION}"; then
        log_error "Failed to download backup from S3"
        rm -rf "${restore_dir}"
        exit 1
    fi

    # Download and verify checksum
    log_info "🔍 Verifying backup integrity..."
    aws s3 cp "s3://${S3_BUCKET}/backups/${backup_file}.sha256" "${restore_dir}/" --region "${AWS_REGION}"

    local expected_checksum=$(cat "${restore_dir}/${backup_file}.sha256")
    local actual_checksum=$(sha256sum "${restore_dir}/${backup_file}" | awk '{print $1}')

    if [ "${expected_checksum}" != "${actual_checksum}" ]; then
        log_error "Checksum verification FAILED!"
        log_error "  Expected: ${expected_checksum}"
        log_error "  Actual:   ${actual_checksum}"
        rm -rf "${restore_dir}"
        exit 1
    fi
    log_info "✅ Checksum verified"

    # Extract backup
    log_info "📂 Extracting backup..."
    tar -xzf "${restore_dir}/${backup_file}" -C "${restore_dir}/"

    # Show manifest
    if [ -f "${restore_dir}/manifest-"*.txt ]; then
        log_info "📄 Backup manifest:"
        cat "${restore_dir}/manifest-"*.txt
        echo ""
    fi

    # Confirm restore
    echo -e "${YELLOW}⚠️  WARNING: This will stop all services and restore from backup!${NC}"
    echo -e "${YELLOW}   Current data will be backed up to /home/ubuntu/presgen.pre-restore-$(date +%s)${NC}"
    read -p "Are you sure you want to continue? (yes/no): " -r

    if [ "$REPLY" != "yes" ]; then
        log_info "Restore cancelled by user"
        rm -rf "${restore_dir}"
        exit 0
    fi

    # Stop services
    log_info "⏹️  Stopping services..."
    cd /home/ubuntu/presgen
    docker-compose down

    # Backup current state
    local backup_current="/home/ubuntu/presgen.pre-restore-$(date +%s)"
    log_info "💾 Backing up current state to: ${backup_current}"
    sudo mv /home/ubuntu/presgen "${backup_current}"

    # Create new presgen directory
    sudo mkdir -p /home/ubuntu/presgen
    cd /home/ubuntu/presgen

    # Restore database
    log_info "📊 Restoring database..."
    local db_backup=$(ls "${restore_dir}"/*database*.sql.gz 2>/dev/null | head -1)
    if [ -n "${db_backup}" ]; then
        mkdir -p /home/ubuntu/presgen/data
        gunzip -c "${db_backup}" > /home/ubuntu/presgen/data/restore.sql
        log_info "✅ Database restore file prepared"
    fi

    # Restore secrets
    log_info "🔐 Restoring secrets..."
    local secrets_backup=$(ls "${restore_dir}"/*secrets*.tar.gz 2>/dev/null | head -1)
    if [ -n "${secrets_backup}" ]; then
        tar -xzf "${secrets_backup}" -C /home/ubuntu/presgen/
        sudo chmod 600 /home/ubuntu/presgen/secrets/*
        log_info "✅ Secrets restored"
    fi

    # Restore config
    log_info "⚙️  Restoring configuration..."
    local config_backup=$(ls "${restore_dir}"/*config*.tar.gz 2>/dev/null | head -1)
    if [ -n "${config_backup}" ]; then
        tar -xzf "${config_backup}" -C /
        log_info "✅ Configuration restored"
    fi

    # Fix permissions
    sudo chown -R ubuntu:ubuntu /home/ubuntu/presgen

    # Restart services
    log_info "🚀 Starting services..."
    cd /home/ubuntu/presgen

    # Import database if needed
    if [ -f "/home/ubuntu/presgen/data/restore.sql" ]; then
        docker-compose up -d presgen-assess
        sleep 10
        cat /home/ubuntu/presgen/data/restore.sql | docker exec -i presgen-assess sqlite3 /app/data/presgen_assess.db
        rm /home/ubuntu/presgen/data/restore.sql
    fi

    docker-compose up -d

    # Wait for services to be healthy
    log_info "⏳ Waiting for services to be healthy..."
    sleep 30

    # Verify services
    if docker-compose ps | grep -q "Up"; then
        log_info "✅ Restore completed successfully!"
        log_info "📁 Previous data backed up to: ${backup_current}"
        log_info "🌐 Application should be available shortly at: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)"
    else
        log_error "❌ Service start failed! Check logs with: docker-compose logs"
        log_error "Previous data is at: ${backup_current}"
        exit 1
    fi

    # Cleanup
    rm -rf "${restore_dir}"
}

# Main
case "${1:-}" in
    list)
        list_backups
        ;;
    latest)
        BACKUP_FILE=$(aws s3 ls "s3://${S3_BUCKET}/backups/" --region "${AWS_REGION}" | \
                     grep "full-backup-" | sort | tail -n 1 | awk '{print $4}')
        if [ -z "${BACKUP_FILE}" ]; then
            log_error "No backups found in S3"
            exit 1
        fi
        restore_from_backup "${BACKUP_FILE}"
        ;;
    "")
        usage
        ;;
    *)
        restore_from_backup "$1"
        ;;
esac
```

### 3.3 Setup Automated Backups

```bash
# File: deployment/setup-backups.sh
#!/bin/bash
set -e

echo "📦 Setting up automated backups..."

# 1. Make scripts executable
chmod +x /home/ubuntu/presgen/scripts/backup-with-verification.sh
chmod +x /home/ubuntu/presgen/scripts/restore.sh

# 2. Create SNS topic for alerts
TOPIC_ARN=$(aws sns create-topic \
    --name presgen-alerts \
    --region us-east-1 \
    --output text --query 'TopicArn')

echo "Created SNS topic: ${TOPIC_ARN}"

# 3. Subscribe email to SNS topic
aws sns subscribe \
    --topic-arn "${TOPIC_ARN}" \
    --protocol email \
    --notification-endpoint ymeirovich@gmail.com \
    --region us-east-1

echo "📧 Confirmation email sent to ymeirovich@gmail.com - please confirm subscription"

# 4. Set up cron job for daily backups at 2 AM
sudo tee /etc/cron.d/presgen-backup > /dev/null << 'EOF'
# PresGen Daily Backup - 2 AM every day
0 2 * * * ubuntu /home/ubuntu/presgen/scripts/backup-with-verification.sh >> /var/log/presgen-backup.log 2>&1
EOF

echo "✅ Automated backups configured!"
echo "   - Daily backups at 2:00 AM"
echo "   - Retention: 30 days"
echo "   - Monthly restore tests on 1st of each month"
echo "   - Email alerts to: ymeirovich@gmail.com"
```

---

## 4. Google Cloud API Quota Management

### 4.1 Exponential Backoff Retry Logic

**File:** `src/agent/google_api_retry.py` (NEW FILE)

```python
"""
Google API Retry Logic with Exponential Backoff
Handles quota exceeded, rate limiting, and transient errors
"""

import logging
import time
from functools import wraps
from typing import Callable, Any, Optional
from googleapiclient.errors import HttpError

log = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 5
INITIAL_BACKOFF = 1  # seconds
MAX_BACKOFF = 60  # seconds
BACKOFF_MULTIPLIER = 2


class QuotaExceededError(Exception):
    """Raised when Google API quota is exceeded after all retries."""
    pass


class APIError(Exception):
    """Raised when Google API returns a non-retryable error."""
    pass


def is_retryable_error(error: HttpError) -> bool:
    """
    Determine if an HTTP error is retryable.

    Retryable errors:
    - 429: Too Many Requests (rate limiting)
    - 500, 502, 503, 504: Server errors
    - 403 with 'rateLimitExceeded' or 'userRateLimitExceeded'
    """
    if not isinstance(error, HttpError):
        return False

    status = error.resp.status

    # Always retry server errors and 429
    if status in [429, 500, 502, 503, 504]:
        return True

    # Check for quota/rate limit errors in 403
    if status == 403:
        error_details = str(error).lower()
        if any(keyword in error_details for keyword in [
            'quota', 'rate', 'limit', 'exceeded', 'ratelimitexceeded'
        ]):
            return True

    return False


def calculate_backoff(attempt: int) -> float:
    """Calculate exponential backoff time with jitter."""
    import random

    backoff = min(
        INITIAL_BACKOFF * (BACKOFF_MULTIPLIER ** attempt),
        MAX_BACKOFF
    )

    # Add jitter (±20%)
    jitter = backoff * 0.2 * (2 * random.random() - 1)
    return backoff + jitter


def with_retry(
    max_retries: int = MAX_RETRIES,
    on_retry: Optional[Callable[[int, Exception], None]] = None
):
    """
    Decorator to add exponential backoff retry logic to Google API calls.

    Usage:
        @with_retry(max_retries=5)
        def create_presentation(service, title):
            return service.presentations().create(body={'title': title}).execute()

    Args:
        max_retries: Maximum number of retry attempts
        on_retry: Optional callback function called before each retry
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)

                except HttpError as e:
                    last_exception = e

                    if not is_retryable_error(e):
                        # Non-retryable error, raise immediately
                        log.error(f"Non-retryable error in {func.__name__}: {e}")
                        raise APIError(f"{func.__name__} failed: {e}") from e

                    if attempt >= max_retries:
                        # Max retries exceeded
                        log.error(
                            f"Max retries ({max_retries}) exceeded for {func.__name__}"
                        )
                        raise QuotaExceededError(
                            f"Google API quota/rate limit exceeded after {max_retries} retries"
                        ) from e

                    # Calculate backoff and retry
                    backoff_time = calculate_backoff(attempt)

                    log.warning(
                        f"Retryable error in {func.__name__} "
                        f"(attempt {attempt + 1}/{max_retries}): {e}. "
                        f"Retrying in {backoff_time:.1f}s..."
                    )

                    # Call custom retry callback if provided
                    if on_retry:
                        try:
                            on_retry(attempt + 1, e)
                        except Exception as callback_error:
                            log.error(f"Error in retry callback: {callback_error}")

                    time.sleep(backoff_time)

                except Exception as e:
                    # Unexpected error
                    log.error(f"Unexpected error in {func.__name__}: {e}")
                    raise

            # Should never reach here, but just in case
            raise last_exception

        return wrapper
    return decorator


# Convenience decorators for specific retry scenarios
def with_slides_api_retry(func: Callable) -> Callable:
    """Retry decorator optimized for Slides API (more retries, longer backoff)."""
    return with_retry(max_retries=7)(func)


def with_drive_api_retry(func: Callable) -> Callable:
    """Retry decorator optimized for Drive API."""
    return with_retry(max_retries=5)(func)


def with_forms_api_retry(func: Callable) -> Callable:
    """Retry decorator optimized for Forms API."""
    return with_retry(max_retries=5)(func)


# Monitoring callback for CloudWatch metrics
def log_retry_attempt(attempt: int, error: Exception) -> None:
    """
    Log retry attempts for monitoring.
    Can be extended to push metrics to CloudWatch.
    """
    log.warning(
        f"Google API retry attempt {attempt}: {error}",
        extra={
            'metric_name': 'google_api_retry',
            'attempt': attempt,
            'error_type': type(error).__name__,
            'error_message': str(error)
        }
    )
```

### 4.2 Update Slides Agent with Retry Logic

**File:** `src/agent/slides_google.py` (UPDATE)

```python
# Add import at top
from src.agent.google_api_retry import (
    with_slides_api_retry,
    QuotaExceededError,
    APIError,
    log_retry_attempt
)

# Update create_presentation function
@with_slides_api_retry
def create_presentation(title: str, template_id: Optional[str] = None) -> str:
    """
    Create a new Google Slides presentation with retry logic.

    Args:
        title: Presentation title
        template_id: Optional template presentation ID to copy

    Returns:
        Presentation ID

    Raises:
        QuotaExceededError: If quota exceeded after all retries
        APIError: If non-retryable error occurs
    """
    service = _get_slides_service()

    body = {'title': title}

    try:
        if template_id:
            # Copy from template
            drive_service = _get_drive_service()
            copied_file = drive_service.files().copy(
                fileId=template_id,
                body={'name': title}
            ).execute()
            presentation_id = copied_file['id']
        else:
            # Create new presentation
            presentation = service.presentations().create(body=body).execute()
            presentation_id = presentation['presentationId']

        log.info(f"✅ Created presentation: {presentation_id}")
        return presentation_id

    except QuotaExceededError:
        log.error("Google Slides API quota exceeded. Please try again later.")
        # Send alert
        _send_quota_alert("Slides API")
        raise

    except APIError as e:
        log.error(f"Failed to create presentation: {e}")
        raise


@with_slides_api_retry
def add_slide(presentation_id: str, layout: str = "BLANK") -> str:
    """Add a slide to presentation with retry logic."""
    service = _get_slides_service()

    requests = [{
        'createSlide': {
            'slideLayoutReference': {
                'predefinedLayout': layout
            }
        }
    }]

    response = service.presentations().batchUpdate(
        presentationId=presentation_id,
        body={'requests': requests}
    ).execute()

    slide_id = response['replies'][0]['createSlide']['objectId']
    log.info(f"✅ Added slide: {slide_id}")
    return slide_id


def _send_quota_alert(api_name: str) -> None:
    """Send alert when quota is exceeded."""
    try:
        import boto3

        sns = boto3.client('sns', region_name='us-east-1')
        topic_arn = "arn:aws:sns:us-east-1:788159322332:presgen-alerts"

        sns.publish(
            TopicArn=topic_arn,
            Subject=f"⚠️ Google {api_name} Quota Exceeded",
            Message=f"""
Google {api_name} quota has been exceeded on PresGen demo instance.

Time: {datetime.now().isoformat()}
Server: {socket.gethostname()}

This may impact demo functionality. Please:
1. Check quota usage in Google Cloud Console
2. Request quota increase if needed
3. Reduce API call frequency

Dashboard: https://console.cloud.google.com/apis/dashboard?project=presgen
            """.strip()
        )
    except Exception as e:
        log.error(f"Failed to send quota alert: {e}")
```

### 4.3 Quota Monitoring Script

**File:** `scripts/monitor-quotas.sh`

```bash
#!/bin/bash

# Google Cloud API Quota Monitoring
# Run this periodically to check quota usage

PROJECT_ID="presgen"

echo "📊 Google Cloud API Quota Usage for project: ${PROJECT_ID}"
echo "================================================================"

check_quota() {
    local service="$1"
    local metric="$2"
    local friendly_name="$3"

    echo ""
    echo "🔍 ${friendly_name}:"

    gcloud services quota list \
        --service="${service}" \
        --consumer="project:${PROJECT_ID}" \
        --filter="metric.type:${metric}" \
        --format="table(
            metric.displayName,
            consumerQuotaLimits.quotaBuckets.effectiveLimit,
            consumerQuotaLimits.quotaBuckets.usage
        )" 2>/dev/null || echo "  ⚠️  Unable to fetch quota"
}

# Check Slides API quota
check_quota "slides.googleapis.com" \
    "slides.googleapis.com/quota/read_requests" \
    "Google Slides API - Read Requests"

check_quota "slides.googleapis.com" \
    "slides.googleapis.com/quota/write_requests" \
    "Google Slides API - Write Requests"

# Check Drive API quota
check_quota "drive.googleapis.com" \
    "drive.googleapis.com/quota/queries" \
    "Google Drive API - Queries"

# Check Forms API quota
check_quota "forms.googleapis.com" \
    "forms.googleapis.com/quota/read_requests" \
    "Google Forms API - Read Requests"

# Check Vertex AI quota
check_quota "aiplatform.googleapis.com" \
    "aiplatform.googleapis.com/online_prediction_requests_per_base_model" \
    "Vertex AI - Prediction Requests"

echo ""
echo "================================================================"
echo "💡 Tip: Request quota increase at:"
echo "   https://console.cloud.google.com/apis/quotas?project=${PROJECT_ID}"
echo ""
echo "📈 View quota metrics at:"
echo "   https://console.cloud.google.com/apis/dashboard?project=${PROJECT_ID}"
```

### 4.4 Request Quota Increase

**File:** `scripts/request-quota-increase.sh`

```bash
#!/bin/bash

# Request Google Cloud API Quota Increase
# Run this BEFORE demo (takes 2-5 business days to process)

PROJECT_ID="presgen"

echo "📝 Requesting quota increases for project: ${PROJECT_ID}"
echo "⚠️  Note: Quota increase requests typically take 2-5 business days"
echo ""

request_quota() {
    local service="$1"
    local metric="$2"
    local new_limit="$3"
    local friendly_name="$4"

    echo "📤 Requesting: ${friendly_name} → ${new_limit}"

    gcloud alpha services quota update \
        --service="${service}" \
        --consumer="project:${PROJECT_ID}" \
        --metric="${metric}" \
        --value="${new_limit}" \
        --force 2>/dev/null && echo "  ✅ Request submitted" || echo "  ⚠️  Request failed"
}

# Request increases for demo workload
echo "Submitting quota increase requests..."
echo ""

request_quota \
    "slides.googleapis.com" \
    "ReadRequests" \
    "1000" \
    "Slides API Read Requests (from 300 to 1000 per minute)"

request_quota \
    "slides.googleapis.com" \
    "WriteRequests" \
    "500" \
    "Slides API Write Requests (from 100 to 500 per minute)"

request_quota \
    "drive.googleapis.com" \
    "Queries" \
    "2000" \
    "Drive API Queries (from 1000 to 2000 per 100 seconds)"

request_quota \
    "forms.googleapis.com" \
    "ReadRequests" \
    "1000" \
    "Forms API Read Requests (from 300 to 1000 per minute)"

echo ""
echo "================================================================"
echo "✅ Quota increase requests submitted!"
echo ""
echo "📧 You'll receive email updates on request status"
echo "📊 Track requests at:"
echo "   https://console.cloud.google.com/apis/quotas?project=${PROJECT_ID}"
echo ""
echo "⏰ Timeline:"
echo "   - Auto-approved (instant): Small increases"
echo "   - Manual review (2-5 days): Larger increases"
echo ""
echo "💡 Tip: Submit these requests 1 week before your demo!"
```

---

## 5. Troubleshooting Runbooks

### 5.1 Docker Container Won't Start

**File:** `aws_migration/runbooks/DOCKER_CONTAINER_WONT_START.md`

```markdown
# Runbook: Docker Container Won't Start

**Symptom:** Container exits immediately or won't start
**Detection:** `docker ps` shows container missing or exited status
**Time to resolve:** 5-15 minutes

---

## Quick Diagnosis

```bash
# Check container status
docker-compose ps

# Check container logs
docker-compose logs presgen-core
docker-compose logs presgen-assess
docker-compose logs presgen-ui

# Check recent errors
docker-compose logs --tail=50 --timestamps presgen-core | grep -i error
```

---

## Common Causes & Solutions

### 1. Port Already in Use

**Symptoms:**
```
Error starting userland proxy: listen tcp 0.0.0.0:8080: bind: address already in use
```

**Solution:**
```bash
# Find process using the port
sudo lsof -i :8080

# Kill the process
sudo kill -9 <PID>

# Or change port in docker-compose.yml
# ports:
#   - "8081:8080"  # Change 8080 to 8081

# Restart
docker-compose up -d
```

### 2. Missing Environment Variables

**Symptoms:**
```
KeyError: 'GOOGLE_APPLICATION_CREDENTIALS'
RuntimeError: Required environment variable not set
```

**Solution:**
```bash
# Check .env file exists
ls -la /home/ubuntu/presgen/.env

# Verify required variables
cat .env | grep -E "GOOGLE|OPENAI|OAUTH"

# If missing, add them:
nano .env

# Required variables:
# GOOGLE_APPLICATION_CREDENTIALS=/secrets/google-creds.json
# OAUTH_TOKEN_PATH=/secrets/token.json
# OPENAI_API_KEY=sk-...
# GOOGLE_CLOUD_PROJECT=presgen

# Restart containers
docker-compose down
docker-compose up -d
```

### 3. Missing Secrets Files

**Symptoms:**
```
FileNotFoundError: [Errno 2] No such file or directory: '/secrets/google-creds.json'
```

**Solution:**
```bash
# Check if secrets directory exists
ls -lh /home/ubuntu/presgen/secrets/

# If missing, upload from local machine:
# On your Mac:
scp -i lightsail-key.pem secrets/google-creds.json ubuntu@IP:/home/ubuntu/presgen/secrets/
scp -i lightsail-key.pem secrets/token.json ubuntu@IP:/home/ubuntu/presgen/secrets/
scp -i lightsail-key.pem secrets/oauth_slides_client.json ubuntu@IP:/home/ubuntu/presgen/secrets/

# On server, fix permissions:
chmod 600 /home/ubuntu/presgen/secrets/*
chown ubuntu:ubuntu /home/ubuntu/presgen/secrets/*

# Restart
docker-compose restart
```

### 4. Python Dependency Issues

**Symptoms:**
```
ModuleNotFoundError: No module named 'google'
ImportError: cannot import name 'X' from 'Y'
```

**Solution:**
```bash
# Rebuild image without cache
docker-compose build --no-cache presgen-core
docker-compose build --no-cache presgen-assess

# Check requirements.txt is correct
cat presgen-assess/requirements.txt | grep google

# If updated requirements, rebuild:
docker-compose down
docker-compose up -d --build
```

### 5. Database Connection Errors

**Symptoms:**
```
sqlalchemy.exc.OperationalError: unable to open database file
sqlite3.OperationalError: disk I/O error
```

**Solution:**
```bash
# Check disk space
df -h

# If disk full, clean up:
docker system prune -af
find /var/log -type f -name "*.log" -mtime +7 -delete

# Check database file permissions
ls -lh /home/ubuntu/presgen/data/

# Fix permissions:
sudo chown -R ubuntu:ubuntu /home/ubuntu/presgen/data
chmod 755 /home/ubuntu/presgen/data

# Restart
docker-compose restart presgen-assess
```

### 6. Out of Memory (OOM)

**Symptoms:**
```
Killed
Container exited with code 137
```

**Solution:**
```bash
# Check memory usage
free -h
docker stats --no-stream

# Reduce memory limits in docker-compose.yml:
# services:
#   presgen-core:
#     mem_limit: 400m  # Reduce from 500m

# Or upgrade Lightsail instance:
aws lightsail stop-instance --instance-name presgen-demo
aws lightsail update-instance --instance-name presgen-demo --bundle-id medium_2_0
aws lightsail start-instance --instance-name presgen-demo
```

### 7. Docker Daemon Issues

**Symptoms:**
```
Cannot connect to the Docker daemon at unix:///var/run/docker.sock
```

**Solution:**
```bash
# Check Docker status
sudo systemctl status docker

# Restart Docker daemon
sudo systemctl restart docker

# Wait 30 seconds, then:
docker-compose up -d
```

---

## Complete Reset Procedure

If all else fails, perform a complete reset:

```bash
# 1. Stop everything
docker-compose down -v

# 2. Remove all containers and images
docker system prune -af
docker volume prune -f

# 3. Backup current data
sudo cp -r /home/ubuntu/presgen /home/ubuntu/presgen.backup-$(date +%s)

# 4. Pull fresh code (if using Git)
cd /home/ubuntu/presgen
git pull origin main

# 5. Rebuild everything
docker-compose build --no-cache

# 6. Start services
docker-compose up -d

# 7. Watch logs for errors
docker-compose logs -f
```

---

## Prevention

```bash
# Add health checks to docker-compose.yml:
services:
  presgen-core:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

# Add restart policy:
    restart: unless-stopped

# Monitor container restarts:
docker-compose ps --format "table {{.Name}}\t{{.Status}}"
```

---

## Escalation

If issue persists after trying all solutions:

1. **Collect diagnostic info:**
   ```bash
   docker-compose logs > /tmp/presgen-logs.txt
   docker ps -a >> /tmp/presgen-logs.txt
   df -h >> /tmp/presgen-logs.txt
   free -h >> /tmp/presgen-logs.txt
   ```

2. **Review logs carefully** for specific error messages

3. **Search GitHub issues** for similar problems

4. **Contact:** ymeirovich@gmail.com with diagnostic info
```

### 5.2 Database Locked Errors

**File:** `aws_migration/runbooks/DATABASE_LOCKED_ERRORS.md`

```markdown
# Runbook: Database Locked Errors

**Symptom:** "database is locked" or "database table is locked"
**Root Cause:** SQLite single-writer limitation with concurrent access
**Time to resolve:** 2-10 minutes

---

## Quick Fix (Immediate)

```bash
# 1. Restart the assess service
docker-compose restart presgen-assess

# 2. Wait 10 seconds
sleep 10

# 3. Test if issue resolved
curl http://localhost:8000/health
```

**If this fixes it:** Continue monitoring. If issue recurs frequently, proceed to "Permanent Solutions" below.

---

## Understanding the Problem

SQLite allows multiple readers OR one writer at a time. When multiple requests try to write simultaneously:

```
Request 1: BEGIN TRANSACTION → ✅ Gets write lock
Request 2: BEGIN TRANSACTION → ⏳ Waits for lock
Request 3: BEGIN TRANSACTION → ⏳ Waits for lock
Request 1: Takes too long...
Request 2: Timeout → ❌ "database is locked"
```

**Common Triggers:**
- Multiple users creating assessments simultaneously
- Long-running transactions (30+ seconds)
- Crashed transaction holding lock
- Disk I/O issues

---

## Diagnosis

### Check Current Status

```bash
# 1. Check for active database connections
docker exec presgen-assess python3 << 'EOF'
import sqlite3
db = sqlite3.connect('/app/data/presgen_assess.db')
cursor = db.cursor()

# Check for locked tables
try:
    cursor.execute("PRAGMA locking_mode;")
    print("Locking mode:", cursor.fetchone())

    cursor.execute("PRAGMA journal_mode;")
    print("Journal mode:", cursor.fetchone())
except sqlite3.OperationalError as e:
    print("Database locked:", e)
EOF

# 2. Check for slow queries
docker logs presgen-assess --since 5m | grep -i "slow\|timeout\|lock"

# 3. Check concurrent users
docker logs presgen-assess --since 1m | grep -c "POST /api/assess"
```

### Check Disk I/O

```bash
# Slow disk I/O can cause lock timeouts
iostat -x 1 5

# If %util is consistently >80%, disk is bottleneck
```

---

## Immediate Solutions

### Solution 1: Restart Service (Fastest)

```bash
# Restart clears all locks
docker-compose restart presgen-assess

# Verify service healthy
docker logs presgen-assess --tail 20
curl http://localhost:8000/health
```

### Solution 2: Clear Lock Manually

```bash
# Stop the service
docker-compose stop presgen-assess

# Remove lock files
sudo rm -f /home/ubuntu/presgen/data/presgen_assess.db-shm
sudo rm -f /home/ubuntu/presgen/data/presgen_assess.db-wal

# Start service
docker-compose start presgen-assess
```

### Solution 3: Increase Timeout

```python
# Edit presgen-assess/src/service/database.py
# Increase timeout from default 5s to 30s:

engine = create_engine(
    DATABASE_URL,
    connect_args={
        "timeout": 30.0,  # Increase from 5 to 30
        "check_same_thread": False
    }
)
```

---

## Permanent Solutions

### Option A: Add Retry Logic (Recommended for Demo)

**File:** `presgen-assess/src/service/database.py`

```python
from tenacity import retry, stop_after_attempt, wait_exponential
import sqlite3

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(sqlite3.OperationalError),
    before_sleep=lambda retry_state: log.warning(
        f"Database locked, retry attempt {retry_state.attempt_number}/5"
    )
)
def execute_with_retry(session, operation):
    """Execute database operation with automatic retry on lock."""
    return operation(session)

# Usage:
def save_workflow(workflow_data):
    return execute_with_retry(
        session,
        lambda s: s.add(workflow_data) and s.commit()
    )
```

**Deploy:**
```bash
# Add to requirements.txt:
tenacity==8.2.3

# Rebuild container:
docker-compose build --no-cache presgen-assess
docker-compose up -d presgen-assess
```

### Option B: Enable WAL Mode (Better Concurrency)

Write-Ahead Logging (WAL) allows simultaneous readers and one writer:

```bash
# Enable WAL mode on database
docker exec presgen-assess sqlite3 /app/data/presgen_assess.db << 'EOF'
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA cache_size=10000;
PRAGMA temp_store=MEMORY;
.quit
EOF

# Verify
docker exec presgen-assess sqlite3 /app/data/presgen_assess.db "PRAGMA journal_mode;"
# Should show: wal

# Restart to apply
docker-compose restart presgen-assess
```

### Option C: Migrate to PostgreSQL (Production Solution)

For >10 concurrent users, migrate from SQLite to PostgreSQL:

```yaml
# docker-compose.yml
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: presgen_assess
      POSTGRES_USER: presgen
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  presgen-assess:
    environment:
      DATABASE_URL: postgresql://presgen:${DB_PASSWORD}@postgres:5432/presgen_assess
    depends_on:
      - postgres

volumes:
  postgres_data:
```

**Migration Steps:**
```bash
# 1. Export SQLite data
docker exec presgen-assess sqlite3 /app/data/presgen_assess.db .dump > dump.sql

# 2. Convert to PostgreSQL format (remove SQLite-specific syntax)
sed -i 's/AUTOINCREMENT/SERIAL/g' dump.sql

# 3. Import to PostgreSQL
cat dump.sql | docker exec -i postgres psql -U presgen -d presgen_assess

# 4. Update DATABASE_URL in .env
echo "DATABASE_URL=postgresql://presgen:PASSWORD@postgres:5432/presgen_assess" >> .env

# 5. Restart
docker-compose down
docker-compose up -d
```

---

## Monitoring & Prevention

### Add Lock Monitoring

```python
# Add to presgen-assess/src/service/middleware.py

import time
import logging
from contextlib import contextmanager

log = logging.getLogger(__name__)

@contextmanager
def monitor_db_lock(operation_name: str):
    """Monitor database operations for lock issues."""
    start_time = time.time()
    try:
        yield
        duration = time.time() - start_time

        if duration > 5:
            log.warning(
                f"Slow database operation: {operation_name} took {duration:.2f}s"
            )
    except sqlite3.OperationalError as e:
        if "locked" in str(e).lower():
            log.error(
                f"Database lock error in {operation_name} after {time.time() - start_time:.2f}s"
            )
            # Send alert
            send_alert("Database Lock Error", str(e))
        raise

# Usage:
with monitor_db_lock("save_workflow"):
    session.add(workflow)
    session.commit()
```

### Rate Limit Database-Heavy Operations

```python
# Add to presgen-assess/src/service/app.py

from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/assess/workflows")
@limiter.limit("5/minute")  # Limit concurrent assessment creation
async def create_workflow(request: Request):
    pass
```

### Set CloudWatch Alert

```bash
# Alert on database lock errors
aws logs put-metric-filter \
  --log-group-name /aws/lightsail/presgen \
  --filter-name DatabaseLockErrors \
  --filter-pattern "[timestamp, request_id, level=ERROR, msg='*database*locked*']" \
  --metric-transformations \
      metricName=DatabaseLockErrorCount,\
      metricNamespace=PresGen,\
      metricValue=1

# Create alarm
aws cloudwatch put-metric-alarm \
  --alarm-name presgen-database-locks \
  --alarm-description "Alert on database lock errors" \
  --metric-name DatabaseLockErrorCount \
  --namespace PresGen \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:788159322332:presgen-alerts
```

---

## Decision Tree

```
Database Locked Error
│
├─ First occurrence?
│  ├─ Yes → Restart service (Solution 1)
│  └─ No → Proceed below
│
├─ Frequency?
│  ├─ Rare (<5/day) → Enable WAL mode (Option B)
│  ├─ Occasional (5-20/day) → Add retry logic (Option A) + WAL mode
│  └─ Frequent (>20/day) → Migrate to PostgreSQL (Option C)
│
└─ Concurrent users?
   ├─ <5 users → WAL mode + retry logic
   ├─ 5-10 users → WAL mode + retry logic + monitor
   └─ >10 users → Migrate to PostgreSQL
```

---

## Quick Reference

| Symptom | Quick Fix | Time | Prevention |
|---------|-----------|------|------------|
| Single lock error | Restart service | 1 min | Add retry logic |
| Recurring locks | Enable WAL mode | 5 min | Monitor frequency |
| Frequent locks | Migrate to PostgreSQL | 2 hours | Rate limit API |
| Slow queries | Increase timeout | 10 min | Optimize queries |

---

## Emergency Contacts

- **Database issues:** ymeirovich@gmail.com
- **AWS Support:** Premium support ticket
- **Google Cloud:** N/A (SQLite is local)
```

---

## 6. Testing & Verification

### 6.1 Test All Enhancements

**File:** `scripts/test-enhancements.sh`

```bash
#!/bin/bash

# Test all security and reliability enhancements
# Run after deployment to verify everything works

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

BASE_URL="http://localhost"
API_USER="demo_user"
API_PASS="AllCloud2024!"

test_passed=0
test_failed=0

log_test() {
    echo -e "\n${YELLOW}TEST:${NC} $1"
}

log_pass() {
    echo -e "${GREEN}✅ PASS:${NC} $1"
    ((test_passed++))
}

log_fail() {
    echo -e "${RED}❌ FAIL:${NC} $1"
    ((test_failed++))
}

# ============================================================================
# Test 1: Rate Limiting
# ============================================================================

log_test "Rate Limiting - API Generation Endpoint"

# Make 15 rapid requests (limit is 10/min)
for i in {1..15}; do
    response=$(curl -s -o /dev/null -w "%{http_code}" \
        -u "${API_USER}:${API_PASS}" \
        -X POST "${BASE_URL}/api/generate" \
        -H "Content-Type: application/json" \
        -d '{"topic":"Test","slides":3}')

    if [ $i -le 13 ]; then
        # First 13 should succeed (10 + burst of 3)
        if [ "$response" = "200" ] || [ "$response" = "202" ]; then
            continue
        else
            log_fail "Request $i should succeed but got $response"
            break
        fi
    else
        # 14th and 15th should be rate limited
        if [ "$response" = "429" ]; then
            log_pass "Rate limiting working - got 429 on request $i"
            break
        fi
    fi
done

# ============================================================================
# Test 2: SSL Certificate
# ============================================================================

log_test "SSL Certificate"

if curl -s -I https://presgen.net | grep -q "HTTP/2 200"; then
    log_pass "HTTPS enabled and working"
else
    log_fail "HTTPS not working or certificate invalid"
fi

# ============================================================================
# Test 3: Backup System
# ============================================================================

log_test "Backup System"

# Test backup script exists and is executable
if [ -x "/home/ubuntu/presgen/scripts/backup-with-verification.sh" ]; then
    log_pass "Backup script is executable"
else
    log_fail "Backup script not found or not executable"
fi

# Check S3 bucket exists
if aws s3 ls s3://presgen-backups-788159322332 >/dev/null 2>&1; then
    log_pass "S3 backup bucket exists"
else
    log_fail "S3 backup bucket not found"
fi

# Check cron job configured
if sudo crontab -u ubuntu -l | grep -q "backup-with-verification"; then
    log_pass "Backup cron job configured"
else
    log_fail "Backup cron job not configured"
fi

# ============================================================================
# Test 4: Google API Retry Logic
# ============================================================================

log_test "Google API Retry Logic"

# Check if retry module exists
if docker exec presgen-core python3 -c "from src.agent.google_api_retry import with_retry" 2>/dev/null; then
    log_pass "Google API retry module loaded successfully"
else
    log_fail "Google API retry module not found"
fi

# ============================================================================
# Test 5: Application Rate Limiting (slowapi)
# ============================================================================

log_test "Application-Level Rate Limiting"

# Check if slowapi is installed
if docker exec presgen-assess python3 -c "import slowapi" 2>/dev/null; then
    log_pass "slowapi installed in presgen-assess"
else
    log_fail "slowapi not installed in presgen-assess"
fi

# ============================================================================
# Test 6: Database WAL Mode
# ============================================================================

log_test "Database WAL Mode"

wal_mode=$(docker exec presgen-assess sqlite3 /app/data/presgen_assess.db "PRAGMA journal_mode;" 2>/dev/null || echo "error")

if [ "$wal_mode" = "wal" ]; then
    log_pass "Database using WAL mode (better concurrency)"
else
    log_fail "Database not using WAL mode (got: $wal_mode)"
fi

# ============================================================================
# Test 7: SNS Alerts Configuration
# ============================================================================

log_test "SNS Alert Topic"

topic_arn="arn:aws:sns:us-east-1:788159322332:presgen-alerts"

if aws sns get-topic-attributes --topic-arn "$topic_arn" >/dev/null 2>&1; then
    log_pass "SNS alert topic exists"

    # Check subscription
    if aws sns list-subscriptions-by-topic --topic-arn "$topic_arn" | grep -q "ymeirovich@gmail.com"; then
        log_pass "Email subscription configured"
    else
        log_fail "Email subscription not found"
    fi
else
    log_fail "SNS alert topic not found"
fi

# ============================================================================
# Test 8: Health Checks
# ============================================================================

log_test "Service Health Checks"

services=("presgen-ui:3000" "presgen-assess:8000" "presgen-core:8080")

for service in "${services[@]}"; do
    name=$(echo $service | cut -d: -f1)
    port=$(echo $service | cut -d: -f2)

    if curl -s "http://localhost:${port}/health" | grep -q "healthy\|ok"; then
        log_pass "$name health check passing"
    else
        log_fail "$name health check failing"
    fi
done

# ============================================================================
# Test 9: Security Headers
# ============================================================================

log_test "Security Headers"

headers=$(curl -s -I "${BASE_URL}" -u "${API_USER}:${API_PASS}")

if echo "$headers" | grep -q "X-Content-Type-Options: nosniff"; then
    log_pass "Security headers present"
else
    log_fail "Security headers missing"
fi

# ============================================================================
# Test 10: Quota Monitoring Script
# ============================================================================

log_test "Quota Monitoring Script"

if [ -x "/home/ubuntu/presgen/scripts/monitor-quotas.sh" ]; then
    log_pass "Quota monitoring script exists"
else
    log_fail "Quota monitoring script not found"
fi

# ============================================================================
# Summary
# ============================================================================

echo ""
echo "============================================"
echo "TEST SUMMARY"
echo "============================================"
echo -e "${GREEN}Passed: $test_passed${NC}"
echo -e "${RED}Failed: $test_failed${NC}"
echo "Total:  $((test_passed + test_failed))"
echo ""

if [ $test_failed -eq 0 ]; then
    echo -e "${GREEN}✅ ALL TESTS PASSED!${NC}"
    exit 0
else
    echo -e "${RED}⚠️  SOME TESTS FAILED${NC}"
    echo "Review failures above and fix before deploying"
    exit 1
fi
```

---

## Summary

This implementation guide provides:

1. ✅ **Nginx rate limiting** - 10 req/min for generation, 60 req/min for API, 120 req/min for UI
2. ✅ **Application-level rate limiting** - slowapi with Redis backend
3. ✅ **Free SSL/TLS** - Let's Encrypt with auto-renewal for presgen.net
4. ✅ **Comprehensive backup system** - Verified backups with S3, checksums, and monthly restore tests
5. ✅ **Google API quota management** - Exponential backoff retry, monitoring, quota increase requests
6. ✅ **Troubleshooting runbooks** - Step-by-step guides for common issues
7. ✅ **Testing framework** - Automated tests to verify all enhancements

**Next Steps:**

1. Review each section
2. Choose which enhancements to implement
3. Follow deployment steps in order
4. Run test script to verify
5. Monitor logs for 24 hours after deployment

**Estimated Implementation Time:**
- Rate limiting: 1 hour
- SSL certificate: 30 minutes
- Backup system: 2 hours
- API retry logic: 1 hour
- Troubleshooting docs: 30 minutes (already done)
- Testing: 30 minutes

**Total: ~5.5 hours** for complete implementation
