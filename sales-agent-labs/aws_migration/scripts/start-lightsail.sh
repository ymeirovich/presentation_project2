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

# Test SSH connectivity
echo "🔐 Testing SSH connectivity..."
ssh -i lightsail-key.pem -o ConnectTimeout=10 ubuntu@$STATIC_IP "echo '✅ SSH connection successful'"

echo "✅ Instance is ready for use!"
