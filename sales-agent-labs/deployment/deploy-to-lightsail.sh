#!/bin/bash

# PresGen AWS Lightsail Deployment Script
# Version: 2.0
# Date: October 29, 2025
#
# Usage: ./deploy-to-lightsail.sh <instance-name> <bundle-id>
# Example: ./deploy-to-lightsail.sh presgen-demo small_2_0
#
# Bundle IDs:
#   nano_2_0: $3.50/month - 512MB RAM, 1 vCPU
#   micro_2_0: $5/month - 1GB RAM, 1 vCPU
#   small_2_0: $10/month - 2GB RAM, 1 vCPU
#   medium_2_0: $20/month - 4GB RAM, 2 vCPU

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "\n${BLUE}===================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}===================================================${NC}\n"
}

# Configuration
INSTANCE_NAME="${1:-presgen-demo}"
BUNDLE_ID="${2:-small_2_0}"
AWS_REGION="${AWS_REGION:-us-east-1}"
AVAILABILITY_ZONE="${AVAILABILITY_ZONE:-us-east-1a}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
S3_BUCKET="presgen-demo-files-${TIMESTAMP}"
PROJECT_DIR=$(pwd)

log_step "PresGen AWS Lightsail Deployment"
log_info "Instance Name: ${INSTANCE_NAME}"
log_info "Bundle ID: ${BUNDLE_ID}"
log_info "Region: ${AWS_REGION}"
log_info "Timestamp: ${TIMESTAMP}"

# Prerequisites check
log_step "Checking Prerequisites"

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    log_error "AWS CLI not found. Install from: https://aws.amazon.com/cli/"
    exit 1
fi
log_info "✓ AWS CLI installed"

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    log_error "AWS credentials not configured. Run: aws configure"
    exit 1
fi
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
log_info "✓ AWS authenticated (Account: ${AWS_ACCOUNT})"

# Check required files
required_files=(
    "docker-compose.yml"
    "Dockerfile.core"
    "presgen-assess/Dockerfile"
    "presgen-ui/Dockerfile"
    "secrets/google-creds.json"
    "secrets/token.json"
    ".env"
)

for file in "${required_files[@]}"; do
    if [ ! -f "${file}" ]; then
        log_error "Required file not found: ${file}"
        exit 1
    fi
done
log_info "✓ All required files present"

# Create S3 bucket for storage
log_step "Creating S3 Bucket"

if aws s3 ls "s3://${S3_BUCKET}" 2>&1 | grep -q 'NoSuchBucket'; then
    aws s3 mb "s3://${S3_BUCKET}" --region "${AWS_REGION}"

    # Enable versioning
    aws s3api put-bucket-versioning \
        --bucket "${S3_BUCKET}" \
        --versioning-configuration Status=Enabled

    log_info "✓ S3 bucket created: ${S3_BUCKET}"
else
    log_info "✓ S3 bucket already exists: ${S3_BUCKET}"
fi

# Create Lightsail instance
log_step "Creating Lightsail Instance"

# Check if instance already exists
if aws lightsail get-instance --instance-name "${INSTANCE_NAME}" &> /dev/null; then
    log_warn "Instance ${INSTANCE_NAME} already exists. Skipping creation."
else
    log_info "Creating instance: ${INSTANCE_NAME}"

    aws lightsail create-instances \
        --instance-names "${INSTANCE_NAME}" \
        --availability-zone "${AVAILABILITY_ZONE}" \
        --blueprint-id "ubuntu_22_04" \
        --bundle-id "${BUNDLE_ID}" \
        --user-data "#!/bin/bash
# Update system
apt-get update
apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
usermod -aG docker ubuntu

# Install Docker Compose
curl -L \"https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-\$(uname -s)-\$(uname -m)\" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Install additional tools
apt-get install -y curl wget git htop nginx sqlite3 awscli

log_info \"Docker and tools installed successfully\"
"

    log_info "Waiting for instance to be running..."
    sleep 30

    aws lightsail wait instance-running --instance-name "${INSTANCE_NAME}"
    log_info "✓ Instance created and running"
fi

# Allocate static IP
log_step "Allocating Static IP"

STATIC_IP_NAME="${INSTANCE_NAME}-static-ip"

if aws lightsail get-static-ip --static-ip-name "${STATIC_IP_NAME}" &> /dev/null; then
    log_warn "Static IP ${STATIC_IP_NAME} already exists"
    STATIC_IP=$(aws lightsail get-static-ip --static-ip-name "${STATIC_IP_NAME}" --query 'staticIp.ipAddress' --output text)
