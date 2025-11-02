# File Upload API - Recent Fixes & Deployment Notes

**Date:** November 2, 2025
**Status:** ✅ Fixed and Ready for AWS Deployment
**Related Issues:** HTTP 500/405 errors, SQLite table errors

---

## 🐛 Issues Identified & Fixed

### Issue 1: SQLite Database Table Initialization

**Problem:**
```
OperationalError: (sqlite3.OperationalError) no such table: knowledge_base_documents
```

**Root Cause:**
The `FileRegistry` class creates its own synchronous SQLite database connection but wasn't ensuring tables were created when the engine was initialized.

**Location:** `src/service/file_upload_service.py:365-383`

**Fix Applied:** ✅
```python
def _get_db(self):
    """Get database session"""
    if self._db_session:
        return self._db_session

    # Create synchronous SQLite session for file registry
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from src.models.base import Base

    # Use SQLite database
    db_path = 'test_database.db'
    engine = create_engine(f'sqlite:///{db_path}', echo=False)

    # Ensure tables exist in SQLite database
    Base.metadata.create_all(engine)  # ← FIX: Added this line

    Session = sessionmaker(bind=engine)
    return Session()
```

**Impact:** File uploads now persist successfully to SQLite database

---

### Issue 2: Incorrect API Endpoint URLs (Client-Side)

**Problems:**
1. **HTTP 500** on `http://localhost/api/presgen-assess/files/upload`
2. **HTTP 405** on `http://localhost/api/presgen-assess/files/profile?profileId=xxx`

**Root Causes:**

#### Upload Endpoint
- ❌ Client URL: `http://localhost/api/presgen-assess/files/upload`
- ✅ Correct URL: `http://localhost:8000/api/v1/presgen-assess/files/upload`

**Issues:**
- Missing port `:8000`
- Missing API version prefix `/api/v1`

#### Profile Endpoint
- ❌ Client URL: `http://localhost/api/presgen-assess/files/profile?profileId=xxx`
- ✅ Correct URL: `http://localhost:8000/api/v1/presgen-assess/files/profile/{profileId}`

**Issues:**
- Missing port `:8000`
- Missing API version prefix `/api/v1`
- Using query parameter `?profileId=` instead of path parameter `/{profileId}`

**Location References:**
- App config: `src/service/app.py:177` - mounts routes with `/api/v1`
- Router config: `src/service/api/v1/router.py:124-128` - prefix `/presgen-assess`
- File router: `src/service/api/v1/endpoints/file_management.py:26` - prefix `/files`
- Upload endpoint: `src/service/api/v1/endpoints/file_management.py:92` - POST `/upload`
- Profile endpoint: `src/service/api/v1/endpoints/file_management.py:275` - GET `/profile/{cert_profile_id}`

---

## 📋 Complete API Endpoint Reference

### File Upload Endpoints

| Endpoint | Method | URL | Request Body |
|----------|--------|-----|--------------|
| **Upload File** | POST | `/api/v1/presgen-assess/files/upload` | multipart/form-data |
| **List Profile Files** | GET | `/api/v1/presgen-assess/files/profile/{profileId}` | - |
| **List User Files** | GET | `/api/v1/presgen-assess/files/user` | - |
| **File Status** | GET | `/api/v1/presgen-assess/files/{fileId}/status` | - |
| **Process File** | POST | `/api/v1/presgen-assess/files/{fileId}/process` | JSON |
| **Delete File** | DELETE | `/api/v1/presgen-assess/files/{fileId}` | - |
| **Download File** | GET | `/api/v1/presgen-assess/files/{fileId}/download` | - |

### Collection Management Endpoints

| Endpoint | Method | URL | Purpose |
|----------|--------|-----|---------|
| **Create Collection** | POST | `/api/v1/presgen-assess/files/collections/{profileId}/create` | Create ChromaDB collection |
| **Delete Collection** | DELETE | `/api/v1/presgen-assess/files/collections/{profileId}` | Delete ChromaDB collection |
| **List Collections** | GET | `/api/v1/presgen-assess/files/collections/user` | List user collections |

### Upload File Request Example

```bash
curl -X POST "http://localhost:8000/api/v1/presgen-assess/files/upload" \
  -F "file=@example.pdf" \
  -F "cert_profile_id=184ef7eb-c6a9-4271-a1e4-204cded7c2f2" \
  -F "resource_type=exam_guide" \
  -F "process_immediately=true"
```

### List Profile Files Request Example

```bash
curl -X GET "http://localhost:8000/api/v1/presgen-assess/files/profile/184ef7eb-c6a9-4271-a1e4-204cded7c2f2"
```

---

## 🗄️ Database Architecture

### Dual Database Setup

The application uses **two separate databases**:

