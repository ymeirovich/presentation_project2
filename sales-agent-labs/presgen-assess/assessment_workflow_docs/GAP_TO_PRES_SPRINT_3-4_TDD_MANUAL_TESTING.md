# Sprint 3-4 TDD Manual Testing Guide
**Gap Analysis → Presentation Generation (Production Mode)**

_Last Updated: 2025-10-03_

---

## Overview

This guide provides step-by-step manual testing procedures for validating Sprint 3-4 implementation including:
- **Option 3**: API endpoint UUID fixes (status & list endpoints)
- **Option 1**: Production PresGen-Core integration (real Google Slides)
- **Option 2** (Optional): Avatar integration basics
- **Option 5**: End-to-end workflow validation

---

## Prerequisites

### Environment Setup
```bash
# 1. Ensure server is running
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/presgen-assess
source ../venv/bin/activate  # or ../.venv/bin/activate
uvicorn src.service.app:app --reload --port 8000

# 2. Verify database is accessible
sqlite3 test_database.db ".tables"

# 3. Check existing test data
sqlite3 test_database.db "SELECT id, status FROM workflow_executions ORDER BY created_at DESC LIMIT 3;"
```

### Test Data Preparation
```bash
# Get test workflow and course IDs
export TEST_WORKFLOW_ID="8e46398dc2924439a04531dfeb49d7ef"
export TEST_WORKFLOW_ID_HYPHENS="8e46398d-c292-4439-a045-31dfeb49d7ef"

# Get a completed presentation ID for testing
export TEST_PRES_ID=$(sqlite3 test_database.db "SELECT id FROM generated_presentations WHERE generation_status = 'completed' LIMIT 1;")

# Get course IDs for testing
export TEST_COURSE_ID_1="220f8b53c7b242a88eeb5f7ae08aff84"  # Networking
export TEST_COURSE_ID_2="f060300480de4308831e35cc0a89e0b8"  # Compute
```

---

## Test Suite 1: Option 3 - API Endpoint Fixes

### Test Case 1.1: Status Endpoint - Without Hyphens ✅

**Objective**: Verify status endpoint works with non-hyphenated UUIDs

**Steps**:
```bash
# 1. Get status for completed presentation (no hyphens)
curl -s "http://localhost:8000/api/v1/workflows/${TEST_WORKFLOW_ID}/presentations/${TEST_PRES_ID}/status" | python3 -m json.tool
```

**Expected Result**:
```json
{
  "job_id": "string",
  "presentation_id": "string",
  "status": "completed",
  "progress": 100,
  "current_step": "Progress: 100%",
  "error_message": null
}
```

**Validation**:
- ✅ HTTP 200 response
- ✅ Returns valid JSON
- ✅ `status` field = "completed"
- ✅ `progress` field = 100
- ✅ No error message

---

### Test Case 1.2: Status Endpoint - With Hyphens ✅

**Objective**: Verify status endpoint works with hyphenated UUIDs

**Steps**:
```bash
# 1. Format presentation ID with hyphens
PRES_ID_HYPHENS=$(echo $TEST_PRES_ID | sed 's/^\(........\)\(....\)\(....\)\(....\)\(............\)$/\1-\2-\3-\4-\5/')

# 2. Get status using hyphenated IDs
curl -s "http://localhost:8000/api/v1/workflows/${TEST_WORKFLOW_ID_HYPHENS}/presentations/${PRES_ID_HYPHENS}/status" | python3 -m json.tool
```

**Expected Result**:
- Same as Test Case 1.1
- Both hyphenated and non-hyphenated formats work identically

**Validation**:
- ✅ HTTP 200 response
- ✅ Returns same data as non-hyphenated version
- ✅ No format-related errors

---

### Test Case 1.3: List Endpoint - All Presentations ✅

**Objective**: Verify list endpoint returns all presentations for workflow

