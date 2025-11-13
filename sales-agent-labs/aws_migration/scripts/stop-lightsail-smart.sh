#!/bin/bash
set -e

echo "🛑 Stopping Lightsail instance to save costs..."

# Configuration
MAX_SNAPSHOTS=3  # Keep only the 3 most recent snapshots
INSTANCE_NAME="presgen-prod"

# Create snapshot before stopping
SNAPSHOT_NAME="presgen-prod-snapshot-$(date +%Y%m%d-%H%M%S)"
echo "📸 Creating snapshot: $SNAPSHOT_NAME"
aws lightsail create-instance-snapshot \
  --instance-name "$INSTANCE_NAME" \
  --instance-snapshot-name "$SNAPSHOT_NAME"

echo "⏳ Waiting for snapshot to complete..."
aws lightsail wait instance-snapshot-available \
  --instance-snapshot-name "$SNAPSHOT_NAME"

echo "✅ Snapshot created successfully"

# Clean up old snapshots (keep only MAX_SNAPSHOTS most recent)
echo "🧹 Checking for old snapshots to delete..."

# Get all snapshots for this instance, sorted by creation date (oldest first)
SNAPSHOTS=$(aws lightsail get-instance-snapshots \
  --query "instanceSnapshots[?fromInstanceName=='$INSTANCE_NAME'].name" \
  --output text | tr '\t' '\n' | sort)

SNAPSHOT_COUNT=$(echo "$SNAPSHOTS" | wc -l | tr -d ' ')

if [ "$SNAPSHOT_COUNT" -gt "$MAX_SNAPSHOTS" ]; then
  DELETE_COUNT=$((SNAPSHOT_COUNT - MAX_SNAPSHOTS))
  echo "📊 Found $SNAPSHOT_COUNT snapshots, deleting oldest $DELETE_COUNT..."

  # Delete oldest snapshots
  echo "$SNAPSHOTS" | head -n "$DELETE_COUNT" | while read -r old_snapshot; do
    if [ -n "$old_snapshot" ]; then
      echo "🗑️  Deleting old snapshot: $old_snapshot"
      aws lightsail delete-instance-snapshot \
        --instance-snapshot-name "$old_snapshot"
    fi
  done

  echo "✅ Deleted $DELETE_COUNT old snapshots"
  echo "💰 Snapshot cost: ~\$$(($MAX_SNAPSHOTS * 4))/month (keeping $MAX_SNAPSHOTS snapshots)"
else
  echo "✅ Snapshot count ($SNAPSHOT_COUNT) within limit ($MAX_SNAPSHOTS)"
  echo "💰 Snapshot cost: ~\$$(($SNAPSHOT_COUNT * 4))/month"
fi

# Stop instance
echo "🛑 Stopping instance..."
aws lightsail stop-instance --instance-name "$INSTANCE_NAME"

echo "⏳ Waiting for instance to stop..."
sleep 30

# Verify stopped
STATE=$(aws lightsail get-instance --instance-name "$INSTANCE_NAME" | grep -o '"name": "stopped"' || echo "not stopped")
if [[ $STATE == *"stopped"* ]]; then
  echo "✅ Instance stopped successfully"
  echo "💰 Now saving ~\$0.67/day"
  echo "📸 Latest snapshot: $SNAPSHOT_NAME"
  echo "📚 Total snapshots kept: $MAX_SNAPSHOTS"
else
  echo "⚠️  Instance may not be stopped yet, check status"
fi

# List remaining snapshots
echo ""
echo "📋 Remaining snapshots:"
aws lightsail get-instance-snapshots \
  --query "instanceSnapshots[?fromInstanceName=='$INSTANCE_NAME'].[name,createdAt,sizeInGb]" \
  --output table
