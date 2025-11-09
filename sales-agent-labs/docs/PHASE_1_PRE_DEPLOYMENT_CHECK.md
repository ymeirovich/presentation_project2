# Phase 1 Pre-Deployment System Check

**Run this before deploying Phase 1**

---

## Current System Status

### Services Check

```bash
docker-compose ps
```

**Expected Output:**
- ✅ presgen-assess: Up (healthy)
- ✅ presgen-core: Up (healthy)
- ✅ presgen-nginx: Up (healthy)
- ✅ presgen-redis: Up (healthy)
- ⚠️ presgen-ui: Up (unhealthy) - **KNOWN ISSUE, safe to ignore**
- ⚠️ presgen-avatar: Up (unhealthy) - **Check logs if needed**

### Known Issues

#### presgen-ui "unhealthy" status
**Status:** Safe to ignore
**Reason:** Health check tries to connect to localhost:3000 but Next.js binds to 0.0.0.0:3000
**Impact:** None - UI is accessible through nginx
**Verification:**
```bash
curl -s http://localhost/health
# Should return: healthy
```

#### presgen-avatar "unhealthy" status
**Status:** Check logs
**Reason:** May have actual issues or similar health check config problem
**Verification:**
```bash
docker-compose logs --tail=20 presgen-avatar
```

---

## Pre-Deployment Checklist

### 1. System Health

```bash
# Overall health
curl -s http://localhost/health
# Expected: "healthy"

# API responsive
curl -s http://localhost/api/v1/workflows | head -5
# Should return JSON (even if auth required)

# Database accessible
docker-compose exec postgres pg_isready -U presgen
# Expected: "accepting connections"
```

### 2. Current Git State

```bash
# Verify you're on the right commit
git log -1 --oneline
# Should show: 6fed789 feat: Phase 1 - Fix course generation timeout and error handling

# Check for uncommitted changes
git status
# Should be clean (only show database/backup files)

# Verify tag exists
git tag | grep phase1-ready
# Should show: phase1-ready
```

### 3. Backup Verification

```bash
# Create backups
docker-compose exec postgres pg_dump -U presgen presgen_assess > backup_$(date +%Y%m%d_%H%M%S).sql
docker-compose exec nginx cat /etc/nginx/nginx.conf > nginx.conf.backup

# Verify backups exist and have content
ls -lh backup_*.sql nginx.conf.backup
# Should show non-zero file sizes
```

### 4. Disk Space

```bash
# Check available disk space
df -h .
# Should have at least 1GB free

# Check Docker disk usage
docker system df
# Review to ensure not near limits
```

### 5. Network Connectivity

```bash
# Verify containers can reach each other
docker-compose exec presgen-assess curl -s http://presgen-core:8080/healthz
# Should return health status

# Verify nginx can reach assess
docker-compose exec nginx wget -q -O- http://presgen_assess:8000/health || echo "Failed"
# Should succeed
```

---

## Issues Found?

### Issue: presgen-assess not healthy

**Solution:**
```bash
# Check logs
docker-compose logs --tail=100 presgen-assess

# Common issues:
# 1. Database connection - check DATABASE_URL
# 2. Migration failed - check alembic logs
# 3. Port conflict - check if 8000 is available

# Restart if needed
docker-compose restart presgen-assess
sleep 10
docker-compose ps presgen-assess
```

### Issue: nginx unhealthy

**Solution:**
```bash
# Check nginx logs
docker-compose logs --tail=50 nginx

# Test config
docker-compose exec nginx nginx -t

# Restart if needed
docker-compose restart nginx
```

### Issue: Out of disk space

**Solution:**
```bash
# Clean up Docker
docker system prune -a --volumes

# Remove old images
docker images | grep '<none>' | awk '{print $3}' | xargs docker rmi

# Check again
df -h .
```

---

## Ready to Deploy?

If all checks pass:

✅ Services are running (presgen-ui unhealthy is OK)
✅ Git is on correct commit (6fed789)
✅ Backups created
✅ Disk space available
✅ Network connectivity works

**Proceed to:** [PHASE_1_QUICK_DEPLOY.md](PHASE_1_QUICK_DEPLOY.md)

---

## Not Ready?

**Issues to fix first:**
- [ ] presgen-assess not healthy → Fix database/config issues
- [ ] nginx not healthy → Fix nginx config
- [ ] No disk space → Clean up Docker
- [ ] Git not on right commit → Pull latest changes

**Get help:**
- Check logs: `docker-compose logs [service]`
- Full documentation: [PHASE_1_DEPLOYMENT_GUIDE.md](PHASE_1_DEPLOYMENT_GUIDE.md)

---

**Checklist completed by:** _________________
**Date:** _________________
**Ready to deploy:** Yes / No
