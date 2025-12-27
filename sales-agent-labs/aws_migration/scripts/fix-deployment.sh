#!/bin/bash
# Fix missing files on Lightsail instance after restart
# This uploads the .env file and missing directories

set -e

echo "🔧 Fixing deployment files on Lightsail instance..."

# Get IP
STATIC_IP=$(aws lightsail get-static-ip \
  --static-ip-name presgen-prod-ip \
  --query 'staticIp.ipAddress' \
  --output text)

echo "🌐 Instance IP: $STATIC_IP"

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
  echo "❌ Error: Must be run from the project root directory"
  echo "   cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs"
  exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
  echo "❌ Error: .env file not found"
  exit 1
fi

echo ""
echo "📋 Using browser-based SSH method..."
echo ""
echo "Please follow these steps:"
echo ""
echo "1. Open this URL in your browser:"
echo "   https://lightsail.aws.amazon.com/ls/webapp/us-east-1/instances/presgen-prod/connect"
echo ""
echo "2. Click 'Connect using SSH'"
echo ""
echo "3. Run these commands in the browser terminal:"
echo ""

cat << 'COMMANDS'
# Navigate to presgen directory
cd /home/ubuntu/presgen

# Check what's missing
ls -la
echo "---"
ls -la presgen-avatar 2>&1 || echo "presgen-avatar is missing"
ls -la .env 2>&1 || echo ".env is missing"

COMMANDS

echo ""
echo "4. If files are missing, we'll upload them using a different method."
echo ""
read -p "Press Enter when you've checked, or Ctrl+C to exit..."

echo ""
echo "🔄 Method 1: Try automated upload via SCP..."
echo ""

# Download SSH key
echo "🔑 Getting SSH key..."
aws lightsail get-instance-access-details \
  --instance-name presgen-prod \
  --query 'accessDetails.privateKey' \
  --output text > /tmp/presgen-ssh-key.pem 2>/dev/null || \
  aws lightsail download-default-key-pair \
    --region us-east-1 \
    --query 'privateKeyBase64' \
    --output text | python3 -c "import sys, base64; sys.stdout.buffer.write(base64.b64decode(sys.stdin.read().strip() + '==='))" > /tmp/presgen-ssh-key.pem 2>/dev/null

chmod 600 /tmp/presgen-ssh-key.pem

# Test SSH
if ssh -i /tmp/presgen-ssh-key.pem -o StrictHostKeyChecking=no -o ConnectTimeout=10 ubuntu@$STATIC_IP "echo 'SSH works'" 2>/dev/null; then
  echo "✅ SSH connection successful!"
  echo ""

  # Upload .env file
  echo "📤 Uploading .env file..."
  scp -i /tmp/presgen-ssh-key.pem -o StrictHostKeyChecking=no .env ubuntu@$STATIC_IP:/home/ubuntu/presgen/.env

  # Upload presgen-avatar directory
  if [ -d "presgen-avatar" ]; then
    echo "📤 Uploading presgen-avatar directory..."
    scp -i /tmp/presgen-ssh-key.pem -o StrictHostKeyChecking=no -r presgen-avatar ubuntu@$STATIC_IP:/home/ubuntu/presgen/
  fi

  # Upload presgen-ui directory if missing
  if [ -d "presgen-ui" ]; then
    echo "📤 Checking presgen-ui directory..."
    ssh -i /tmp/presgen-ssh-key.pem -o StrictHostKeyChecking=no ubuntu@$STATIC_IP "[ -d /home/ubuntu/presgen/presgen-ui ] || echo 'missing'" | grep -q "missing" && \
      scp -i /tmp/presgen-ssh-key.pem -o StrictHostKeyChecking=no -r presgen-ui ubuntu@$STATIC_IP:/home/ubuntu/presgen/
  fi

  # Upload presgen-assess directory if missing
  if [ -d "presgen-assess" ]; then
    echo "📤 Checking presgen-assess directory..."
    ssh -i /tmp/presgen-ssh-key.pem -o StrictHostKeyChecking=no ubuntu@$STATIC_IP "[ -d /home/ubuntu/presgen/presgen-assess ] || echo 'missing'" | grep -q "missing" && \
      scp -i /tmp/presgen-ssh-key.pem -o StrictHostKeyChecking=no -r presgen-assess ubuntu@$STATIC_IP:/home/ubuntu/presgen/
  fi

  echo ""
  echo "✅ Files uploaded successfully!"
  echo ""
  echo "🐳 Restarting Docker services..."

  ssh -i /tmp/presgen-ssh-key.pem -o StrictHostKeyChecking=no ubuntu@$STATIC_IP << 'ENDSSH'
    cd /home/ubuntu/presgen

    echo "Building and starting services..."
    docker-compose down 2>/dev/null || true
    docker-compose build --no-cache
    docker-compose up -d

    echo ""
    echo "Waiting for services to start (60 seconds)..."
    sleep 60

    echo ""
    echo "Service status:"
    docker-compose ps

    echo ""
    echo "Recent logs:"
    docker-compose logs --tail=20
