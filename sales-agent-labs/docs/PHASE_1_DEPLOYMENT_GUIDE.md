# Phase 1 Deployment Guide - Course Generation Timeout Fix

**Date:** 2025-11-09
**Phase:** 1 - Immediate Fixes
**Estimated Time:** 30-45 minutes
**Downtime Required:** ~5 minutes (rolling restart)

---

## Overview

This deployment implements Phase 1 fixes for course generation timeout issues:

### Changes Made

1. **PresGen-Core error handling** - Returns proper failed response instead of HTTP 502
2. **PresGen-Avatar error handling** - Returns proper failed response instead of HTTP 502
3. **Avatar job ID validation removed** - No more HTTP 400 when polling failed courses
4. **Nginx timeout extended** - Specific route for course-status with 35-minute timeout
5. **error_message field added** - CourseGenerationResponse schema includes user-friendly errors

### Expected Impact

✅ **Fixes:**
- No more HTTP 400 "No avatar job ID found" errors
- No more HTTP 502 errors when PresGen-Core/Avatar time out
- No more nginx 504 timeout errors for course-status endpoint
- User-friendly error messages displayed in UI
- Frontend properly detects failed status and stops polling

✅ **UX Improvements:**
- Clear error messages ("The presentation generation took longer than expected...")
- Proper failed state handling
- No confusing JavaScript errors

---

## Pre-Deployment Checklist

- [ ] Read this entire document
- [ ] Backup current database: `docker-compose exec postgres pg_dump -U presgen presgen_assess > backup_$(date +%Y%m%d_%H%M%S).sql`
- [ ] Tag current code: `git tag pre-phase1-deployment && git push origin pre-phase1-deployment`
- [ ] Backup nginx config: `docker-compose exec nginx cat /etc/nginx/nginx.conf > nginx.conf.backup`
- [ ] Review changes in Git: `git diff HEAD~5`
- [ ] Notify team of deployment window
- [ ] Have rollback plan ready (see below)

---

## Files Changed

### Backend
- `presgen-assess/src/schemas/gap_analysis.py` - Added `error_message` field to CourseGenerationResponse
- `presgen-assess/src/service/api/v1/endpoints/workflows.py` - Fixed error handling in poll_course_status

### Infrastructure
- `nginx/nginx.conf` - Added course-status specific location block with extended timeouts

### Tests
- `presgen-assess/tests/test_course_status_errors.py` - New test file (templates only)

---

## Deployment Steps

### Step 1: Verify Environment

```bash
# Ensure you're in the correct directory
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs

# Check current git branch
git branch

# Check running containers
docker-compose ps
```

### Step 2: Pull Latest Changes

```bash
# Ensure you have the latest code
git status
git log -3 --oneline

# Verify the changes are present
git diff HEAD~5 presgen-assess/src/service/api/v1/endpoints/workflows.py | head -50
```

### Step 3: Verify Nginx Configuration

```bash
# Test nginx configuration syntax
docker-compose exec nginx nginx -t

# Expected output: "syntax is ok" and "test is successful"
```

If the test fails, **STOP** and review the nginx configuration changes.

### Step 4: Build Updated Images

```bash
# Build presgen-assess with new code
docker-compose build presgen-assess

# This should show:
# - Building presgen-assess
# - Successfully built ...
# - Successfully tagged ...
```

### Step 5: Deploy (Rolling Restart)

```bash
# Restart presgen-assess service
docker-compose up -d presgen-assess

# Wait 5-10 seconds for service to start
sleep 10

# Verify service is healthy
docker-compose ps presgen-assess
docker-compose logs --tail=50 presgen-assess | grep -E "Started|ERROR|CRITICAL"
```

### Step 6: Reload Nginx Configuration

```bash
# Reload nginx WITHOUT restarting (no downtime)
docker-compose exec nginx nginx -s reload

# Verify no errors
docker-compose logs --tail=20 nginx
```

### Step 7: Verify Deployment

```bash
# Check all services are running
docker-compose ps

# Expected: All services should show "Up" status
```

---

## Post-Deployment Verification

### Test 1: Health Check