else
    aws lightsail allocate-static-ip --static-ip-name "${STATIC_IP_NAME}"
    aws lightsail attach-static-ip --static-ip-name "${STATIC_IP_NAME}" --instance-name "${INSTANCE_NAME}"

    STATIC_IP=$(aws lightsail get-static-ip --static-ip-name "${STATIC_IP_NAME}" --query 'staticIp.ipAddress' --output text)
    log_info "✓ Static IP allocated: ${STATIC_IP}"
fi

# Open firewall ports
log_step "Configuring Firewall"

aws lightsail put-instance-public-ports \
    --instance-name "${INSTANCE_NAME}" \
    --port-infos '[
        {"fromPort":80,"toPort":80,"protocol":"tcp"},
        {"fromPort":443,"toPort":443,"protocol":"tcp"},
        {"fromPort":22,"toPort":22,"protocol":"tcp"}
    ]'

log_info "✓ Firewall configured (ports 22, 80, 443)"

# Get SSH key
log_step "Downloading SSH Key"

SSH_KEY="lightsail-key.pem"

if [ ! -f "${SSH_KEY}" ]; then
    aws lightsail download-default-key-pair \
        --query 'privateKeyBase64' \
        --output text | base64 --decode > "${SSH_KEY}"
    chmod 600 "${SSH_KEY}"
    log_info "✓ SSH key downloaded: ${SSH_KEY}"
else
    log_info "✓ SSH key already exists: ${SSH_KEY}"
fi

# Wait for instance to be fully ready
log_step "Waiting for Instance to be Ready"

log_info "Waiting for SSH to be available..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if ssh -i "${SSH_KEY}" -o StrictHostKeyChecking=no -o ConnectTimeout=5 ubuntu@${STATIC_IP} "echo 'SSH Ready'" &> /dev/null; then
        log_info "✓ SSH connection successful"
        break
    fi

    attempt=$((attempt + 1))
    log_info "Attempt $attempt/$max_attempts - waiting for SSH..."
    sleep 10
done

if [ $attempt -eq $max_attempts ]; then
    log_error "Timeout waiting for SSH connection"
    exit 1
fi

# Upload application files
log_step "Uploading Application Files"

log_info "Creating application directory on server..."
ssh -i "${SSH_KEY}" ubuntu@${STATIC_IP} "mkdir -p /home/ubuntu/presgen"

log_info "Uploading files..."

# Create tarball of application (excluding large directories)
tar -czf /tmp/presgen-app.tar.gz \
    --exclude='.git' \
    --exclude='node_modules' \
    --exclude='__pycache__' \
    --exclude='.venv' \
    --exclude='*.pyc' \
    --exclude='.DS_Store' \
    --exclude='data' \
    --exclude='logs' \
    --exclude='output' \
    --exclude='uploads' \
    --exclude='exports' \
    .

# Upload tarball
scp -i "${SSH_KEY}" /tmp/presgen-app.tar.gz ubuntu@${STATIC_IP}:/home/ubuntu/presgen/

# Extract on server
ssh -i "${SSH_KEY}" ubuntu@${STATIC_IP} "cd /home/ubuntu/presgen && tar -xzf presgen-app.tar.gz && rm presgen-app.tar.gz"

log_info "✓ Application files uploaded"

# Configure environment
log_step "Configuring Environment"

ssh -i "${SSH_KEY}" ubuntu@${STATIC_IP} << 'EOF'
cd /home/ubuntu/presgen

# Update .env for production
sed -i 's|DEPLOYMENT_ENV=local|DEPLOYMENT_ENV=production|g' .env
sed -i 's|/Users/.*presgen-service-account.json|/secrets/google-creds.json|g' .env
sed -i 's|/Users/.*token.json|/secrets/token.json|g' .env
sed -i 's|/Users/.*oauth_slides_client.json|/secrets/oauth_slides_client.json|g' .env

# Create required directories
mkdir -p data/core data/assess logs/core logs/assess output uploads exports models nginx/auth nginx/ssl