**Steps**:
```bash
# 1. List presentations (no hyphens)
curl -s "http://localhost:8000/api/v1/workflows/${TEST_WORKFLOW_ID}/presentations" | python3 -m json.tool > /tmp/list_no_hyphens.json

# 2. List presentations (with hyphens)
curl -s "http://localhost:8000/api/v1/workflows/${TEST_WORKFLOW_ID_HYPHENS}/presentations" | python3 -m json.tool > /tmp/list_with_hyphens.json

# 3. Compare results
diff /tmp/list_no_hyphens.json /tmp/list_with_hyphens.json
```

**Expected Result**:
```json
{
  "workflow_id": "string",
  "presentations": [
    {
      "id": "string",
      "skill_name": "string",
      "generation_status": "completed",
      "presentation_url": "https://docs.google.com/...",
      "total_slides": 7-11,
      ...
    }
  ],
  "total_count": 3,
  "completed_count": 3,
  "pending_count": 0,
  "generating_count": 0,
  "failed_count": 0
}
```

**Validation**:
- ✅ Returns presentation array (not empty)
- ✅ Count fields accurate
- ✅ Both UUID formats return identical results
- ✅ All presentation fields populated

---

### Test Case 1.4: Get Single Presentation Details ✅

**Objective**: Verify new GET endpoint returns complete presentation data

**Steps**:
```bash
# Get detailed presentation info
curl -s "http://localhost:8000/api/v1/workflows/${TEST_WORKFLOW_ID_HYPHENS}/presentations/${PRES_ID_HYPHENS}" | python3 -m json.tool
```

**Expected Result**:
- Returns full presentation object with all 30 fields
- Includes URLs, timestamps, drive paths, etc.

**Validation**:
- ✅ HTTP 200 response
- ✅ `presentation_url` populated
- ✅ `drive_folder_path` populated
- ✅ `total_slides` between 7-11
- ✅ All timestamp fields present

---

### Test Case 1.5: Error Handling - Invalid UUID ✅

**Objective**: Verify proper error handling for invalid presentation IDs

**Steps**:
```bash
# 1. Test with invalid presentation ID
curl -s "http://localhost:8000/api/v1/workflows/${TEST_WORKFLOW_ID}/presentations/invalid-id-12345/status" | python3 -m json.tool

# 2. Test with non-existent workflow
curl -s "http://localhost:8000/api/v1/workflows/00000000000000000000000000000000/presentations" | python3 -m json.tool
```

**Expected Result**:
```json
{
  "detail": "Presentation invalid-id-12345 not found"
}
```

**Validation**:
- ✅ HTTP 404 response
- ✅ Error message is clear and specific
- ✅ No 500 internal server errors
- ✅ JSON response format maintained

---

## Test Suite 2: Option 1 - Production PresGen-Core Integration

### Pre-Implementation Checklist

**Before starting**:
```bash
# 1. Verify PresGen-Core is running
curl http://localhost:8001/health
# Expected: {"status": "healthy"} or similar

# 2. Check Google credentials exist
ls -la ~/Documents/learn/presentation_project/sales-agent-labs/presgen-service-account2.json
ls -la ~/Documents/learn/presentation_project/sales-agent-labs/token.json

# 3. Verify .env configuration
cat .env | grep -E "PRESGEN_CORE_URL|GOOGLE_APPLICATION_CREDENTIALS"
```

---

### Test Case 2.1: Mock Mode Baseline ✅

**Objective**: Establish baseline before switching to production mode

**Steps**:
```bash
# 1. Generate presentation in mock mode
curl -X POST "http://localhost:8000/api/v1/workflows/${TEST_WORKFLOW_ID}/courses/${TEST_COURSE_ID_2}/generate-presentation" \
  -H "Content-Type: application/json" \
  -d "{
    \"workflow_id\": \"${TEST_WORKFLOW_ID}\",
    \"course_id\": \"${TEST_COURSE_ID_2}\",
    \"custom_title\": \"Mock Mode Baseline Test\"
  }" | python3 -m json.tool

# 2. Monitor completion (should be fast in mock mode)
watch -n 2 'sqlite3 test_database.db "SELECT generation_status, job_progress FROM generated_presentations ORDER BY created_at DESC LIMIT 1;"'
```

**Expected Result**:
- ✅ Completes in 1-2 seconds
- ✅ Status: completed
- ✅ Progress: 100%
- ✅ Mock URLs generated

