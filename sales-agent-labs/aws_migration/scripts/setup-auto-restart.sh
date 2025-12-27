#!/bin/bash
# Setup automatic Docker service restart on Lightsail instance boot
# Run this once to enable auto-restart of Docker services

set -e

echo "🔧 Setting up automatic Docker service restart..."

# Get IP
STATIC_IP=$(aws lightsail get-static-ip \
  --static-ip-name presgen-prod-ip \
  --query 'staticIp.ipAddress' \
  --output text)

echo "🌐 Instance IP: $STATIC_IP"

# Download SSH key
echo "🔑 Downloading SSH key..."
aws lightsail download-default-key-pair \
  --region us-east-1 \
  --query 'privateKeyBase64' \
  --output text > /tmp/lightsail-key-b64.txt

# Decode key
python3 -c "import base64; key = open('/tmp/lightsail-key-b64.txt').read().strip(); open('/tmp/lightsail-ssh-key.pem', 'wb').write(base64.b64decode(key + '=' * (4 - len(key) % 4)))" 2>/dev/null || \
  python3 -c "import base64; key = open('/tmp/lightsail-key-b64.txt').read().strip(); open('/tmp/lightsail-ssh-key.pem', 'wb').write(base64.b64decode(key))"

chmod 600 /tmp/lightsail-ssh-key.pem

echo "🔐 Connecting to instance..."
if ! ssh -i /tmp/lightsail-ssh-key.pem -o StrictHostKeyChecking=no -o ConnectTimeout=10 ubuntu@$STATIC_IP "echo 'SSH OK'" 2>/dev/null; then
  echo "❌ SSH connection failed. Use manual setup:"
  echo ""
  echo "1. SSH into your instance:"
  echo "   https://lightsail.aws.amazon.com/ls/webapp/us-east-1/instances/presgen-prod/connect"
  echo ""
  echo "2. Run the following commands:"
  cat << 'MANUAL'

cat << 'EOF' | sudo tee /etc/systemd/system/presgen-docker.service
[Unit]
Description=PresGen Docker Compose Service
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/ubuntu/presgen/sales-agent-labs
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=300
User=ubuntu
Group=ubuntu
Environment="PATH=/usr/local/bin:/usr/bin:/bin"

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable presgen-docker.service
sudo systemctl start presgen-docker.service
sudo systemctl status presgen-docker.service

MANUAL
  rm -f /tmp/lightsail-key-b64.txt /tmp/lightsail-ssh-key.pem
  exit 1
fi

echo "⚙️  Installing systemd service..."
ssh -i /tmp/lightsail-ssh-key.pem -o StrictHostKeyChecking=no ubuntu@$STATIC_IP << 'ENDSSH'
  # Create systemd service file
  cat << 'EOF' | sudo tee /etc/systemd/system/presgen-docker.service
[Unit]
Description=PresGen Docker Compose Service
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/ubuntu/presgen/sales-agent-labs
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=300
User=ubuntu
Group=ubuntu
Environment="PATH=/usr/local/bin:/usr/bin:/bin"

[Install]
WantedBy=multi-user.target
EOF

  # Enable and start the service
  sudo systemctl daemon-reload
  sudo systemctl enable presgen-docker.service

  echo ""
  echo "Service installed and enabled!"
  echo ""
  echo "Testing service start..."
  sudo systemctl start presgen-docker.service
  sleep 10
  sudo systemctl status presgen-docker.service --no-pager

  echo ""
  echo "Docker containers:"
  cd /home/ubuntu/presgen/sales-agent-labs
  docker-compose ps
ENDSSH

echo ""
echo "✅ Auto-restart setup complete!"
echo ""
echo "🎯 What this does:"
echo "   - Docker services will automatically start when the instance boots"
echo "   - No need to manually restart services after stopping/starting the instance"
echo "   - Services start after Docker and network are ready"
echo ""
echo "🔍 To verify:"
echo "   sudo systemctl status presgen-docker.service"
echo ""
echo "🧪 To test:"
echo "   1. Stop your instance: ./aws_migration/scripts/stop-lightsail.sh"
echo "   2. Start it again: ./aws_migration/scripts/start-lightsail.sh"
echo "   3. Services should automatically start within 2-3 minutes"
echo ""

# Cleanup
rm -f /tmp/lightsail-key-b64.txt /tmp/lightsail-ssh-key.pem
