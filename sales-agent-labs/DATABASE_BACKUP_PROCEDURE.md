# Database Backup Procedure

## Critical Information

**NEVER commit database files to git!** Database files are now in `.gitignore` and will not be tracked.

## Files Protected from Git

- `data/assess/presgen_assess.db` - Main production database
- `data/assess/chroma/` - ChromaDB vector database
- All `*.db`, `*.sqlite`, `*.sqlite3` files
- Database WAL and SHM files (`*.db-shm`, `*.db-wal`)

## Manual Backup Procedure

### On the Server (Ubuntu)

```bash
# Navigate to project directory
cd /home/ubuntu/presgen/sales-agent-labs

# Create timestamped backup
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
cp data/assess/presgen_assess.db "data/assess/presgen_assess_backup_${TIMESTAMP}.db"

# Verify backup was created
ls -lh data/assess/*.db

# Keep only last 7 backups (delete older ones)
cd data/assess
ls -t presgen_assess_backup_*.db | tail -n +8 | xargs rm -f
```

### Automated Daily Backup (Recommended)

Create a cron job to backup daily at 2 AM:

```bash
# Edit crontab
crontab -e

# Add this line:
0 2 * * * cd /home/ubuntu/presgen/sales-agent-labs && cp data/assess/presgen_assess.db "data/assess/presgen_assess_backup_$(date +\%Y\%m\%d_\%H\%M\%S).db" && find data/assess -name "presgen_assess_backup_*.db" -mtime +7 -delete
```

## Restore from Backup

```bash
# List available backups
ls -lh data/assess/presgen_assess_backup_*.db

# Stop the service
docker-compose stop presgen-assess

# Restore from specific backup (replace TIMESTAMP)
cp data/assess/presgen_assess_backup_TIMESTAMP.db data/assess/presgen_assess.db

# Restart the service
docker-compose up -d presgen-assess

# Verify restoration
docker logs presgen-assess | tail -20
```

## Before Git Pull (Important!)

**The database is now protected by .gitignore**, but as a safety measure:

```bash
# Create a quick backup before pulling code updates
cd /home/ubuntu/presgen/sales-agent-labs
cp data/assess/presgen_assess.db data/assess/presgen_assess_pre_pull.db

# Now safe to pull
git pull origin 001-read-specification-md

# Verify database was NOT overwritten
ls -lh data/assess/presgen_assess.db
# (timestamp should NOT change after pull)
```

## Database Recovery Checklist

If data is lost:

1. **Stop the service immediately**
   ```bash
   docker-compose stop presgen-assess
   ```

2. **Check for recent backups**
   ```bash
   ls -lht data/assess/*.db | head -10
   ```

3. **Restore the most recent backup**
   ```bash
   cp data/assess/presgen_assess_backup_YYYYMMDD_HHMMSS.db data/assess/presgen_assess.db
   ```

4. **Restart the service**
   ```bash
   docker-compose up -d presgen-assess
   ```

5. **Verify data is present**
   - Log into the UI
   - Check for recent workflows and courses
   - Check certification profiles

## What NOT to Do

- ❌ **NEVER** commit database files to git
- ❌ **NEVER** use `git add data/assess/*.db`
- ❌ **NEVER** remove `*.db` from `.gitignore`
- ❌ **NEVER** pull code changes without verifying database is backed up

## Production Database Location

- **Server**: `/home/ubuntu/presgen/sales-agent-labs/data/assess/presgen_assess.db`
- **Container**: `/app/data/assess/presgen_assess.db` (mounted from server)

## Backup Storage Recommendations

For production:
1. Set up automated daily backups with cron
2. Keep last 7 daily backups on server
3. Weekly: Copy backups to separate storage (S3, external drive, etc.)
4. Monthly: Archive important backups for long-term retention

## Emergency Contact Information

If database is corrupted or lost beyond recovery:
- Check docker volumes: `docker volume ls`
- Check container mounts: `docker inspect presgen-assess | grep Mounts -A 20`
- Database schema can be recreated with: `alembic upgrade head`
- Data must be re-entered manually (no automatic recovery without backup)