**Record Baseline**:
```bash
sqlite3 test_database.db "SELECT skill_name, generation_duration_ms, total_slides, presentation_url FROM generated_presentations ORDER BY created_at DESC LIMIT 1;"
```

---

### Test Case 2.2: Production Mode - Single Presentation ✅

**Objective**: Generate real Google Slides presentation using PresGen-Core

**Steps**:
```bash
# 1. Verify mock mode is disabled
grep "use_mock" src/service/presgen_core_client.py

# 2. Generate presentation (PRODUCTION MODE)
curl -X POST "http://localhost:8000/api/v1/workflows/${TEST_WORKFLOW_ID}/courses/${TEST_COURSE_ID_1}/generate-presentation" \
  -H "Content-Type: application/json" \
  -d "{
    \"workflow_id\": \"${TEST_WORKFLOW_ID}\",
    \"course_id\": \"${TEST_COURSE_ID_1}\",
    \"custom_title\": \"AWS Networking Fundamentals - Production Test\"
  }" | python3 -m json.tool > /tmp/production_pres_response.json

# 3. Extract presentation ID
PROD_PRES_ID=$(cat /tmp/production_pres_response.json | python3 -c "import json, sys; print(json.load(sys.stdin)['presentation_id'])")

# 4. Monitor progress (will take 3-7 minutes)
watch -n 10 "sqlite3 test_database.db \"SELECT generation_status, job_progress, generation_duration_ms/1000.0 as elapsed_seconds FROM generated_presentations WHERE id = '$PROD_PRES_ID';\""
```

**Expected Result**:
- ✅ Generation takes 3-7 minutes (180-420 seconds)
- ✅ Status progresses: pending → generating → completed
- ✅ Progress updates: 0% → 20% → 80% → 100%
- ✅ Real Google Slides URL generated

**Validation**:
```bash
# Check final presentation
sqlite3 test_database.db "SELECT presentation_url, drive_file_id, total_slides, generation_duration_ms/1000.0 as duration_sec FROM generated_presentations WHERE id = '$PROD_PRES_ID';"

# Open in browser to verify it's real
PRES_URL=$(sqlite3 test_database.db "SELECT presentation_url FROM generated_presentations WHERE id = '$PROD_PRES_ID';")
echo "Open this URL: $PRES_URL"
```

**Success Criteria**:
- ✅ Presentation URL is actual Google Slides document
- ✅ Can open and view in browser
- ✅ Slide count between 7-11
- ✅ Content is relevant to skill (Networking)
- ✅ No timeout errors

---

### Test Case 2.3: Production Mode - Error Handling ✅

**Objective**: Verify error handling for production failures

**Steps**:
```bash
# 1. Test with invalid/empty title
curl -X POST "http://localhost:8000/api/v1/workflows/${TEST_WORKFLOW_ID}/courses/${TEST_COURSE_ID_1}/generate-presentation" \
  -H "Content-Type: application/json" \
  -d "{
    \"workflow_id\": \"${TEST_WORKFLOW_ID}\",
    \"course_id\": \"${TEST_COURSE_ID_1}\",
    \"custom_title\": \"\"
  }" | python3 -m json.tool

# 2. Check error is recorded properly
sqlite3 test_database.db "SELECT generation_status, job_error_message FROM generated_presentations ORDER BY created_at DESC LIMIT 1;"
```

**Expected Result**:
- ✅ HTTP 400 or 422 validation error (not 500)
- ✅ Clear error message returned
- ✅ Database record shows 'failed' status if created
- ✅ Error message populated in job_error_message field

---

### Test Case 2.4: Production Mode - Drive Folder Organization ✅

**Objective**: Verify Google Drive folder structure is correct

**Steps**:
```bash
# 1. Check drive folder paths
sqlite3 test_database.db "SELECT skill_name, drive_folder_path, drive_file_id FROM generated_presentations WHERE id = '$PROD_PRES_ID';"

# 2. Expected path format
# Assessments/gap_analysis_complete_[workflow_id]/Presentations/[skill_name]/
```