```bash
# Basic health check
curl -u demo:demo123 http://localhost/health

# Expected: "healthy"
```

### Test 2: API Responsiveness

```bash
# Test a simple API endpoint
curl -u demo:demo123 http://localhost/api/v1/workflows | jq '.'

# Should return JSON (not error)
```

### Test 3: Course Status Endpoint (with non-existent course)

```bash
# Test the course-status endpoint with a fake ID
# Should return 404, NOT 500/502/504
curl -u demo:demo123 \
  'http://localhost/api/v1/workflows/00000000-0000-0000-0000-000000000000/skills/test/course-status' \
  -w "\nHTTP Status: %{http_code}\n"

# Expected: HTTP Status: 404
# (NOT 400, 502, or 504)
```

### Test 4: Monitor Logs for Errors

```bash
# Watch logs for any errors (press Ctrl+C to stop)
docker-compose logs -f presgen-assess nginx | grep -E "ERROR|CRITICAL|500|502|504"

# Should not see any immediate errors
```

### Test 5: Real Course Generation (Optional)

If you have access to the UI:

1. Navigate to the dashboard
2. Click "Generate Course"
3. Monitor the browser console (F12)
4. Watch the network tab for API requests
5. Verify:
   - No HTTP 400/502/504 errors
   - If generation fails, error message is displayed clearly
   - Polling stops after receiving failed status

---

## Monitoring (First 24 Hours)

### What to Watch

1. **Nginx Access Logs** - Look for 504 errors
   ```bash
   docker-compose logs nginx | grep -E "504|upstream timed out"
   ```

2. **Application Errors** - Look for unhandled exceptions
   ```bash
   docker-compose logs presgen-assess | grep -E "ERROR|CRITICAL"
   ```

3. **Course Generation Logs**
   ```bash
   tail -f logs/assess/course_generation.log
   ```

### Expected Behavior

**Before Fix:**
```
CORE_ASYNC_FAILED | error=PresGen-Core request timed out
[nginx] upstream timed out reading response header
[frontend] ApiError: No avatar job ID found
```

**After Fix:**
```
CORE_ASYNC_FAILED | error=PresGen-Core request timed out | error_type=PresGenCoreTimeoutError
COURSE_STATUS_POLL | status=failed | progress=25
[frontend] Course generation failed: ... timed out. Please try again.
```

### Metrics to Track

| Metric | Before | Expected After |
|--------|--------|----------------|
| HTTP 400 errors/day | ~20 | 0 |
| HTTP 502 errors/day | ~30 | 0 |
| HTTP 504 errors/day | ~50 | 0 |
| Failed course generations | ~50% | ~50% (unchanged) |
| User-visible error messages | Broken | Clear |

---

## Rollback Procedures

### If Deployment Fails

**Option A: Quick Rollback (Recommended)**

```bash
# Step 1: Revert to previous Docker image
docker-compose down
git checkout HEAD~1
docker-compose build presgen-assess
docker-compose up -d

# Step 2: Restore nginx config
docker-compose cp nginx.conf.backup nginx:/etc/nginx/nginx.conf
docker-compose exec nginx nginx -s reload

# Step 3: Verify
docker-compose ps
docker-compose logs --tail=50 presgen-assess
```

**Option B: Full Rollback**

```bash
# Revert all changes
git revert HEAD
git push origin main

# Rebuild and restart
docker-compose build presgen-assess nginx
docker-compose up -d presgen-assess nginx

# Verify
docker-compose logs -f presgen-assess nginx
```

### If Database Issues Occur

```bash
# Restore database from backup
docker-compose exec -T postgres psql -U presgen presgen_assess < backup_<timestamp>.sql
```

---

## Known Issues & Limitations

### Issue 1: PresGen-Core Still Takes >10 Minutes

**Status:** Not fixed in Phase 1
**Impact:** Courses will still time out if Core takes >10 minutes
**Fix:** Phase 2 will optimize retry logic; Phase 3 will implement background workers

**Workaround:** Increase `PRESGEN_CORE_TIMEOUT_SECONDS` in environment:
```bash
# Add to .env file
PRESGEN_CORE_TIMEOUT_SECONDS=900  # 15 minutes
```

