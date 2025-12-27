#!/bin/bash
# Restore Lightsail instance from snapshot
# This will restore to the last working state

set -e

SNAPSHOT_NAME="presgen-prod-snapshot-20251114-010213"
INSTANCE_NAME="presgen-prod"

echo "🔄 Restoring instance from snapshot..."
echo "Snapshot: $SNAPSHOT_NAME"
echo "Instance: $INSTANCE_NAME"
echo ""
echo "⚠️  WARNING: This will restore your instance to November 14th state"
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled"
    exit 1
fi

# Stop the current instance
echo "🛑 Stopping current instance..."
aws lightsail stop-instance --instance-name $INSTANCE_NAME

echo "⏳ Waiting for instance to stop..."
aws lightsail wait instance-stopped --instance-name $INSTANCE_NAME

# Create instance from snapshot
echo "📦 Creating new instance from snapshot..."
# Note: We need to delete and recreate, or create with a new name

# Get current instance details
BUNDLE_ID=$(aws lightsail get-instance --instance-name $INSTANCE_NAME --query 'instance.bundleId' --output text)
AZ=$(aws lightsail get-instance --instance-name $INSTANCE_NAME --query 'instance.location.availabilityZone' --output text)

echo "Current bundle: $BUNDLE_ID"
echo "Current AZ: $AZ"
echo ""

# Detach static IP
echo "🔌 Detaching static IP..."
aws lightsail detach-static-ip --static-ip-name presgen-prod-ip || true

# Delete current instance
echo "🗑️  Deleting current instance..."
aws lightsail delete-instance --instance-name $INSTANCE_NAME

echo "⏳ Waiting 60 seconds for deletion to complete..."
sleep 60

# Create new instance from snapshot
echo "✨ Creating instance from snapshot..."
aws lightsail create-instances-from-snapshot \
  --instance-names $INSTANCE_NAME \
  --instance-snapshot-name $SNAPSHOT_NAME \
  --availability-zone $AZ \
  --bundle-id $BUNDLE_ID

echo "⏳ Waiting for instance to start..."
aws lightsail wait instance-running --instance-name $INSTANCE_NAME

# Reattach static IP
echo "🔗 Reattaching static IP..."
aws lightsail attach-static-ip --static-ip-name presgen-prod-ip --instance-name $INSTANCE_NAME

# Get IP
STATIC_IP=$(aws lightsail get-static-ip \
  --static-ip-name presgen-prod-ip \
  --query 'staticIp.ipAddress' \
  --output text)

echo ""
echo "✅ Instance restored from snapshot!"
echo "🌐 IP Address: $STATIC_IP"
echo ""
echo "⏳ Waiting 2 minutes for instance to fully boot..."
sleep 120

echo ""
echo "🐳 Starting Docker services..."

# Download SSH key and start services
aws lightsail get-instance-access-details \
  --instance-name $INSTANCE_NAME \
  --query 'accessDetails.privateKey' \
  --output text > /tmp/lightsail-restore-key.pem

chmod 600 /tmp/lightsail-restore-key.pem

if ssh -i /tmp/lightsail-restore-key.pem -o StrictHostKeyChecking=no -o ConnectTimeout=10 ubuntu@$STATIC_IP "cd /home/ubuntu/presgen && docker-compose up -d" 2>/dev/null; then
  echo "✅ Docker services started"
  echo ""
  echo "⏳ Waiting 60 seconds for services to start..."
  sleep 60

  ssh -i /tmp/lightsail-restore-key.pem -o StrictHostKeyChecking=no ubuntu@$STATIC_IP "cd /home/ubuntu/presgen && docker-compose ps"

  rm -f /tmp/lightsail-restore-key.pem
else
  echo "⚠️  Could not SSH to restart Docker. Use browser SSH:"
  echo "   https://lightsail.aws.amazon.com/ls/webapp/us-east-1/instances/presgen-prod/connect"
  echo "   Run: cd /home/ubuntu/presgen && docker-compose up -d"
  rm -f /tmp/lightsail-restore-key.pem
fi

echo ""
echo "🎉 Restoration complete!"
echo "🔗 Access at: http://$STATIC_IP"