**Validation**:
- ✅ Navigate to Google Drive manually
- ✅ Confirm folder structure exists
- ✅ Presentation is in correct folder
- ✅ Folder naming matches assessment title + workflow context

---

### Test Case 2.5: Production vs Mock Performance Comparison 📊

**Objective**: Compare production vs mock mode performance

**Steps**:
```bash
# Generate comparison report
sqlite3 test_database.db "
SELECT
    CASE
        WHEN presentation_url LIKE '%mock%' THEN 'Mock Mode'
        ELSE 'Production Mode'
    END as mode,
    COUNT(*) as presentations,
    ROUND(AVG(generation_duration_ms)/1000.0, 1) as avg_duration_sec,
    ROUND(MIN(generation_duration_ms)/1000.0, 1) as min_duration_sec,
    ROUND(MAX(generation_duration_ms)/1000.0, 1) as max_duration_sec,
    ROUND(AVG(total_slides), 1) as avg_slides
FROM generated_presentations
WHERE generation_status = 'completed'
GROUP BY mode;
"
```

**Expected Result**:
```
Mode             | presentations | avg_duration_sec | min | max | avg_slides
-----------------+---------------+------------------+-----+-----+-----------
Mock Mode        | 3             | 1.2              | 1.0 | 1.5 | 8.7
Production Mode  | 1             | 240.0            | 240 | 240 | 9.0
```

**Success Criteria**:
- ✅ Production mode: 180-420 seconds average
- ✅ Mock mode: 1-2 seconds average
- ✅ Both produce similar slide counts (7-11)

---

## Test Suite 3: Batch Generation & Parallel Jobs

### Test Case 3.1: Batch Generation - All Skills ✅

**Objective**: Verify batch generation creates multiple presentations in parallel

**Steps**:
```bash
# 1. Count existing presentations
BEFORE_COUNT=$(sqlite3 test_database.db "SELECT COUNT(*) FROM generated_presentations WHERE workflow_id = '$TEST_WORKFLOW_ID';")

# 2. Trigger batch generation
curl -X POST "http://localhost:8000/api/v1/workflows/${TEST_WORKFLOW_ID}/generate-all-presentations" \
  -H "Content-Type: application/json" \
  -d "{
    \"workflow_id\": \"${TEST_WORKFLOW_ID_HYPHENS}\",
    \"max_concurrent\": 3
  }" | python3 -m json.tool > /tmp/batch_response.json

# 3. Monitor parallel execution
watch -n 5 "sqlite3 test_database.db \"
SELECT
    skill_name,
    generation_status,
    job_progress,
    ROUND(generation_duration_ms/1000.0, 1) as elapsed_sec
FROM generated_presentations
WHERE workflow_id = '$TEST_WORKFLOW_ID'
ORDER BY created_at DESC
LIMIT 5;
\""

# 4. Wait for completion
while true; do
    COMPLETED=$(sqlite3 test_database.db "SELECT COUNT(*) FROM generated_presentations WHERE workflow_id = '$TEST_WORKFLOW_ID' AND generation_status = 'completed';")
    AFTER_COUNT=$(sqlite3 test_database.db "SELECT COUNT(*) FROM generated_presentations WHERE workflow_id = '$TEST_WORKFLOW_ID';")
    NEW_COUNT=$((AFTER_COUNT - BEFORE_COUNT))

    echo "Progress: $COMPLETED / $NEW_COUNT presentations completed"

    if [ "$COMPLETED" -eq "$AFTER_COUNT" ]; then
        echo "✅ All presentations complete!"
        break
    fi

    sleep 10
done
```

**Expected Result**:
- ✅ Multiple presentations start simultaneously
- ✅ max_concurrent=3 limits parallel executions
- ✅ All presentations complete successfully
- ✅ No failed jobs

**Validation**:
```bash
# Check batch results
sqlite3 test_database.db "
SELECT
    skill_name,
    total_slides,
    ROUND(generation_duration_ms/1000.0, 1) as duration_sec,
    generation_status
FROM generated_presentations
WHERE workflow_id = '$TEST_WORKFLOW_ID'
AND created_at > datetime('now', '-10 minutes')
ORDER BY created_at DESC;
"
```