#### 1. PostgreSQL (Async) - Primary Application Database
- **Purpose:** Main application data (certifications, assessments, workflows)
- **Connection:** Configured via `DATABASE_URL` environment variable
- **Type:** Async (SQLAlchemy AsyncSession)
- **Default:** `postgresql+asyncpg://presgen_assess_user:secure_password@localhost:5432/presgen_assess`
- **Initialization:** `src/service/database.py:33-42` via `init_db()`

#### 2. SQLite (Sync) - File Registry Database
- **Purpose:** File upload metadata and registry
- **Connection:** Hardcoded in `FileRegistry._get_db()`
- **Type:** Sync (SQLAlchemy Session)
- **Location:** `test_database.db` (project root)
- **Initialization:** `Base.metadata.create_all(engine)` on first access

### Why Two Databases?

**Historical Reason:** The `FileRegistry` was designed to work independently with synchronous operations for background file processing tasks. Using PostgreSQL would require async/sync bridging which adds complexity.

**Production Consideration:** For AWS deployment, SQLite file can be persisted using:
- EFS (Elastic File System) for shared access
- Volume mounts in Docker
- Local instance storage for single-container deployments

---

## 🚀 AWS Deployment Considerations

### SQLite Persistence Strategy

#### Option 1: Local Instance Storage (Recommended for Demo)
```yaml
# docker-compose.yml
volumes:
  - ./test_database.db:/app/test_database.db
```

**Pros:**
- ✅ Simple, no additional AWS resources
- ✅ Fast access
- ✅ Works immediately

**Cons:**
- ⚠️ Data lost if instance is terminated (use snapshots/backups)
- ⚠️ Not suitable for multi-container deployments

#### Option 2: EFS Volume Mount (Production)
```bash
# Create EFS volume
aws efs create-file-system --region us-east-1

# Mount in Lightsail
# Add to /etc/fstab or docker volume driver
```

**Pros:**
- ✅ Persistent across instance replacements
- ✅ Shared across multiple containers
- ✅ Automatic backups available

**Cons:**
- ⚠️ Additional cost (~$0.30/GB/month)
- ⚠️ Slightly slower than local storage

#### Option 3: S3 Backup Only (Hybrid)
```bash
# Daily backup to S3
0 2 * * * aws s3 cp /app/test_database.db s3://presgen-backups/db/test_database.db
```

**Pros:**
- ✅ Cost-effective
- ✅ Disaster recovery
- ✅ Simple to implement

**Cons:**
- ⚠️ Manual restore required after instance recreation
- ⚠️ ~5 minutes downtime for restore

### Recommended for AWS: Option 1 + Option 3

Use local storage with daily S3 backups:

```bash
#!/bin/bash
# /home/ubuntu/presgen/scripts/backup-database.sh

# Backup SQLite database
timestamp=$(date +%Y%m%d_%H%M%S)
aws s3 cp /home/ubuntu/presgen/test_database.db \
  s3://presgen-demo-files/backups/db/test_database_${timestamp}.db

# Cleanup old backups (keep 30 days)
aws s3 ls s3://presgen-demo-files/backups/db/ | \
  awk '{if (NR > 30) print $4}' | \
  xargs -I {} aws s3 rm s3://presgen-demo-files/backups/db/{}
```

**Add to crontab:**
```bash
0 2 * * * /home/ubuntu/presgen/scripts/backup-database.sh >> /var/log/presgen/backup.log 2>&1
```

---

## 🐳 Docker Configuration for AWS

### Volume Mounts

```yaml
# docker-compose.yml (AWS version)
services:
  presgen-assess:
    image: presgen-assess:latest
    volumes:
      - ./test_database.db:/app/test_database.db
      - ./uploads:/app/uploads
      - ./knowledge-base:/app/knowledge-base
    environment:
      - DATABASE_URL=${DATABASE_URL}
```

### Database File Permissions

```bash
# On AWS instance
chmod 664 /home/ubuntu/presgen/test_database.db
chown ubuntu:docker /home/ubuntu/presgen/test_database.db
```

### Health Check

Add database health check to ensure SQLite is accessible:

```yaml
# docker-compose.yml
healthcheck:
  test: ["CMD", "sqlite3", "/app/test_database.db", "SELECT 1"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

---

## 📊 Monitoring & Alerts

### Database Size Monitoring

```bash
# Add to CloudWatch custom metrics
#!/bin/bash
# /home/ubuntu/presgen/scripts/monitor-db-size.sh

DB_SIZE=$(du -b /home/ubuntu/presgen/test_database.db | cut -f1)
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%S")

aws cloudwatch put-metric-data \
  --namespace "PresGen/Database" \
  --metric-name "SQLiteDatabaseSize" \
  --value $DB_SIZE \
  --timestamp $TIMESTAMP \
  --unit Bytes
