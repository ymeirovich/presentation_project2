# Phase 1 Quick Deployment Reference

**Status:** ✅ Ready to Deploy
**Commit:** `01527f6` (tag: `phase1-ready`)
**Time:** 30-45 minutes
**Risk:** Low

---

## Pre-Deployment (5 minutes)

```bash
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs

# 1. Backup database
docker-compose exec postgres pg_dump -U presgen presgen_assess > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Backup nginx config
docker-compose exec nginx cat /etc/nginx/nginx.conf > nginx.conf.backup

# 3. Verify you're on the right commit
git log -1 --oneline
# Should show: 01527f6 feat: Phase 1 - Fix course generation timeout and error handling
```

---

## Deployment (10 minutes)

```bash
# 1. Verify nginx config
docker-compose exec nginx nginx -t
# Expected: "syntax is ok"

# 2. Build updated image
docker-compose build presgen-assess

# 3. Deploy (rolling restart)
docker-compose up -d presgen-assess

# 4. Wait for startup
sleep 10

# 5. Reload nginx (no downtime)
docker-compose exec nginx nginx -s reload

# 6. Verify all services running
docker-compose ps
# All should show "Up"
```

---

## Verification (5 minutes)

```bash
# 1. Health check
curl -u demo:demo123 http://localhost/health
# Expected: "healthy"

# 2. Test course-status endpoint (should return 404, not 400/502/504)
curl -u demo:demo123 \
  'http://localhost/api/v1/workflows/00000000-0000-0000-0000-000000000000/skills/test/course-status' \
  -w "\nHTTP: %{http_code}\n"
# Expected: HTTP: 404

# 3. Watch logs for errors
docker-compose logs --tail=50 presgen-assess nginx | grep -E "ERROR|502|504"
# Should be clean
```

---

## Rollback (if needed)

```bash
# Quick rollback
git checkout HEAD~1
docker-compose build presgen-assess
docker-compose up -d presgen-assess
docker-compose cp nginx.conf.backup nginx:/etc/nginx/nginx.conf
docker-compose exec nginx nginx -s reload
```

---

## What Changed

| Component | Change | Impact |
|-----------|--------|--------|
| Backend | Returns HTTP 200 with failed status | No more 502 errors |
| Backend | Handles missing avatar job ID | No more 400 errors |
| Nginx | 35-minute timeout for course-status | No more 504 errors |
| Schema | Added error_message field | Better error messages |

---

## Monitoring (First 24 Hours)

```bash
# Watch for 504 errors
docker-compose logs nginx | grep -E "504|upstream timed out"

# Watch for application errors
docker-compose logs presgen-assess | grep -E "ERROR|CRITICAL"

# Watch course generation
tail -f logs/assess/course_generation.log
```

---

## Success Criteria

After deployment, you should see:

✅ No HTTP 400 "No avatar job ID found" errors
✅ No HTTP 502 errors when Core/Avatar fail
✅ No HTTP 504 nginx timeout errors
✅ Clear error messages in UI when generation fails
✅ Frontend stops polling after receiving failed status

---

## Full Documentation

- **Complete Plan:** [COURSE_GENERATION_FIX_PLAN.md](COURSE_GENERATION_FIX_PLAN.md)
- **Full Deployment Guide:** [PHASE_1_DEPLOYMENT_GUIDE.md](PHASE_1_DEPLOYMENT_GUIDE.md)
- **Implementation Details:** [PHASE_1_IMPLEMENTATION_SUMMARY.md](PHASE_1_IMPLEMENTATION_SUMMARY.md)

---

**Deployed by:** _________________
**Date:** _________________
**Issues:** _________________