---

### Test Case 3.2: Concurrent Job Isolation ✅

**Objective**: Verify jobs don't interfere with each other

**Steps**:
```bash
# 1. Generate presentations for different workflows concurrently
# (If you have multiple test workflows)

# 2. Check for any cross-contamination
sqlite3 test_database.db "
SELECT
    workflow_id,
    COUNT(*) as presentations,
    COUNT(DISTINCT skill_name) as unique_skills,
    SUM(CASE WHEN generation_status = 'completed' THEN 1 ELSE 0 END) as completed
FROM generated_presentations
GROUP BY workflow_id;
"
```

**Expected Result**:
- ✅ Each workflow has its own presentations
- ✅ No presentation records with wrong workflow_id
- ✅ Database session isolation working correctly

---

## Test Suite 4: End-to-End Workflow Validation

### Test Case 4.1: Data Consistency Check ✅

**Objective**: Verify referential integrity across all tables

**Steps**:
```bash
# 1. Check gap analysis → courses mapping
sqlite3 test_database.db "
SELECT
    ga.skill_name,
    COUNT(DISTINCT rc.id) as course_count,
    COUNT(DISTINCT gp.id) as presentation_count
FROM gap_analysis ga
LEFT JOIN recommended_courses rc ON ga.skill_id = rc.skill_id AND ga.workflow_id = rc.workflow_id
LEFT JOIN generated_presentations gp ON rc.id = gp.course_id
WHERE ga.workflow_id = '$TEST_WORKFLOW_ID'
GROUP BY ga.skill_name;
"

# 2. Check for orphaned records
sqlite3 test_database.db "
SELECT 'Orphaned Presentations' as check_type, COUNT(*) as count
FROM generated_presentations gp
LEFT JOIN recommended_courses rc ON gp.course_id = rc.id
WHERE rc.id IS NULL

UNION ALL

SELECT 'Presentations Missing URLs', COUNT(*)
FROM generated_presentations
WHERE generation_status = 'completed' AND presentation_url IS NULL;
"
```

**Expected Result**:
- ✅ Every gap has ≥1 course
- ✅ Every course has ≤1 presentation
- ✅ No orphaned records
- ✅ All completed presentations have URLs

---

### Test Case 4.2: Workflow Timeline Verification ✅

**Objective**: Verify logical flow of timestamps

**Steps**:
```bash
# Check workflow progression timeline
sqlite3 test_database.db "
SELECT
    'Workflow Created' as stage,
    created_at as timestamp
FROM workflow_executions
WHERE id = '$TEST_WORKFLOW_ID'

UNION ALL

SELECT
    'Gap Analysis Complete',
    MAX(created_at)
FROM gap_analysis
WHERE workflow_id = '$TEST_WORKFLOW_ID'

UNION ALL

SELECT
    'Courses Recommended',
    MAX(created_at)
FROM recommended_courses
WHERE workflow_id = '$TEST_WORKFLOW_ID'

UNION ALL

SELECT
    'Presentations Started',
    MIN(generation_started_at)
FROM generated_presentations
WHERE workflow_id = '$TEST_WORKFLOW_ID'

UNION ALL

SELECT
    'Presentations Completed',
    MAX(generation_completed_at)
FROM generated_presentations
WHERE workflow_id = '$TEST_WORKFLOW_ID'

ORDER BY timestamp;
"
```

**Expected Result**:
- ✅ Timestamps in logical order
- ✅ No future timestamps
- ✅ Reasonable duration between stages

---

## Test Suite 5: Regression Testing

### Test Case 5.1: Existing Data Integrity ✅

**Objective**: Ensure new code doesn't corrupt existing data

**Steps**:
```bash
# 1. Check old presentations still accessible
sqlite3 test_database.db "
SELECT
    id,
    skill_name,
    generation_status,
    created_at
FROM generated_presentations
WHERE created_at < datetime('now', '-1 day')
LIMIT 5;
"

# 2. Verify old presentations via API
OLD_PRES_ID=$(sqlite3 test_database.db "SELECT id FROM generated_presentations WHERE created_at < datetime('now', '-1 day') LIMIT 1;")

if [ ! -z "$OLD_PRES_ID" ]; then
    curl -s "http://localhost:8000/api/v1/workflows/${TEST_WORKFLOW_ID}/presentations/${OLD_PRES_ID}/status" | python3 -m json.tool
fi
```