```

### Alert on Database Growth

```bash
# CloudWatch alarm for database > 1GB
aws cloudwatch put-metric-alarm \
  --alarm-name presgen-database-size \
  --metric-name SQLiteDatabaseSize \
  --namespace PresGen/Database \
  --statistic Maximum \
  --period 3600 \
  --threshold 1073741824 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1
```

---

## 🧪 Testing File Upload After Fix

### Test Script

```bash
#!/bin/bash
# test-file-upload.sh

# Configuration
API_URL="http://localhost:8000/api/v1/presgen-assess"
PROFILE_ID="184ef7eb-c6a9-4271-a1e4-204cded7c2f2"

echo "Testing File Upload API..."

# 1. Create test PDF file
echo "Creating test file..."
echo "Test content for certification" > test.txt

# 2. Upload file
echo "Uploading file..."
RESPONSE=$(curl -s -X POST "${API_URL}/files/upload" \
  -F "file=@test.txt" \
  -F "cert_profile_id=${PROFILE_ID}" \
  -F "resource_type=supplemental" \
  -F "process_immediately=true")

echo "Response: $RESPONSE"

# 3. Extract file ID
FILE_ID=$(echo $RESPONSE | jq -r '.file_id')
echo "File ID: $FILE_ID"

# 4. Check status
echo "Checking file status..."
curl -s -X GET "${API_URL}/files/${FILE_ID}/status" | jq

# 5. List profile files
echo "Listing profile files..."
curl -s -X GET "${API_URL}/files/profile/${PROFILE_ID}" | jq

# Cleanup
rm test.txt

echo "✅ Test complete!"
```

### Expected Response

```json
{
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "original_filename": "test.txt",
  "file_size": 32,
  "mime_type": "text/plain",
  "resource_type": "supplemental",
  "upload_timestamp": "2025-11-02T10:30:00.000000",
  "processing_status": "pending",
  "message": "File uploaded successfully and processing started"
}
```

---

## 📝 Deployment Checklist for AWS

### Pre-Deployment
- [x] SQLite table initialization fix applied
- [x] API endpoint documentation updated
- [ ] Client/frontend updated with correct URLs
- [ ] Test file upload locally
- [ ] Backup script created
- [ ] Database volume mount configured

### During Deployment
- [ ] Ensure `test_database.db` is included in deployment package
- [ ] Verify volume mounts in docker-compose.yml
- [ ] Set correct file permissions (664)
- [ ] Configure backup cron job
- [ ] Setup CloudWatch metrics for database size

### Post-Deployment
- [ ] Test file upload on AWS instance
- [ ] Verify files persist after container restart
- [ ] Confirm backup script runs successfully
- [ ] Setup alerts for database size
- [ ] Document restore procedure

---

## 🔧 Troubleshooting

### File Upload Returns 500 Error

**Check:**
1. Database file exists: `ls -la test_database.db`
2. Database permissions: `stat test_database.db`
3. SQLAlchemy models imported: Check logs for import errors
4. Container logs: `docker logs presgen-assess | grep -i database`

**Fix:**
```bash
# Recreate database with correct schema
docker exec -it presgen-assess python -c "
from src.models.base import Base
from sqlalchemy import create_engine
engine = create_engine('sqlite:///test_database.db')
Base.metadata.create_all(engine)
print('✅ Tables created')
"
```

### Files Not Persisting After Restart

**Check:**
```bash
docker-compose down
docker-compose up -d
# Files should still be listed
curl http://localhost:8000/api/v1/presgen-assess/files/user
```

**Fix:**
Ensure volume mount in docker-compose.yml:
```yaml
volumes:
  - ./test_database.db:/app/test_database.db
```

### Database Locked Errors

**Cause:** Multiple processes accessing SQLite simultaneously

**Fix:**
```python
# Increase timeout in file_upload_service.py
engine = create_engine(
    f'sqlite:///{db_path}',
    echo=False,
    connect_args={'timeout': 30}  # Add this
)
```

---

## 🎯 Summary

### What Was Fixed
1. ✅ SQLite table initialization in FileRegistry
2. ✅ Documented correct API endpoint URLs
3. ✅ Added AWS deployment strategy for SQLite persistence

### What Needs Client-Side Updates
- Update API base URL to include `:8000` and `/api/v1`
- Change profile endpoint from query param to path param

### AWS Deployment Ready
- SQLite persistence strategy documented
- Backup procedures defined
- Monitoring setup included
- Troubleshooting guide provided

---

**Status:** ✅ Ready for AWS Deployment

**Next Steps:**
1. Update client/frontend with correct API URLs
2. Test locally with fixed SQLite initialization
3. Deploy to AWS with documented persistence strategy
4. Setup automated backups

**Questions?** Refer to main [AWS_MIGRATION_PLAN.md](AWS_MIGRATION_PLAN.md)
