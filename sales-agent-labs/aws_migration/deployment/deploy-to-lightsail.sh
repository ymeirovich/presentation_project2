#!/bin/bash
# Complete Deployment Script for PresGen on AWS Lightsail
# Usage: ./deploy-to-lightsail.sh [instance-name] [instance-size]
#
# Example:
#   ./deploy-to-lightsail.sh presgen-demo medium_2_0
#
# Instance sizes:
#   - nano_2_0: 512MB, $3.50/month
#   - micro_2_0: 1GB, $5/month
#   - small_2_0: 2GB, $10/month (RECOMMENDED)
#   - medium_2_0: 4GB, $20/month
#
# Prerequisites:
#   - AWS CLI configured
#   - Environment variables set in .env file
#   - Docker installed locally (for building images)

set -e  # Exit on error
set -u  # Exit on undefined variable

# ===== Configuration =====
INSTANCE_NAME="${1:-presgen-demo}"
BUNDLE_ID="${2:-small_2_0}"  # 2GB RAM, $10/month
BLUEPRINT_ID="ubuntu_22_04"
REGION="us-east-1"
AZ="${REGION}a"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ===== Functions =====
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI not installed. Install from: https://aws.amazon.com/cli/"
        exit 1
    fi

    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured. Run: aws configure"
        exit 1
    fi

    # Check .env file
    if [ ! -f .env ]; then
        log_error ".env file not found. Copy .env.template to .env and configure."
        exit 1
    fi

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker not installed. Install from: https://www.docker.com/get-started"
        exit 1
    fi

    log_info "Prerequisites OK"
}

create_s3_bucket() {
    log_info "Creating S3 bucket..."

    BUCKET_NAME="presgen-demo-files-${TIMESTAMP}"

    # Create bucket
    aws s3 mb s3://${BUCKET_NAME} --region ${REGION}

    # Enable versioning
    aws s3api put-bucket-versioning \
        --bucket ${BUCKET_NAME} \
        --versioning-configuration Status=Enabled

    # Set lifecycle policy
    cat > /tmp/lifecycle.json <<EOF
{
  "Rules": [
    {
      "Id": "DeleteOldUploads",
      "Status": "Enabled",
      "Prefix": "uploads/",
      "Expiration": {"Days": 90}
    },
    {
      "Id": "DeleteOldTemp",
      "Status": "Enabled",
      "Prefix": "temp/",
      "Expiration": {"Days": 7}
    }
  ]
}
EOF

    aws s3api put-bucket-lifecycle-configuration \
        --bucket ${BUCKET_NAME} \
        --lifecycle-configuration file:///tmp/lifecycle.json

    # Enable CORS
    cat > /tmp/cors.json <<EOF
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
        --cors-configuration file:///tmp/cors.json

    log_info "S3 bucket created: $BUCKET_NAME"
    echo "S3_BUCKET=$BUCKET_NAME" >> aws-resources.env
}

create_lightsail_instance() {
    log_info "Creating Lightsail instance: $INSTANCE_NAME..."

    # Create startup script
    cat > /tmp/startup-script.sh <<'STARTUP'
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
DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep -Po '"tag_name": "\K.*?(?=")')
curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" \
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
    apache2-utils \
    jq \
    netcat

# Create directories
mkdir -p /home/ubuntu/presgen/{data,logs,secrets,nginx,uploads,exports,output}
chown -R ubuntu:ubuntu /home/ubuntu/presgen

# Create nginx auth directory
mkdir -p /etc/nginx/auth
chown -R ubuntu:ubuntu /etc/nginx/auth

# Enable swap (1GB for 2GB instance)
fallocate -l 1G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# Increase file watchers (for Next.js)
echo "fs.inotify.max_user_watches=524288" >> /etc/sysctl.conf
sysctl -p