ENDSSH

  echo ""
  echo "✅ Deployment fixed!"

  # Test service
  echo ""
  echo "🧪 Testing service..."
  sleep 5
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 http://$STATIC_IP/health || echo "000")
  if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "401" ]; then
    echo "✅ Web service is responding: http://$STATIC_IP"
  else
    echo "⚠️  Web service returned HTTP $HTTP_CODE"
  fi

  rm -f /tmp/presgen-ssh-key.pem
else
  echo "❌ SSH connection failed. Using manual upload method..."
  echo ""
  echo "🔄 Method 2: Manual upload via AWS Console"
  echo ""
  echo "Step 1: Create a temporary tar file..."

  # Create deployment package with all necessary files
  tar czf /tmp/presgen-missing-files.tar.gz \
    .env \
    presgen-avatar/ \
    docker-compose.yml \
    Dockerfile.core \
    presgen-ui/ \
    presgen-assess/ \
    nginx/ \
    2>/dev/null

  echo "✅ Created /tmp/presgen-missing-files.tar.gz"
  echo ""
  echo "Step 2: Upload using AWS Console:"
  echo "   1. Go to: https://lightsail.aws.amazon.com/ls/webapp/us-east-1/instances/presgen-prod/connect"
  echo "   2. Click 'Connect using SSH'"
  echo "   3. In another terminal on your Mac, run:"
  echo ""
  echo "      cat /tmp/presgen-missing-files.tar.gz | base64 > /tmp/presgen-files-b64.txt"
  echo ""
  echo "   4. Copy the contents of /tmp/presgen-files-b64.txt"
  echo "   5. In the browser SSH terminal, run:"
  echo ""
  cat << 'MANUAL_COMMANDS'
      cat << 'EOFDATA' | base64 -d > /tmp/presgen-files.tar.gz
      [PASTE THE BASE64 CONTENT HERE]
      EOFDATA

      cd /home/ubuntu/presgen
      tar xzf /tmp/presgen-files.tar.gz
      rm /tmp/presgen-files.tar.gz

      # Restart services
      docker-compose down
      docker-compose build --no-cache
      docker-compose up -d

      # Check status
      sleep 60
      docker-compose ps
MANUAL_COMMANDS

  echo ""
  echo "Or use this simpler approach:"
  echo ""
  echo "   1. SSH into the instance via browser"
  echo "   2. Create the .env file manually:"
  echo ""
  echo "      cd /home/ubuntu/presgen"
  echo "      cat > .env << 'ENVEOF'"
  cat .env
  echo "      ENVEOF"
  echo ""
  echo "   3. Check if presgen-avatar directory is missing, if so:"
  echo "      # The directory might already exist from previous deployment"
  echo "      # Just restart the services"
  echo ""
  echo "   4. Restart Docker services:"
  echo "      docker-compose down"
  echo "      docker-compose up -d"
  echo ""

  rm -f /tmp/presgen-ssh-key.pem
fi

echo ""
echo "🎉 Done!"
echo ""
echo "To verify, visit: http://$STATIC_IP"
