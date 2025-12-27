#!/bin/bash
# Restart Docker services on Lightsail instance after restart
# This script should be run after start-lightsail.sh completes

set -e

echo "🔄 Restarting Docker services on Lightsail instance..."

# Get IP
STATIC_IP=$(aws lightsail get-static-ip \
  --static-ip-name presgen-prod-ip \
  --query 'staticIp.ipAddress' \
  --output text)

echo "🌐 Instance IP: $STATIC_IP"

# Get SSH key
echo "🔑 Downloading SSH key..."
aws lightsail download-default-key-pair \
  --region us-east-1 \
  --query 'privateKeyBase64' \
  --output text > /tmp/lightsail-key-b64.txt

# Decode key properly
python3 -c "import base64; key = open('/tmp/lightsail-key-b64.txt').read().strip(); open('/tmp/lightsail-ssh-key.pem', 'wb').write(base64.b64decode(key + '=' * (4 - len(key) % 4)))" 2>/dev/null || \
  python3 -c "import base64; key = open('/tmp/lightsail-key-b64.txt').read().strip(); open('/tmp/lightsail-ssh-key.pem', 'wb').write(base64.b64decode(key))"

chmod 600 /tmp/lightsail-ssh-key.pem

echo "🔐 Testing SSH connectivity..."
if ! ssh -i /tmp/lightsail-ssh-key.pem -o StrictHostKeyChecking=no -o ConnectTimeout=10 ubuntu@$STATIC_IP "echo 'SSH OK'" 2>/dev/null; then
  echo "❌ SSH connection failed. Trying alternative method..."

  # Try using AWS Systems Manager Session Manager if available
  echo "📋 Instructions for manual restart:"
  echo "1. Go to: https://lightsail.aws.amazon.com/ls/webapp/us-east-1/instances/presgen-prod/connect"
  echo "2. Click 'Connect using SSH'"
  echo "3. Run these commands:"
  echo ""
  echo "   cd /home/ubuntu/presgen/sales-agent-labs"
  echo "   docker-compose down"
  echo "   docker-compose up -d"
  echo "   docker-compose ps"
  echo ""
  echo "⚠️  Or use the AWS Console to run commands via browser-based SSH"
  exit 1
fi

echo "🐳 Checking Docker status..."
ssh -i /tmp/lightsail-ssh-key.pem -o StrictHostKeyChecking=no ubuntu@$STATIC_IP << 'ENDSSH'
  cd /home/ubuntu/presgen/sales-agent-labs

  echo "Current Docker status:"
  docker ps -a

  echo ""
  echo "Restarting services..."
  docker-compose down
  sleep 5
  docker-compose up -d

  echo ""
  echo "Waiting for services to start (60 seconds)..."
  sleep 60

  echo ""
  echo "Final status:"
  docker-compose ps

  echo ""
  echo "Health checks:"
  docker-compose logs --tail=20 presgen-nginx
ENDSSH

echo ""
echo "✅ Docker services restarted!"
echo ""
echo "🔗 Testing web service..."
sleep 10

# Test the service
if curl -s --connect-timeout 10 -o /dev/null -w "%{http_code}" http://$STATIC_IP/health | grep -q "200\|401"; then
  echo "✅ Web service is responding at: http://$STATIC_IP"
else
  echo "⚠️  Web service may still be starting. Check logs with:"
  echo "   ssh -i /tmp/lightsail-ssh-key.pem ubuntu@$STATIC_IP 'cd /home/ubuntu/presgen/sales-agent-labs && docker-compose logs -f'"
fi

echo ""
echo "🎉 Restart complete!"

# Cleanup
rm -f /tmp/lightsail-key-b64.txt /tmp/lightsail-ssh-key.pem