### Issue 2: Frontend May Still Show Old Error Messages

**Status:** Depends on UI bundle deployment
**Impact:** Old frontend bundle may not display new error_message field
**Fix:** Redeploy frontend: `docker-compose build presgen-ui && docker-compose up -d presgen-ui`

**Workaround:** Hard refresh browser: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)

### Issue 3: Long Blocking Time During Retries

**Status:** Not fixed in Phase 1
**Impact:** Endpoint still blocks for 20-30 minutes during retries
**Fix:** Phase 2 will reduce retry attempts; Phase 3 will use async workers

**Workaround:** Current nginx timeout (35 min) is set high enough to prevent 504s

---

## Success Criteria

After deployment, verify these conditions:

### Functional
- [ ] Course creation works
- [ ] Course status polling returns HTTP 200 (not 400/502/504)
- [ ] Failed courses return proper error messages
- [ ] Nginx doesn't timeout during long Core processing
- [ ] Frontend displays error messages clearly

### Performance
- [ ] No HTTP 400 errors in nginx logs
- [ ] No HTTP 502 errors in application logs
- [ ] No HTTP 504 errors in nginx logs
- [ ] Course status endpoint responds (even if slowly)

### UX
- [ ] Error messages are user-friendly
- [ ] No JavaScript console errors
- [ ] Polling stops after receiving failed status

---

## Next Steps

After successful Phase 1 deployment:

1. **Monitor for 24-48 hours** - Watch logs and metrics
2. **Gather feedback** - Check with users about error message clarity
3. **Plan Phase 2** - Backend optimizations (reduce retries, config tuning)
4. **Consider Phase 3** - Background worker implementation for long-term fix

---

## Troubleshooting

### Problem: Nginx won't reload

```bash
# Check nginx logs
docker-compose logs nginx | tail -50

# Check syntax
docker-compose exec nginx nginx -t

# If syntax error, restore backup
docker-compose cp nginx.conf.backup nginx:/etc/nginx/nginx.conf
docker-compose exec nginx nginx -s reload
```

### Problem: presgen-assess won't start

```bash
# Check logs
docker-compose logs presgen-assess | tail -100

# Common issues:
# 1. Import error - check Python syntax
# 2. Database connection - check DATABASE_URL
# 3. Port conflict - check if port 8000 is available

# Restart with verbose logging
docker-compose up presgen-assess
```

### Problem: Still seeing HTTP 400 errors

```bash
# Check the course status in database
docker-compose exec postgres psql -U presgen presgen_assess \
  -c "SELECT id, status, presgen_avatar_job_id, error_message FROM generated_courses WHERE status='failed' LIMIT 5;"

# Check if new code is deployed
docker-compose exec presgen-assess grep -n "error_message" /app/src/schemas/gap_analysis.py

# Should see line with: error_message: Optional[str] = Field(
```

### Problem: Still seeing HTTP 502 errors

```bash
# Verify exception handling is in place
docker-compose exec presgen-assess grep -A5 "PresGenCoreTimeoutError" /app/src/service/api/v1/endpoints/workflows.py

# Should see: "except Exception as e:" followed by error message logic
```

---

## Support

**Documentation:**
- Full plan: `docs/COURSE_GENERATION_FIX_PLAN.md`
- Architecture: See plan document Phase 1 section

**Logs:**
- Application: `docker-compose logs presgen-assess`
- Nginx: `docker-compose logs nginx`
- Course generation: `logs/assess/course_generation.log`

**Contacts:**
- Engineering team
- DevOps team

---

## Appendix: Environment Variables

No new environment variables required for Phase 1.

Optional (for Phase 2):
```bash
PRESGEN_CORE_TIMEOUT_SECONDS=900
PRESGEN_CORE_MAX_ATTEMPTS=2
PRESGEN_CORE_BACKOFF_SECONDS=3
```

---

## Sign-off

**Deployed by:** _________________
**Date:** _________________
**Rollback tested:** Yes / No
**Success criteria met:** Yes / No
**Issues encountered:** _________________

---

End of Deployment Guide
