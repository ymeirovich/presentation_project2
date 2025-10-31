# Database Migration Issue - Schema Out of Sync

## Problem Summary

The presgen-assess service is returning 500 errors on endpoints like `/api/v1/certifications` and `/api/v1/workflows` due to missing database columns.

## Symptoms

```
❌ Failed to list workflows: (sqlite3.OperationalError) no such column: workflow_executions.current_step
❌ Failed to list certification profiles: (sqlite3.OperationalError) no such column: certification_profiles.knowledge_base_path
```

## Root Cause

**Alembic migrations are out of sync with SQLAlchemy model definitions.**

The migrations run successfully but create an incomplete schema. The code models have evolved (added columns) but the migration files haven't been updated to match.

### Missing Columns

1. `workflow_executions.current_step` - Expected by WorkflowExecution model
2. `certification_profiles.knowledge_base_path` - Expected by CertificationProfile model
3. Possibly others

## What Was Attempted

1. ✅ **Created database backups**
   - `./backups/test_database.db.backup-20251031-160343` (236KB)
   - `./backups/test_database.db.backup-20251031-161324` (176KB - empty)

2. ✅ **Fixed DATABASE_URL configuration**
   - Changed from: `sqlite+aiosqlite:///./test_database.db` (temporary)
   - Changed to: docker-compose default `/app/data/presgen_assess.db` (persisted)
   - Modified: `.env` file - commented out DATABASE_URL line

3. ✅ **Deleted old incompatible database**
   - No data loss - database was empty (0 rows in all tables)

4. ✅ **Ran fresh migrations**
   ```
   INFO [alembic] Running upgrade  -> 8a37fe1f7ca9, Initial database schema
   INFO [alembic] Running upgrade 8a37fe1f7ca9 -> 005_chromadb_integration
   INFO [alembic] Running upgrade 005_chromadb_integration -> 006_gap_analysis
   INFO [alembic] Running upgrade 006_gap_analysis -> 007_presentations
   INFO [alembic] Running upgrade 007_presentations -> ce9ec16057c4
   INFO [alembic] Running upgrade ce9ec16057c4 -> 2af7dd294b0f
   INFO [alembic] Running upgrade 2af7dd294b0f -> 6c7d0d3a4b2b
   ```

5. ❌ **Result: Schema still incomplete**
   - Migrations claim success but columns are missing
   - Models expect columns that migrations didn't create

## Solution Options

### Option 1: Update Migrations (Recommended for Production)
Create new migration files to add the missing columns:

```bash
# Generate migration based on model changes
docker exec presgen-assess alembic revision --autogenerate -m "add_missing_columns"

# Review the generated migration
# Edit if needed to ensure it adds:
#   - workflow_executions.current_step
#   - certification_profiles.knowledge_base_path

# Apply migration
docker exec presgen-assess alembic upgrade head
```

### Option 2: Use SQLAlchemy create_all() (Quick Fix for Development)
Bypass migrations and create tables directly from models:

1. Modify `presgen-assess/src/service/database.py` or startup code
2. Add: `Base.metadata.create_all(bind=engine)`
3. This creates all tables with current model definitions
4. **Warning:** Not recommended for production - no migration history

### Option 3: Manual SQL (Not Recommended)
Manually add missing columns via SQL:

```sql
ALTER TABLE workflow_executions ADD COLUMN current_step VARCHAR(255);
ALTER TABLE certification_profiles ADD COLUMN knowledge_base_path TEXT;
```

## Recommended Next Steps

1. **Generate new migration** with Option 1 above
2. **Test locally** to verify schema matches models
3. **Verify endpoints** return empty arrays instead of 500 errors:
   ```bash
   curl -u demo:demo http://localhost/api/v1/certifications/
   # Should return: [] (empty array, not error)
   ```
4. **Commit migration** to version control
5. **Update deployment docs** with migration steps

## Current Workaround

The UI is currently functional except for these endpoints:
- ✅ Prompts endpoint works
- ✅ Voice profiles endpoint works
- ❌ Certifications endpoint returns 500
- ❌ Workflows endpoint returns 500

Since the database is empty anyway, the missing data endpoints don't block UI functionality - they just show empty states.

## Files Modified

- `.env` - Commented out `DATABASE_URL` line (not committed - file is gitignored)
- Created backups in `./backups/` directory

## Date

October 31, 2025 - 16:20
