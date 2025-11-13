#!/bin/bash
set -e

echo "🛑 Stopping Lightsail instance (NO SNAPSHOT)..."
echo "⚠️  Skipping snapshot creation to minimize costs"
echo "ℹ️  Data persists on instance disk even when stopped"

INSTANCE_NAME="presgen-prod"

# Stop instance immediately (no snapshot)
echo "🛑 Stopping instance..."
aws lightsail stop-instance --instance-name "$INSTANCE_NAME"

echo "⏳ Waiting for instance to stop..."
sleep 30

# Verify stopped
STATE=$(aws lightsail get-instance --instance-name "$INSTANCE_NAME" | grep -o '"name": "stopped"' || echo "not stopped")
if [[ $STATE == *"stopped"* ]]; then
  echo "✅ Instance stopped successfully"
  echo "💰 Now saving ~\$0.67/day (instance cost)"
  echo "💰 Snapshot cost: \$0/month (no snapshots created)"
  echo ""
  echo "ℹ️  To create a manual snapshot later:"
  echo "   aws lightsail create-instance-snapshot \\"
  echo "     --instance-name $INSTANCE_NAME \\"
  echo "     --instance-snapshot-name presgen-prod-manual-$(date +%Y%m%d)"
else
  echo "⚠️  Instance may not be stopped yet, check status"
fi