**Expected Result**:
- ✅ Old presentations still retrievable
- ✅ No data corruption in existing records
- ✅ API endpoints work for historical data

---

### Test Case 5.2: Server Restart Resilience ✅

**Objective**: Verify behavior after server restart

**Steps**:
```bash
# 1. Record current state
PRES_COUNT_BEFORE=$(sqlite3 test_database.db "SELECT COUNT(*) FROM generated_presentations;")

# 2. Restart server (Ctrl+C and restart uvicorn)
# Kill and restart manually

# 3. Check data after restart
PRES_COUNT_AFTER=$(sqlite3 test_database.db "SELECT COUNT(*) FROM generated_presentations;")

echo "Before: $PRES_COUNT_BEFORE, After: $PRES_COUNT_AFTER"

# 4. Test API after restart
curl -s "http://localhost:8000/api/v1/workflows/${TEST_WORKFLOW_ID}/presentations" | python3 -c "import json, sys; print(json.load(sys.stdin)['total_count'])"
```

**Expected Result**:
- ✅ Data persists across restarts
- ✅ API endpoints functional immediately
- ⚠️ In-memory job queue cleared (expected limitation)

---

## Test Suite 6: Performance & Load Testing

### Test Case 6.1: Response Time Benchmarks 📊

**Objective**: Establish performance baselines

**Steps**:
```bash
# 1. Status endpoint performance
time curl -s "http://localhost:8000/api/v1/workflows/${TEST_WORKFLOW_ID}/presentations/${TEST_PRES_ID}/status" > /dev/null

# 2. List endpoint performance
time curl -s "http://localhost:8000/api/v1/workflows/${TEST_WORKFLOW_ID}/presentations" > /dev/null

# 3. Generation endpoint (async - just submission)
time curl -s -X POST "http://localhost:8000/api/v1/workflows/${TEST_WORKFLOW_ID}/courses/${TEST_COURSE_ID_1}/generate-presentation" \
  -H "Content-Type: application/json" \
  -d "{\"workflow_id\": \"${TEST_WORKFLOW_ID}\", \"course_id\": \"${TEST_COURSE_ID_1}\"}" > /dev/null
```

**Expected Result**:
- ✅ Status endpoint: <200ms
- ✅ List endpoint: <500ms (depends on presentation count)
- ✅ Generation submission: <100ms (async, returns immediately)

---

### Test Case 6.2: Database Growth Analysis 📊

**Objective**: Monitor database size and growth patterns

**Steps**:
```bash
# 1. Check current database size
du -h test_database.db

# 2. Table sizes
sqlite3 test_database.db "
SELECT
    name as table_name,
    CAST(SUM(pgsize) / 1024.0 AS INTEGER) as size_kb
FROM dbstat
WHERE name IN (
    'workflow_executions',
    'gap_analysis',
    'recommended_courses',
    'generated_presentations'
)
GROUP BY name
ORDER BY size_kb DESC;
"

# 3. Record count per table
sqlite3 test_database.db "
SELECT 'workflow_executions' as table_name, COUNT(*) as records FROM workflow_executions
UNION ALL
SELECT 'gap_analysis', COUNT(*) FROM gap_analysis
UNION ALL
SELECT 'recommended_courses', COUNT(*) FROM recommended_courses
UNION ALL
SELECT 'generated_presentations', COUNT(*) FROM generated_presentations;
"
```

**Expected Result**:
- ✅ Database size reasonable (<50MB for dev/testing)
- ✅ ~500KB per workflow
- ✅ ~50KB per presentation

---

## Test Summary & Reporting

### Generate Comprehensive Test Report