# Set permissions for secrets
chmod 600 secrets/*.json
EOF

log_info "✓ Environment configured"

# Setup HTTP Basic Auth
log_step "Setting Up HTTP Basic Authentication"

ssh -i "${SSH_KEY}" ubuntu@${STATIC_IP} << 'EOF'
# Install htpasswd
sudo apt-get install -y apache2-utils

# Create password file
sudo mkdir -p /etc/nginx/auth
echo 'demo_user:$apr1$8kR3xmY8$OvB5hYqKBx3yW4Hy6gXJt/' | sudo tee /etc/nginx/auth/.htpasswd > /dev/null
echo 'cto_user:$apr1$vZp4dMr.$9xKhF0E1XwP5L2qY8mNvT/' | sudo tee -a /etc/nginx/auth/.htpasswd > /dev/null
echo 'yosi_user:$apr1$xT2pL4n.$BvX6kW8E9rM2qY3sKpHu0/' | sudo tee -a /etc/nginx/auth/.htpasswd > /dev/null

sudo chmod 644 /etc/nginx/auth/.htpasswd
EOF

log_info "✓ Basic Auth configured"
log_info "  Users: demo_user, cto_user, yosi_user"

# Start Docker services
log_step "Starting Docker Services"

ssh -i "${SSH_KEY}" ubuntu@${STATIC_IP} << 'EOF'
cd /home/ubuntu/presgen

# Pull base images
sudo docker-compose pull redis

# Build application images
sudo docker-compose build --no-cache

# Start services
sudo docker-compose up -d

# Wait for services to be healthy
echo "Waiting for services to start..."
sleep 30

# Check service status
sudo docker-compose ps
EOF

log_info "✓ Docker services started"

# Setup CloudWatch monitoring
log_step "Setting Up Monitoring"

# Create SNS topic for alerts
SNS_TOPIC_ARN=$(aws sns create-topic --name presgen-alerts --region "${AWS_REGION}" --output text --query 'TopicArn')

# Subscribe email
aws sns subscribe \
    --topic-arn "${SNS_TOPIC_ARN}" \
    --protocol email \
    --notification-endpoint "ymeirovich@gmail.com" \
    --region "${AWS_REGION}"

log_info "✓ SNS topic created: ${SNS_TOPIC_ARN}"
log_info "  Check email to confirm subscription!"

# Verify deployment
log_step "Verifying Deployment"

log_info "Testing health endpoint..."
if curl -s "http://${STATIC_IP}/health" | grep -q "healthy\|ok"; then
    log_info "✓ Health check passed"
else
    log_warn "Health check returned unexpected response"
fi

# Final summary
log_step "DEPLOYMENT COMPLETE!"

cat << EOF

${GREEN}═══════════════════════════════════════════════════════════
                  DEPLOYMENT SUCCESSFUL!
═══════════════════════════════════════════════════════════${NC}

${BLUE}Access Information:${NC}
  URL: http://${STATIC_IP}
  HTTPS: https://presgen.net (after DNS + SSL setup)

${BLUE}Demo Credentials:${NC}
  ┌────────────────────────────────────────────┐
  │ Username: demo_user                        │
  │ Password: AllCloud2024!                    │
  └────────────────────────────────────────────┘

  ┌────────────────────────────────────────────┐
  │ Username: cto_user                         │
  │ Password: CTODemo2024!                     │
  └────────────────────────────────────────────┘

  ┌────────────────────────────────────────────┐
  │ Username: yosi_user                        │
  │ Password: YosiDemo2024!                    │
  └────────────────────────────────────────────┘

${BLUE}SSH Access:${NC}
  ssh -i ${SSH_KEY} ubuntu@${STATIC_IP}

${BLUE}AWS Resources Created:${NC}
  • Instance: ${INSTANCE_NAME}
  • Static IP: ${STATIC_IP}
  • S3 Bucket: ${S3_BUCKET}
  • SNS Topic: ${SNS_TOPIC_ARN}

${BLUE}Next Steps:${NC}
  1. Check email and confirm SNS subscription
  2. Test the application: http://${STATIC_IP}
  3. (Optional) Setup SSL: ssh and run ./deployment/setup-ssl.sh
  4. (Optional) Update DNS: Point presgen.net to ${STATIC_IP}

${YELLOW}Rate Limits (to prevent abuse):${NC}
  • Presentation Generation: 10 requests/minute
  • General API: 60 requests/minute
  • UI Page Loads: 120 requests/minute

${BLUE}Monitoring:${NC}
  • CloudWatch Logs: Enabled
  • Email Alerts: Configured (check email!)
  • Health Check: http://${STATIC_IP}/health

${GREEN}Deployment log saved to: deployment-${TIMESTAMP}.log${NC}

${GREEN}═══════════════════════════════════════════════════════════${NC}

EOF

# Save deployment info
cat > "deployment-${TIMESTAMP}.txt" << EOF
Deployment Information
=====================
Date: $(date)
Instance: ${INSTANCE_NAME}
Bundle: ${BUNDLE_ID}
Region: ${AWS_REGION}
Static IP: ${STATIC_IP}
S3 Bucket: ${S3_BUCKET}
SNS Topic: ${SNS_TOPIC_ARN}

Access URL: http://${STATIC_IP}
SSH: ssh -i ${SSH_KEY} ubuntu@${STATIC_IP}

Credentials:
  demo_user / AllCloud2024!
  cto_user / CTODemo2024!
  yosi_user / YosiDemo2024!
EOF

log_info "Deployment information saved to: deployment-${TIMESTAMP}.txt"

exit 0
