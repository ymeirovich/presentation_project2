#!/bin/bash
set -e

echo "🛑 Stopping Lightsail instance to save costs..."

# Create snapshot before stopping (optional but recommended)
SNAPSHOT_NAME="presgen-prod-snapshot-$(date +%Y%m%d-%H%M%S)"
echo "📸 Creating snapshot: $SNAPSHOT_NAME"
aws lightsail create-instance-snapshot \
  --instance-name presgen-prod \
  --instance-snapshot-name "$SNAPSHOT_NAME"

echo "⏳ Waiting for snapshot to complete..."
aws lightsail wait instance-snapshot-available \
  --instance-snapshot-name "$SNAPSHOT_NAME"

# Stop instance
echo "🛑 Stopping instance..."
aws lightsail stop-instance --instance-name presgen-prod

echo "⏳ Waiting for instance to stop..."
sleep 30

# Verify stopped
STATE=$(aws lightsail get-instance --instance-name presgen-prod | grep -o '"name": "stopped"' || echo "not stopped")
if [[ $STATE == *"stopped"* ]]; then
  echo "✅ Instance stopped successfully"
  echo "💰 Now saving ~\$0.67/day"
  echo "📸 Snapshot created: $SNAPSHOT_NAME"
else
  echo "⚠️  Instance may not be stopped yet, check status"
fi