echo "Startup script completed"
STARTUP

    # Create instance
    aws lightsail create-instances \
        --instance-names ${INSTANCE_NAME} \
        --availability-zone ${AZ} \
        --blueprint-id ${BLUEPRINT_ID} \
        --bundle-id ${BUNDLE_ID} \
        --user-data file:///tmp/startup-script.sh \
        --tags key=Project,value=PresGen key=Environment,value=Demo

    log_info "Waiting for instance to be running..."
    aws lightsail wait instance-running --instance-name ${INSTANCE_NAME}

    # Allocate and attach static IP
    log_info "Allocating static IP..."
    aws lightsail allocate-static-ip --static-ip-name ${INSTANCE_NAME}-ip
    aws lightsail attach-static-ip --static-ip-name ${INSTANCE_NAME}-ip --instance-name ${INSTANCE_NAME}

    # Get static IP
    STATIC_IP=$(aws lightsail get-static-ip --static-ip-name ${INSTANCE_NAME}-ip --query 'staticIp.ipAddress' --output text)

    log_info "Instance created with static IP: $STATIC_IP"

    # Open ports
    log_info "Configuring firewall..."
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

    log_info "Instance ready. Waiting 2 minutes for startup script to complete..."
    sleep 120
}

download_ssh_key() {
    log_info "Downloading SSH key..."

    aws lightsail download-default-key-pair \
        --query 'privateKeyBase64' \
        --output text | base64 -d > lightsail-key.pem

    chmod 600 lightsail-key.pem

    log_info "SSH key saved to: lightsail-key.pem"
}

upload_application() {
    source aws-resources.env
    log_info "Uploading application to $STATIC_IP..."

    # Create deployment package
    log_info "Creating deployment package..."
    tar czf /tmp/presgen-deploy.tar.gz \
        --exclude='node_modules' \
        --exclude='.git' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='.next' \
        --exclude='data' \
        --exclude='output' \
        --exclude='logs' \
        .

    # Upload package
    scp -i lightsail-key.pem -o StrictHostKeyChecking=no \
        /tmp/presgen-deploy.tar.gz ubuntu@${STATIC_IP}:/home/ubuntu/presgen/

    # Extract on server
    ssh -i lightsail-key.pem ubuntu@${STATIC_IP} << 'ENDSSH'
        cd /home/ubuntu/presgen
        tar xzf presgen-deploy.tar.gz
        rm presgen-deploy.tar.gz
        echo "Application uploaded and extracted"
ENDSSH

    log_info "Application uploaded successfully"
}

configure_secrets() {
    source aws-resources.env
    log_info "Configuring secrets..."

    # Load environment variables
    source .env

    # Create secrets file on server
    ssh -i lightsail-key.pem ubuntu@${STATIC_IP} << ENDSSH
        # Create .env file
        cat > /home/ubuntu/presgen/.env <<'EOF'
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Ports
PRESGEN_CORE_PORT=8080
PRESGEN_ASSESS_PORT=8000
PRESGEN_UI_PORT=3000

# Service URLs
PRESGEN_CORE_URL=http://presgen-core:8080
PRESGEN_ASSESS_URL=http://presgen-assess:8000
NEXT_PUBLIC_PRESGEN_ASSESS_URL=/api
NEXT_PUBLIC_PRESGEN_CORE_URL=/core

# Database
DATABASE_URL=sqlite+aiosqlite:////app/data/presgen_assess.db
REDIS_URL=redis://redis:6379/0

# AWS
AWS_REGION=${AWS_REGION}
S3_BUCKET=${S3_BUCKET}
STORAGE_PROVIDER=s3

# API Keys
OPENAI_API_KEY=${OPENAI_API_KEY}

# Features
PRESGEN_USE_MOCK=false
USE_AI_IMAGES=true
GPU_ENABLED=false
EOF

        chmod 600 /home/ubuntu/presgen/.env
ENDSSH

    # Upload Google credentials
    if [ -f "secrets/google-creds.json" ]; then
        scp -i lightsail-key.pem secrets/google-creds.json \
            ubuntu@${STATIC_IP}:/home/ubuntu/presgen/secrets/
    fi

    if [ -f "secrets/google-oauth-token.json" ]; then
        scp -i lightsail-key.pem secrets/google-oauth-token.json \
            ubuntu@${STATIC_IP}:/home/ubuntu/presgen/secrets/
    fi

    log_info "Secrets configured"
}