```bash
# Create test summary
cat > /tmp/sprint_3_4_test_report.md << 'EOF'
# Sprint 3-4 Testing Report

**Date**: $(date '+%Y-%m-%d %H:%M:%S')
**Tester**: [Your Name]
**Environment**: Development

## Test Results Summary

### Option 3: API Endpoint Fixes
- Test Case 1.1 (Status - No Hyphens): ✅ PASS
- Test Case 1.2 (Status - With Hyphens): ✅ PASS
- Test Case 1.3 (List Endpoint): ✅ PASS
- Test Case 1.4 (Get Single): ✅ PASS
- Test Case 1.5 (Error Handling): ✅ PASS

### Option 1: Production PresGen-Core
- Test Case 2.1 (Mock Baseline): ✅ PASS
- Test Case 2.2 (Production Single): ✅ PASS
- Test Case 2.3 (Error Handling): ✅ PASS
- Test Case 2.4 (Drive Organization): ✅ PASS
- Test Case 2.5 (Performance): ✅ PASS

### Batch & Parallel
- Test Case 3.1 (Batch Generation): ✅ PASS
- Test Case 3.2 (Job Isolation): ✅ PASS

### E2E & Regression
- Test Case 4.1 (Data Consistency): ✅ PASS
- Test Case 4.2 (Workflow Timeline): ✅ PASS
- Test Case 5.1 (Existing Data): ✅ PASS
- Test Case 5.2 (Server Restart): ✅ PASS

### Performance
- Test Case 6.1 (Response Times): ✅ PASS
- Test Case 6.2 (Database Growth): ✅ PASS

## Overall Status: ✅ PASS

### Issues Found
- [List any issues]

### Next Steps
- [List recommendations]

EOF

cat /tmp/sprint_3_4_test_report.md
```

---

## Rollback Procedures

### If Tests Fail: Immediate Rollback

```bash
# 1. Revert code changes
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/presgen-assess
git log --oneline -5  # Find last good commit
git checkout [COMMIT_HASH] -- src/service/api/v1/endpoints/presentations.py
git checkout [COMMIT_HASH] -- src/service/presgen_core_client.py

# 2. Restart server
# Ctrl+C to stop
uvicorn src.service.app:app --reload --port 8000

# 3. Verify rollback successful
curl -s "http://localhost:8000/api/v1/workflows/${TEST_WORKFLOW_ID}/presentations" | python3 -c "import json, sys; print('Rollback OK' if 'presentations' in json.load(sys.stdin) else 'Rollback Failed')"
```

### Clean Test Data (Optional)

```bash
# Remove test presentations created during testing
sqlite3 test_database.db "DELETE FROM generated_presentations WHERE created_at > datetime('now', '-1 hour');"

# Verify cleanup
sqlite3 test_database.db "SELECT COUNT(*) FROM generated_presentations;"
```

---

## Success Criteria Checklist

### Sprint 3-4 Complete When:

- ✅ All Test Suite 1 cases pass (API endpoints)
- ✅ All Test Suite 2 cases pass (Production PresGen-Core)
- ✅ At least 1 real Google Slides presentation generated
- ✅ Batch generation creates multiple presentations successfully
- ✅ Data consistency verified across all tables
- ✅ Performance within acceptable ranges
- ✅ No regression in existing functionality
- ✅ Error handling works for all failure scenarios
- ✅ Documentation updated with test results

---

## Appendix: Quick Reference Commands

```bash
# Check server status
curl http://localhost:8000/health

# View recent presentations
sqlite3 test_database.db "SELECT skill_name, generation_status, job_progress FROM generated_presentations ORDER BY created_at DESC LIMIT 5;"

# Monitor active jobs
watch -n 3 'sqlite3 test_database.db "SELECT COUNT(*), generation_status FROM generated_presentations WHERE created_at > datetime('now', '-10 minutes') GROUP BY generation_status;"'

# Check logs
tail -f logs/presgen_assess.log | grep -E "(ERROR|PresGen|generation)"

# Clear stuck jobs (if needed)
sqlite3 test_database.db "UPDATE generated_presentations SET generation_status = 'failed', job_error_message = 'Manually cleared - stuck job' WHERE generation_status IN ('pending', 'generating') AND created_at < datetime('now', '-1 hour');"
```

---

**End of TDD Manual Testing Guide**
