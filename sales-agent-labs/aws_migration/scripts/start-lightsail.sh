#!/bin/bash
set -e

echo "🚀 Starting Lightsail instance..."

# Start instance
aws lightsail start-instance --instance-name presgen-prod

echo "⏳ Waiting for instance to start (this takes ~2-3 minutes)..."
sleep 120

# Get IP
STATIC_IP=$(aws lightsail get-static-ip \
  --static-ip-name presgen-prod-ip \
  --query 'staticIp.ipAddress' \
  --output text)

echo "🌐 Instance IP: $STATIC_IP"

# Verify state
STATE=$(aws lightsail get-instance --instance-name presgen-prod | grep -o '"name": "running"' || echo "not running")
if [[ $STATE == *"running"* ]]; then
  echo "✅ Instance started successfully"
  echo "🔗 Access at: http://$STATIC_IP"
  echo "💰 Now incurring ~\$0.67/day"
else
  echo "⚠️  Instance may not be running yet, check status"
  exit 1
fi

# Test SSH connectivity and restart Docker services
echo "🔐 Testing SSH connectivity..."

# Download fresh SSH key
echo "Downloading SSH key..."
aws lightsail download-default-key-pair \
  --region us-east-1 \
  --query 'privateKeyBase64' \
  --output text > /tmp/lightsail-key-b64.txt

# Decode key (handle padding issues)
python3 -c "import base64; key = open('/tmp/lightsail-key-b64.txt').read().strip(); open('/tmp/lightsail-key-temp.pem', 'wb').write(base64.b64decode(key + '=' * (4 - len(key) % 4)))" 2>/dev/null || \
  python3 -c "import base64; key = open('/tmp/lightsail-key-b64.txt').read().strip(); open('/tmp/lightsail-key-temp.pem', 'wb').write(base64.b64decode(key))"

chmod 600 /tmp/lightsail-key-temp.pem

if ssh -i /tmp/lightsail-key-temp.pem -o StrictHostKeyChecking=no -o ConnectTimeout=10 ubuntu@$STATIC_IP "echo 'SSH connection successful'" 2>/dev/null; then
  echo "✅ SSH connection successful"

  echo "🐳 Restarting Docker services..."
  ssh -i /tmp/lightsail-key-temp.pem -o StrictHostKeyChecking=no ubuntu@$STATIC_IP << 'ENDSSH'
    cd /home/ubuntu/presgen/sales-agent-labs

    echo "Stopping existing containers..."
    docker-compose down 2>/dev/null || true

    echo "Starting services..."
    docker-compose up -d

    echo "Waiting for services to start..."
    sleep 60

    echo "Service status:"
    docker-compose ps
ENDSSH

  echo "✅ Docker services restarted"

  # Test web service
  echo "🔗 Testing web service..."
  sleep 10
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 http://$STATIC_IP/health || echo "000")
  if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "401" ]; then
    echo "✅ Web service is responding"
  else
    echo "⚠️  Web service returned HTTP $HTTP_CODE - may still be starting"
  fi

  rm -f /tmp/lightsail-key-temp.pem /tmp/lightsail-key-b64.txt
else
  echo "⚠️  SSH connection failed. Manual restart required:"
  echo "1. Go to: https://lightsail.aws.amazon.com/ls/webapp/us-east-1/instances/presgen-prod/connect"
  echo "2. Click 'Connect using SSH'"
  echo "3. Run: cd /home/ubuntu/presgen/sales-agent-labs && docker-compose down && docker-compose up -d"
  rm -f /tmp/lightsail-key-temp.pem /tmp/lightsail-key-b64.txt
  exit 1
fi

echo "✅ Instance is ready for use!"
