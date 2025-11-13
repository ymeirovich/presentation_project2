# Lightsail Snapshot Management Guide

**Date:** November 14, 2025
**Purpose:** Manage Lightsail snapshots to control costs while maintaining backups

---

## Understanding Snapshots

### What Are Snapshots?

Snapshots are **point-in-time backups** of your entire Lightsail instance:
- ✅ Complete backup of 80GB disk
- ✅ All files, databases, Docker volumes
- ✅ System state at snapshot creation
- ✅ Can restore to new instance if needed

### Snapshot Versioning

**Snapshots are VERSIONED, not overwritten.**

Each time you run the stop script, it creates a **NEW snapshot** with a unique timestamp:

```
presgen-prod-snapshot-20251114-100000  (Created Nov 14, 10:00 AM)
presgen-prod-snapshot-20251114-150000  (Created Nov 14, 3:00 PM)
presgen-prod-snapshot-20251115-090000  (Created Nov 15, 9:00 AM)
```

**They accumulate** unless you delete them manually.

---

## 💰 Cost Implications

### Snapshot Pricing
- **Cost:** $0.05/GB/month per snapshot
- **Your instance:** 80GB
- **Per snapshot:** ~$4/month

### Cost Accumulation Example

| Usage Pattern | Snapshots/Month | Monthly Cost |
|---------------|-----------------|--------------|
| Stop once/week | 4 snapshots | $16/month |
| Stop daily (workdays) | 20 snapshots | $80/month |
| Stop twice/day | 60 snapshots | $240/month |

⚠️ **Without cleanup, snapshot costs can exceed instance costs!**

---

## 📊 Snapshot Strategy Comparison

### Strategy 1: Every Stop Creates Snapshot (Default)

**Script:** `stop-lightsail.sh` (original)

**Pros:**
- ✅ Maximum safety
- ✅ Multiple restore points
- ✅ Can recover from any point in time

**Cons:**
- ❌ Costs accumulate quickly
- ❌ Requires manual cleanup
- ❌ Can cost more than instance itself

**Best for:**
- Infrequent stop/start (1-2 times/week)
- Critical data that changes often
- You remember to clean up old snapshots

**Monthly snapshot cost:** $4 × number of stops

---

### Strategy 2: Keep Latest 3 Snapshots (Recommended)

**Script:** `stop-lightsail-smart.sh` (new)

**How it works:**
1. Creates new snapshot before stopping
2. Automatically deletes snapshots older than the 3 most recent
3. Always maintains 3 restore points

**Pros:**
- ✅ Automatic cleanup (no manual work)
- ✅ Fixed, predictable cost
- ✅ Multiple restore points
- ✅ Balance of safety and cost

**Cons:**
- ⚠️ Lose snapshots older than 3rd most recent
- ⚠️ Can't recover from points >3 stops ago

**Best for:**
- Regular stop/start usage
- Good balance of safety and cost
- Most users (recommended default)

**Monthly snapshot cost:** Fixed at ~$12/month (3 snapshots)

---

### Strategy 3: No Snapshots (Cheapest)

**Script:** `stop-lightsail-no-snapshot.sh` (new)

**How it works:**
- Stops instance immediately
- No snapshot created
- Data persists on instance disk

**Pros:**
- ✅ Zero snapshot costs
- ✅ Fastest stop time
- ✅ Data still safe (persists on disk)

**Cons:**
- ❌ No backup if instance is accidentally deleted
- ❌ Can't restore to earlier state
- ❌ No protection against instance corruption

**Best for:**
- Non-critical development/testing
- Budget-conscious deployments
- You have other backup strategies
- You're confident you won't delete the instance

**Monthly snapshot cost:** $0

**Risk mitigation:**
- Create manual snapshots before major changes
- Export SQLite database backups to local machine
- Use S3 for critical data backups

---

## 🛠️ Available Scripts

### 1. Original Stop Script (Creates Snapshots)
```bash
./aws_migration/scripts/stop-lightsail.sh
```

**What it does:**
- ✅ Creates snapshot with timestamp
- ✅ Waits for snapshot completion
- ✅ Stops instance
- ❌ Does NOT delete old snapshots

**Use when:** You want maximum backups and will manually manage them

---

### 2. Smart Stop Script (Auto-Cleanup)
```bash
./aws_migration/scripts/stop-lightsail-smart.sh
```

**What it does:**
- ✅ Creates new snapshot
- ✅ Automatically deletes oldest snapshots (keeps 3)
- ✅ Shows cost estimate
- ✅ Lists remaining snapshots

**Configuration:**
```bash
# Edit script to change how many to keep
MAX_SNAPSHOTS=3  # Default: keep 3 most recent
```

**Use when:** You want automatic cleanup and predictable costs (RECOMMENDED)

---

### 3. No-Snapshot Stop Script (Cheapest)
```bash
./aws_migration/scripts/stop-lightsail-no-snapshot.sh
```

**What it does:**
- ✅ Stops instance immediately
- ❌ No snapshot created
- ℹ️ Data still safe on disk

**Use when:** You want zero snapshot costs and accept the risk

---

## 📋 Manual Snapshot Management Commands

### List All Snapshots
```bash
aws lightsail get-instance-snapshots \
  --query 'instanceSnapshots[*].[name,createdAt,sizeInGb]' \
  --output table
```

### List Snapshots for presgen-prod Only
```bash
aws lightsail get-instance-snapshots \
  --query "instanceSnapshots[?fromInstanceName=='presgen-prod'].[name,createdAt,sizeInGb]" \
  --output table
```