setup_basic_auth() {
    source aws-resources.env
    log_info "Setting up HTTP Basic Authentication..."

    ssh -i lightsail-key.pem ubuntu@${STATIC_IP} << 'ENDSSH'
        # Install htpasswd
        sudo apt-get install -y apache2-utils

        # Create users
        echo 'AllCloud2024!' | sudo htpasswd -ci /etc/nginx/auth/.htpasswd demo_user
        echo 'CTODemo2024!' | sudo htpasswd -i /etc/nginx/auth/.htpasswd cto_user
        echo 'YosiDemo2024!' | sudo htpasswd -i /etc/nginx/auth/.htpasswd yosi_user

        sudo chmod 644 /etc/nginx/auth/.htpasswd
        sudo chown root:root /etc/nginx/auth/.htpasswd

        echo "Basic authentication configured"
ENDSSH

    log_info "Basic authentication configured"
    log_info "Credentials:"
    log_info "  demo_user / AllCloud2024!"
    log_info "  cto_user / CTODemo2024!"
    log_info "  yosi_user / YosiDemo2024!"
}

deploy_application() {
    source aws-resources.env
    log_info "Deploying application..."

    ssh -i lightsail-key.pem ubuntu@${STATIC_IP} << 'ENDSSH'
        cd /home/ubuntu/presgen

        # Load environment
        source .env

        # Build and start services
        docker-compose build --no-cache
        docker-compose up -d

        # Wait for services
        echo "Waiting for services to start..."
        sleep 60

        # Check status
        docker-compose ps

        echo "Deployment complete"
ENDSSH

    log_info "Application deployed"
}

verify_deployment() {
    source aws-resources.env
    log_info "Verifying deployment..."

    # Test health endpoint
    HEALTH=$(curl -s http://${STATIC_IP}/health || echo "failed")
    if echo "$HEALTH" | grep -q "healthy"; then
        log_info "Health check: PASSED"
    else
        log_error "Health check: FAILED"
    fi

    # Test with authentication
    AUTH_RESPONSE=$(curl -s -u demo_user:AllCloud2024! -o /dev/null -w "%{http_code}" http://${STATIC_IP}/)
    if [ "$AUTH_RESPONSE" = "200" ]; then
        log_info "Basic auth: WORKING"
    else
        log_error "Basic auth: FAILED (HTTP $AUTH_RESPONSE)"
    fi

    log_info ""
    log_info "====================================="
    log_info "DEPLOYMENT COMPLETE!"
    log_info "====================================="
    log_info ""
    log_info "Access URL: http://${STATIC_IP}"
    log_info "Credentials:"
    log_info "  demo_user / AllCloud2024!"
    log_info "  cto_user / CTODemo2024!"
    log_info "  yosi_user / YosiDemo2024!"
    log_info ""
    log_info "SSH Access:"
    log_info "  ssh -i lightsail-key.pem ubuntu@${STATIC_IP}"
    log_info ""
    log_info "View Logs:"
    log_info "  docker-compose logs -f"
    log_info ""
    log_info "Resource Info:"
    cat aws-resources.env
    log_info ""
}

# ===== Main Execution =====
main() {
    log_info "Starting PresGen deployment to AWS Lightsail..."
    log_info "Instance: $INSTANCE_NAME"
    log_info "Size: $BUNDLE_ID"
    log_info "Region: $REGION"
    log_info ""

    check_prerequisites
    create_s3_bucket
    create_lightsail_instance
    download_ssh_key
    upload_application
    configure_secrets
    setup_basic_auth
    deploy_application
    verify_deployment

    log_info "Deployment script completed successfully!"
}

# Run main function
main
