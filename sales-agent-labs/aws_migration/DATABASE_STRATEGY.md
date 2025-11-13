# PresGen Database Strategy for AWS Migration

**Version:** 1.0
**Date:** November 13, 2025
**Decision:** **STAY ON SQLite** (Recommended)
**Rationale:** Simplicity, reliability, cost-effectiveness for current use case

---

## Executive Summary

**Recommendation: Keep SQLite for AWS Lightsail deployment**

- ✅ **Current setup works:** SQLite is already proven in your environment
- ✅ **Right-sized for use case:** Demo/internal tool with <10 concurrent users
- ✅ **Zero complexity:** No database server to manage
- ✅ **Zero cost:** Included in Lightsail instance
- ✅ **Easy backups:** Simple file copy
- ✅ **Future flexibility:** Can migrate to PostgreSQL later if needed

---

## SQLite vs PostgreSQL: Detailed Comparison

### Performance Comparison

| Metric | SQLite | PostgreSQL (Docker) | PostgreSQL (Lightsail DB) |
|--------|--------|---------------------|---------------------------|
| **Read Performance** | ⚡ Excellent (faster than network DB) | ✅ Good | ✅ Good |
| **Write Performance (single user)** | ⚡ Excellent | ✅ Good | ✅ Good |
| **Write Performance (concurrent)** | ⚠️ Limited (1 writer at a time) | ⚡ Excellent | ⚡ Excellent |
| **Latency** | ⚡ Zero (file access) | ✅ ~1ms (Docker network) | ⚠️ ~5-10ms (separate server) |
| **Throughput** | ✅ 100-200 req/s (single user) | ⚡ 1000+ req/s | ⚡ 1000+ req/s |

### Operational Complexity

| Factor | SQLite | PostgreSQL (Docker) | PostgreSQL (Lightsail DB) |
|--------|--------|---------------------|---------------------------|
| **Setup** | ✅ Zero config | ⚠️ docker-compose.yml | ❌ AWS console setup |
| **Maintenance** | ✅ None | ⚠️ Docker container mgmt | ✅ Managed (AWS handles) |
| **Backups** | ✅ `cp database.db backup.db` | ⚠️ `pg_dump` + scripts | ✅ Automated snapshots |
| **Monitoring** | ✅ File size only | ⚠️ Metrics + queries | ✅ CloudWatch metrics |
| **Scaling** | ❌ Vertical only | ⚠️ Vertical + read replicas | ✅ Managed scaling |
| **Troubleshooting** | ✅ Simple | ⚠️ Moderate | ⚠️ Moderate |

### Cost Analysis

| Option | Monthly Cost | Included | Notes |
|--------|--------------|----------|-------|
| **SQLite** | **$0** | Lightsail instance | No extra cost |
| **PostgreSQL (Docker)** | **$0** | Lightsail instance | Uses instance RAM (~300MB) |
| **Lightsail Managed DB (1GB)** | **$15** | Backups, HA option | Separate billing |
| **RDS db.t3.micro** | **$25+** | Backups | Overkill for this use case |

### Reliability & Durability

| Factor | SQLite | PostgreSQL (Docker) | PostgreSQL (Lightsail DB) |
|--------|--------|---------------------|---------------------------|
| **Data Durability** | ✅ Excellent (file on disk) | ✅ Excellent (volume) | ⚡ Best (managed backups) |
| **Crash Recovery** | ✅ Built-in WAL | ✅ Built-in WAL | ⚡ Best (managed) |
| **Backup Frequency** | Manual (or cron) | Manual (or cron) | ⚡ Automated hourly |
| **Point-in-Time Recovery** | ❌ No | ⚠️ With setup | ✅ Yes |
| **High Availability** | ❌ No | ❌ No (single container) | ⚠️ Optional (multi-AZ) |

---

## Recommendation Matrix

### Use SQLite if:

- ✅ **Concurrent users: <10** (you fit here)
- ✅ **Use case: Demo, internal tool, MVP**
- ✅ **Team size: 1-5 developers**
- ✅ **Budget: Tight ($0 for DB preferred)**
- ✅ **Complexity tolerance: Low (keep it simple)**
- ✅ **Write patterns: Mostly reads, occasional writes**
- ✅ **Data size: <10GB** (you're likely <1GB)

**Verdict: ✅ This is you!**

### Use PostgreSQL (Docker) if:

- ⚠️ **Concurrent users: 10-50**
- ⚠️ **Write-heavy workload** (>100 writes/minute)
- ⚠️ **Experiencing "database is locked" errors**
- ⚠️ **Need complex queries** (window functions, CTEs, etc.)
- ⚠️ **Future growth expected** (scaling to 100+ users)

**Verdict:** ⚠️ Not yet, but easy to upgrade later

### Use PostgreSQL (Lightsail Managed DB) if:

- ❌ **Production SaaS** with paying customers
- ❌ **Concurrent users: 50+**
- ❌ **SLA requirements** (99.9% uptime)
- ❌ **Compliance mandates** (SOC 2, HIPAA requiring managed DB)
- ❌ **Multi-region deployment**

**Verdict:** ❌ Overkill for your use case

---

## SQLite on AWS Lightsail: Implementation Plan

### Architecture

```
Lightsail Instance (medium_2_0)
├── Docker Volumes
│   └── presgen-data (persistent)
│       └── assess/
│           └── presgen_assess.db  ← SQLite file here
│
├── Containers
│   └── presgen-assess
│       └── Mounts: presgen-data:/app/data
│
└── Daily Backup (S3)
    └── s3://presgen-prod-backups/sqlite/
        └── presgen_assess-20251113.db
```

### Docker Compose Configuration

```yaml
# Already in your docker-compose.yml
services:
  presgen-assess:
    image: presgen-assess:latest
    environment:
      - DATABASE_URL=sqlite:///data/assess/presgen_assess.db
    volumes:
      - presgen-data:/app/data  # Persistent volume
    restart: unless-stopped

volumes:
  presgen-data:
    driver: local
    driver_opts:
      type: none
      device: /home/ubuntu/presgen/data
      o: bind
```

### Backup Strategy

**Daily Automated Backup to S3:**

```bash
#!/bin/bash
# /home/ubuntu/presgen/scripts/backup-sqlite.sh

DATE=$(date +%Y%m%d-%H%M%S)
DB_FILE="/home/ubuntu/presgen/data/assess/presgen_assess.db"
BACKUP_DIR="/tmp/presgen-backup-$DATE"
S3_BUCKET="presgen-prod-backups"

# Create backup
mkdir -p "$BACKUP_DIR"
sqlite3 "$DB_FILE" ".backup $BACKUP_DIR/presgen_assess.db"

# Compress
gzip "$BACKUP_DIR/presgen_assess.db"

# Upload to S3 (optional - only if using S3)
if command -v aws &> /dev/null; then
    aws s3 cp "$BACKUP_DIR/presgen_assess.db.gz" \
        "s3://$S3_BUCKET/sqlite/presgen_assess-$DATE.db.gz"
fi

# Keep local backups for 7 days
find /home/ubuntu/presgen/backups/sqlite/ -name "*.db.gz" -mtime +7 -delete

# Cleanup
rm -rf "$BACKUP_DIR"
```

**Schedule via cron:**
```bash
# Daily at 2 AM
0 2 * * * /home/ubuntu/presgen/scripts/backup-sqlite.sh
```

### Monitoring

**What to monitor:**

```bash
# Database file size
du -h /home/ubuntu/presgen/data/assess/presgen_assess.db

# Check for locks (if experiencing issues)
lsof /home/ubuntu/presgen/data/assess/presgen_assess.db

# Integrity check
sqlite3 /home/ubuntu/presgen/data/assess/presgen_assess.db "PRAGMA integrity_check;"

# Table sizes
sqlite3 /home/ubuntu/presgen/data/assess/presgen_assess.db ".tables"
sqlite3 /home/ubuntu/presgen/data/assess/presgen_assess.db "SELECT COUNT(*) FROM workflows;"
```

**Set up alerts:**
- Database file size > 5GB
- "Database is locked" errors in logs

---

## Migration Path: SQLite → PostgreSQL (If Needed Later)

**When to migrate:**
1. Sustained "database is locked" errors (>10/day)
2. Concurrent users consistently >10
3. Database size >10GB
4. Need for advanced PostgreSQL features
5. Scaling to production SaaS

**Migration Steps:**

### Option 1: PostgreSQL in Docker (Easiest)

```yaml
# Add to docker-compose.yml
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: presgen_assess
      POSTGRES_USER: presgen
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  postgres-data:
```

**Migration script:**
```bash
# Export from SQLite
sqlite3 presgen_assess.db .dump > dump.sql

# Import to PostgreSQL
psql -U presgen -d presgen_assess -f dump.sql

# Update .env
DATABASE_URL=postgresql://presgen:PASSWORD@postgres:5432/presgen_assess
```

**Cost:** $0 (uses ~300MB of instance RAM)
**Time:** 2-3 hours

### Option 2: Lightsail Managed Database

```bash
# Create managed database
aws lightsail create-relational-database \
  --relational-database-name presgen-db \
  --relational-database-bundle-id micro_1_0 \
  --master-database-name presgen_assess \
  --master-username presgen
```

**Cost:** $15/month
**Time:** 4-5 hours (includes setup, migration, testing)

---

## SQLite Performance Optimization

**Already implemented in your setup:**

```python
# presgen-assess/src/common/config.py
# SQLite optimizations:
# - WAL mode enabled (better concurrency)
# - Busy timeout (retry on lock)
# - Foreign keys enabled
```

**If experiencing lock issues, tune these:**

```python
# In database connection setup
engine = create_engine(
    "sqlite:///data/assess/presgen_assess.db",
    connect_args={
        "check_same_thread": False,
        "timeout": 30,  # Wait 30 seconds for lock
    },
    pool_pre_ping=True,  # Verify connections
    pool_recycle=3600,   # Recycle connections hourly
)

# Enable WAL mode
with engine.connect() as conn:
    conn.execute(text("PRAGMA journal_mode=WAL"))
    conn.execute(text("PRAGMA busy_timeout=30000"))  # 30 seconds
```

---

## Real-World SQLite at Scale

**Companies using SQLite in production:**
- **Expensify:** Syncing engine for millions of users
- **Airbnb:** Offline data storage in mobile app
- **Dropbox:** Local file metadata
- **Firefox:** Browser database
- **Apple:** Core Data (SQLite backend)

**SQLite can handle:**
- Database size: Up to 281 TB (theoretical), 100GB+ practical
- Transactions: 100,000+ per second
- Concurrent reads: Unlimited
- Concurrent writes: 1 at a time (but very fast)

**Your use case:** Assessment data, gap analysis results
- **Estimated size:** <1GB for thousands of assessments
- **Write frequency:** Low (user-initiated assessments)
- **Read frequency:** Moderate (dashboard queries)

**Verdict:** SQLite is perfect for this workload

---

## Decision Summary

### ✅ Recommendation: SQLite

**Benefits:**
1. **Zero configuration:** Works out of the box
2. **Zero cost:** No additional database charges
3. **Fast:** Lower latency than network database
4. **Simple backups:** `cp database.db backup.db`
5. **Proven:** Already working in your setup
6. **Future-proof:** Can migrate to PostgreSQL if needed

**Limitations (acceptable for your use case):**
1. **Concurrency:** 1 writer at a time (fine for <10 users)
2. **Scaling:** Vertical only (Lightsail instance can scale)
3. **Features:** Fewer advanced SQL features (you don't need them)

### ⚠️ When to Reconsider

Monitor these metrics monthly:

| Metric | Threshold | Action |
|--------|-----------|--------|
| "Database locked" errors | >10/day | Consider PostgreSQL |
| Concurrent users | >10 sustained | Benchmark performance |
| Database size | >5GB | Consider managed DB |
| Write frequency | >100/minute | Consider PostgreSQL |
| Query response time | >1 second | Optimize queries |

**Set calendar reminder:** Review database performance every 3 months

---

## Implementation Checklist

### Phase 2: AWS Infrastructure (Keep SQLite)

- [ ] Provision Lightsail instance with sufficient disk (60GB SSD)
- [ ] Create persistent Docker volume for `/data`
- [ ] Verify SQLite database mounts correctly
- [ ] Test database access from presgen-assess container

### Phase 3: Initial Deployment

- [ ] Copy existing SQLite database to Lightsail
  ```bash
  scp -i lightsail-key.pem data/assess/presgen_assess.db \
      ubuntu@<IP>:/home/ubuntu/presgen/data/assess/
  ```
- [ ] Run Alembic migrations to ensure schema is current
  ```bash
  docker exec presgen-assess alembic upgrade head
  ```
- [ ] Verify data integrity
  ```bash
  docker exec presgen-assess sqlite3 /app/data/assess/presgen_assess.db \
      "PRAGMA integrity_check;"
  ```

### Phase 4: Functional Validation

- [ ] Test assessments creation
- [ ] Test gap analysis queries
- [ ] Test concurrent user simulation (if >5 expected users)
- [ ] Monitor for "database locked" errors
- [ ] Benchmark query performance

### Phase 7: Monitoring & Operations

- [ ] Set up backup script (`backup-sqlite.sh`)
- [ ] Schedule daily backups (cron)
- [ ] Test restore procedure
- [ ] Monitor database file size
- [ ] Set up alerts for errors

---

## Conclusion

**For your use case (demo/internal tool, <10 users, simple deployment), SQLite is the RIGHT choice.**

- ✅ Simpler than PostgreSQL
- ✅ Cheaper than managed databases
- ✅ Faster than network databases
- ✅ Already proven in your setup
- ✅ Easy to upgrade later if needed

**Don't over-engineer.** Use SQLite now, migrate to PostgreSQL only when you have concrete evidence it's needed.

---

**Decision:** ✅ **STAY ON SQLite**

**Next Steps:**
1. Continue with Phase 1 (Rollback Procedure documentation)
2. Proceed to Phase 2 (AWS Infrastructure) with SQLite
3. Set up automated backups in Phase 7
4. Review database performance monthly

---

**Status:** ✅ Decision Finalized
**Last Updated:** November 13, 2025
**Approver:** Yitzchak Meirovich

---

*Database strategy aligns with AWS Well-Architected Framework principles:*
*"Choose the simplest solution that meets your requirements"*