### Count Snapshots
```bash
aws lightsail get-instance-snapshots \
  --query "instanceSnapshots[?fromInstanceName=='presgen-prod'].name" \
  --output text | wc -w
```

### Calculate Total Snapshot Cost
```bash
# Get total GB across all snapshots
TOTAL_GB=$(aws lightsail get-instance-snapshots \
  --query "instanceSnapshots[?fromInstanceName=='presgen-prod'].sizeInGb" \
  --output text | awk '{s+=$1} END {print s}')

echo "Total snapshot storage: ${TOTAL_GB}GB"
echo "Estimated monthly cost: \$$(echo "$TOTAL_GB * 0.05" | bc)"
```

### Delete Specific Snapshot
```bash
aws lightsail delete-instance-snapshot \
  --instance-snapshot-name presgen-prod-snapshot-20251114-100000
```

### Delete All Snapshots Older Than 7 Days
```bash
# Get snapshots older than 7 days
CUTOFF_DATE=$(date -u -v-7d +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ)

aws lightsail get-instance-snapshots \
  --query "instanceSnapshots[?fromInstanceName=='presgen-prod' && createdAt<'$CUTOFF_DATE'].name" \
  --output text | tr '\t' '\n' | while read snapshot; do
    if [ -n "$snapshot" ]; then
      echo "Deleting old snapshot: $snapshot"
      aws lightsail delete-instance-snapshot --instance-snapshot-name "$snapshot"
    fi
  done
```

### Create Manual Snapshot (On-Demand)
```bash
aws lightsail create-instance-snapshot \
  --instance-name presgen-prod \
  --instance-snapshot-name presgen-prod-manual-$(date +%Y%m%d-%H%M%S)
```

---

## 🎯 Recommended Strategy by Use Case

### Development/Testing
**Recommendation:** No snapshots or 1 manual snapshot/week

```bash
# Daily: Use no-snapshot script
./aws_migration/scripts/stop-lightsail-no-snapshot.sh

# Weekly: Create one manual snapshot on Friday
aws lightsail create-instance-snapshot \
  --instance-name presgen-prod \
  --instance-snapshot-name presgen-prod-weekly-$(date +%Y%m%d)
```

**Cost:** $0-4/month

---

### Regular Demo/Production Use
**Recommendation:** Smart script (keep 3 snapshots)

```bash
# Always use smart script
./aws_migration/scripts/stop-lightsail-smart.sh
```

**Cost:** ~$12/month (3 snapshots)

---

### Critical Production Data
**Recommendation:** Original script + manual cleanup weekly

```bash
# Daily: Create snapshots
./aws_migration/scripts/stop-lightsail.sh

# Weekly: Clean up old ones (keep 7)
# Run manual cleanup script
```

**Cost:** ~$28/month (7 snapshots)

---

## 🔄 Restoring from Snapshot

### Create New Instance from Snapshot
```bash
aws lightsail create-instances-from-snapshot \
  --instance-names presgen-prod-restored \
  --availability-zone us-east-1a \
  --bundle-id medium_2_0 \
  --instance-snapshot-name presgen-prod-snapshot-20251114-100000
```

### Attach Static IP to Restored Instance
```bash
# Detach from old instance
aws lightsail detach-static-ip --static-ip-name presgen-prod-ip

# Attach to restored instance
aws lightsail attach-static-ip \
  --static-ip-name presgen-prod-ip \
  --instance-name presgen-prod-restored
```

---

## 💡 Best Practices

1. **Choose Your Strategy Early**
   - Decide which stop script to use based on your needs
   - Stick with it consistently

2. **Monitor Snapshot Costs**
   ```bash
   # Weekly: Check snapshot count and cost
   aws lightsail get-instance-snapshots \
     --query "instanceSnapshots[?fromInstanceName=='presgen-prod']" \
     | jq length
   ```

3. **Clean Up Before Major Costs Accumulate**
   - Review snapshots monthly
   - Delete unnecessary old snapshots

4. **Alternative: Export SQLite to Local**
   Instead of many snapshots, export database regularly:
   ```bash
   scp -i lightsail-key.pem ubuntu@35.175.156.231:/home/ubuntu/presgen/data/assess/presgen_assess.db ~/backups/presgen_assess-$(date +%Y%m%d).db
   ```

5. **Test Restore Procedure**
   - Test restoring from snapshot at least once
   - Verify all data is intact
   - Document the process

---

## 📊 Cost Comparison Summary

| Strategy | Snapshot Cost/Month | Instance Cost/Month | Total/Month | Safety Level |
|----------|---------------------|---------------------|-------------|--------------|
| **No snapshots** | $0 | $20 | **$20** | ⚠️ Medium |
| **Keep 3 (smart)** | $12 | $20 | **$32** | ✅ Good |
| **All snapshots (daily)** | $80+ | $20 | **$100+** | ✅✅ Excellent |
| **Manual weekly** | $4 | $20 | **$24** | ✅ Good |

---

## 🎯 My Recommendation

**Use the Smart Stop Script** (`stop-lightsail-smart.sh`)

**Why:**
- ✅ Automatic cleanup (no manual work)
- ✅ Fixed $12/month cost (predictable)
- ✅ 3 restore points (recent safety)
- ✅ Best balance of cost and safety

**Command:**
```bash
# Always use this when stopping
./aws_migration/scripts/stop-lightsail-smart.sh
```

**Plus:** Create manual snapshots before major changes:
```bash
# Before major deployment or changes
aws lightsail create-instance-snapshot \
  --instance-name presgen-prod \
  --instance-snapshot-name presgen-prod-before-phase3-$(date +%Y%m%d)
```

---

**Questions?** All three stop scripts are now available in `aws_migration/scripts/`
