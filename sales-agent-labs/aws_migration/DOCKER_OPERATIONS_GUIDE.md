# Docker Operations Guide - Start, Stop, Recover

**Quick Reference for Managing PresGen Docker Stack**

---

## 🚀 Starting the Application

### Option 1: Start Everything (Recommended)

```bash
# Navigate to project directory
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs

# Start all services in background
docker-compose up -d

# Wait for services to be ready
sleep 70

# Check status
docker-compose ps
```

**Expected Output:**
```
NAME              IMAGE                          STATUS
presgen-assess    sales-agent-labs-presgen-assess   Up 2 minutes (healthy)
presgen-core      sales-agent-labs-presgen-core     Up 2 minutes (healthy)
presgen-nginx     nginx:alpine                      Up 2 minutes (healthy)
presgen-redis     redis:7-alpine                    Up 2 minutes (healthy)
presgen-ui        sales-agent-labs-presgen-ui       Up 2 minutes (unhealthy)
```

**Access Points:**
- **UI:** http://localhost/
- **Credentials:** demo / demo
- **Health:** http://localhost/health (no auth)

---

### Option 2: Start Specific Services

```bash
# Start only presgen-ui (and its dependencies)
docker-compose up -d presgen-ui

# Start only presgen-assess
docker-compose up -d presgen-assess

# Start core and assess
docker-compose up -d presgen-core presgen-assess
```

---

### Option 3: Start with Logs (Foreground)

```bash
# See logs in real-time (Ctrl+C to stop)
docker-compose up

# Or specific service
docker-compose up presgen-ui
```

---

## 🛑 Stopping the Application

### Stop All Services

```bash
# Stop all containers (keeps data)
docker-compose stop

# Stop and remove containers (keeps volumes/data)
docker-compose down

# Stop, remove containers AND volumes (DELETES DATA!)
docker-compose down -v  # ⚠️ Use with caution!
```

### Stop Specific Service

```bash
# Stop just the UI
docker-compose stop presgen-ui

# Stop core and assess
docker-compose stop presgen-core presgen-assess
```

---

## 🔄 Restarting Services

### Restart All Services

```bash
# Quick restart (keeps containers)
docker-compose restart

# Full restart (recreate containers)
docker-compose down && docker-compose up -d
```

### Restart Specific Service

```bash
# Restart just presgen-ui
docker-compose restart presgen-ui

# Restart and rebuild presgen-assess
docker-compose build presgen-assess
docker-compose up -d presgen-assess
```

---

## 🔍 Checking Status

### View Running Containers

```bash
# All containers
docker-compose ps

# All containers (Docker native command)
docker ps

# All containers including stopped
docker ps -a

# Filter by service
docker ps -f name=presgen-ui
```

### Check Health Status

```bash
# View health of all services
docker-compose ps

# Check specific service health
docker inspect presgen-assess | grep -A 10 "Health"

# Test health endpoint manually
curl http://localhost/health
```

### View Resource Usage

```bash
# All containers
docker stats

# Specific service
docker stats presgen-assess

# One-time snapshot
docker stats --no-stream
```

---

## 📋 Viewing Logs

### View Logs - All Services

```bash
# All logs
docker-compose logs

# Follow logs in real-time
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100

# With timestamps
docker-compose logs -t
```

### View Logs - Specific Service

```bash
# presgen-ui logs
docker logs presgen-ui

# Follow presgen-assess logs
docker logs -f presgen-assess

# Last 50 lines of presgen-core
docker logs --tail 50 presgen-core

# nginx access logs
docker logs presgen-nginx

# Search for errors
docker logs presgen-assess 2>&1 | grep -i error
```

### View Logs - Multiple Services

```bash
# UI and assess together
docker-compose logs -f presgen-ui presgen-assess

# Core and nginx
docker-compose logs -f presgen-core presgen-nginx
```

---

## 🔨 Rebuilding Services

### When to Rebuild

Rebuild when you've changed:
- Source code in `src/`
- `requirements.txt` (Python dependencies)
- `package.json` (Node dependencies)
- `Dockerfile`

### Rebuild Single Service

```bash
# Rebuild presgen-ui
docker-compose build presgen-ui

# Rebuild and restart
docker-compose build presgen-ui && docker-compose up -d presgen-ui

# Force rebuild (no cache)
docker-compose build --no-cache presgen-ui
```

### Rebuild All Services

```bash
# Rebuild everything
docker-compose build

# Rebuild without cache
docker-compose build --no-cache

# Rebuild and start
docker-compose up -d --build
```

---

## 🚨 Recovery Procedures

### Scenario 1: Service Won't Start

**Symptoms:**
- Container keeps restarting
- Shows as "unhealthy"
- Not responding

**Steps:**

1. **Check logs first:**
   ```bash
   docker logs presgen-ui --tail 100
   ```

2. **Look for common errors:**
   - Port already in use
   - Missing dependencies
   - Configuration errors
   - Database connection issues

3. **Try restarting:**
   ```bash
   docker-compose restart presgen-ui
   ```

4. **If that fails, rebuild:**
   ```bash
   docker-compose build presgen-ui
   docker-compose up -d presgen-ui
   ```

5. **If still failing, clean start:**
   ```bash
   docker-compose down
   docker-compose up -d
   ```

---

### Scenario 2: Port Already in Use

**Error:**
```
Error starting userland proxy: listen tcp 0.0.0.0:8000: bind: address already in use
```

**Solution:**

1. **Find what's using the port:**
   ```bash
   # Find process on port 8000
   lsof -i :8000

   # Or on port 3000 (UI)
   lsof -i :3000
   ```

2. **Kill the process:**
   ```bash
   # Kill by PID
   kill -9 <PID>

   # Or stop the Docker container
   docker stop <container-name>
   ```

3. **Or change the port in docker-compose.yml:**
   ```yaml
   ports:
     - "8001:8000"  # Use 8001 instead of 8000
   ```

---

### Scenario 3: "Unhealthy" Container

**Symptoms:**
- `docker-compose ps` shows "(unhealthy)"
- Service actually works but shows unhealthy

**Example:**
```
presgen-ui    Up 5 minutes (unhealthy)   3000/tcp
```

**Steps:**

1. **Check if service actually works:**
   ```bash
   # Test the endpoint directly
   curl http://localhost:3000  # For UI
   curl http://localhost:8000/health  # For assess
   ```

2. **If it works, health check might be wrong:**
   - Check `HEALTHCHECK` in Dockerfile
   - Verify endpoint path is correct
   - Check if health check tool (curl/wget/nc) exists in container

3. **Temporary fix - ignore health check:**
   - In `docker-compose.yml`, change dependency from `service_healthy` to `service_started`

4. **Or disable health check:**
   ```yaml
   healthcheck:
     disable: true
   ```

---

### Scenario 4: Database Errors

**Error:**
```
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) database is locked
```

**Solution:**

1. **Stop all services:**
   ```bash
   docker-compose down
   ```

2. **Check database files:**
   ```bash
   ls -la data/assess/
   ls -la presgen-assess/
   ```

3. **If needed, remove lock files:**
   ```bash
   find . -name "*.db-shm" -o -name "*.db-wal" | xargs rm
   ```

4. **Restart:**
   ```bash
   docker-compose up -d
   ```

---

### Scenario 5: Container Crashed

**Symptoms:**
- Container shows as "Exited"
- Service not responding

**Steps:**

1. **Check exit status:**
   ```bash
   docker ps -a | grep presgen-ui
   ```

2. **View logs to find crash reason:**
   ```bash
   docker logs presgen-ui --tail 100
   ```

3. **Common crash causes:**
   - Out of memory → Check: `docker logs presgen-ui | grep -i "memory\|oom"`
   - Syntax error → Check: `docker logs presgen-ui | grep -i "error"`
   - Missing file → Check: `docker logs presgen-ui | grep -i "not found"`

4. **Try to restart:**
   ```bash
   docker start presgen-ui
   ```

5. **If it crashes again, rebuild:**
   ```bash
   docker-compose build presgen-ui
   docker-compose up -d presgen-ui
   ```

---

### Scenario 6: Network Issues

**Error:**
```
ERROR: Network presgen-network not found
```

**Solution:**

1. **Recreate network:**
   ```bash
   docker-compose down
   docker network create sales-agent-labs_presgen-network
   docker-compose up -d
   ```

2. **Or let docker-compose recreate it:**
   ```bash
   docker-compose down
   docker-compose up -d
   ```

---

### Scenario 7: Out of Disk Space

**Error:**
```
no space left on device
```

**Solution:**

1. **Check disk usage:**
   ```bash
   df -h
   docker system df
   ```

2. **Clean up Docker:**
   ```bash
   # Remove unused containers, networks, images
   docker system prune

   # Remove ALL unused data (be careful!)
   docker system prune -a

   # Remove unused volumes
   docker volume prune
   ```

3. **Remove specific items:**
   ```bash
   # Remove stopped containers
   docker container prune

   # Remove unused images
   docker image prune -a

   # Remove build cache
   docker builder prune
   ```

---

### Scenario 8: Changes Not Reflecting

**Symptoms:**
- Code changes don't appear
- Still using old version

**Solution:**

1. **Force rebuild with no cache:**
   ```bash
   docker-compose build --no-cache presgen-ui
   docker-compose up -d presgen-ui
   ```

2. **Or rebuild everything:**
   ```bash
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   ```

3. **Check you're editing the right files:**
   ```bash
   # Files are copied INTO the container
   # Make sure you're editing source files, not container files
   ```

---

## 🧹 Clean Start (Nuclear Option)

When everything is broken and you want a fresh start:

```bash
# Step 1: Stop everything
docker-compose down

# Step 2: Remove containers
docker-compose rm -f

# Step 3: Remove volumes (⚠️ DELETES DATA!)
docker-compose down -v

# Step 4: Remove images (forces rebuild)
docker rmi sales-agent-labs-presgen-ui
docker rmi sales-agent-labs-presgen-assess
docker rmi sales-agent-labs-presgen-core

# Step 5: Clean Docker system
docker system prune -a

# Step 6: Rebuild everything
docker-compose build --no-cache

# Step 7: Start fresh
docker-compose up -d

# Step 8: Wait and check
sleep 70
docker-compose ps
```

**⚠️ Warning:** This deletes all data in Docker volumes!

---

## 📊 Common Status Checks

### Is Everything Running?

```bash
# Quick check
docker-compose ps

# Expected healthy services:
# - presgen-core: healthy
# - presgen-assess: healthy
# - presgen-redis: healthy
# - presgen-nginx: healthy
# - presgen-ui: may show unhealthy but works
```

### Can I Access the UI?

```bash
# Test health endpoint (no auth)
curl http://localhost/health

# Test UI (with auth)
curl -u demo:demo http://localhost/ | head -20

# Should return HTML
```

### Are APIs Working?

```bash
# Test Core API
curl -u demo:demo http://localhost/core/healthz

# Should return: {"ok":true}

# Test Assess API health
docker exec presgen-assess curl -s http://localhost:8000/health

# Should return: {"status":"healthy","service":"presgen-assess"}
```

---

## 🔧 Debugging Tips

### 1. Check Container is Running

```bash
docker ps -f name=presgen-ui
```

### 2. Check Logs for Errors

```bash
docker logs presgen-ui 2>&1 | grep -i error | tail -20
```

### 3. Exec Into Container

```bash
# Get a shell inside the container
docker exec -it presgen-ui sh

# Then you can:
ls /app
ps aux
env | grep PRESGEN
```

### 4. Test Connectivity

```bash
# From host to container
curl http://localhost:3000

# From container to container
docker exec presgen-ui ping presgen-core
```

### 5. Check Environment Variables

```bash
docker exec presgen-ui env | grep -i presgen
```

### 6. Inspect Container Configuration

```bash
docker inspect presgen-ui | less
```

---

## 📝 Startup Checklist

Use this checklist when starting the application:

- [ ] Navigate to project directory
- [ ] Pull latest code: `git pull`
- [ ] Check no containers running: `docker-compose ps`
- [ ] Start services: `docker-compose up -d`
- [ ] Wait 70 seconds: `sleep 70`
- [ ] Check status: `docker-compose ps`
- [ ] Check logs: `docker-compose logs --tail=50`
- [ ] Test health: `curl http://localhost/health`
- [ ] Test UI: `curl -u demo:demo http://localhost/`
- [ ] Open browser: http://localhost/
- [ ] Login: demo / demo

---

## 🚀 Quick Commands Reference

| Task | Command |
|------|---------|
| **Start all** | `docker-compose up -d` |
| **Stop all** | `docker-compose down` |
| **Restart all** | `docker-compose restart` |
| **View logs** | `docker-compose logs -f` |
| **Check status** | `docker-compose ps` |
| **Rebuild service** | `docker-compose build presgen-ui` |
| **Rebuild all** | `docker-compose build` |
| **Clean start** | `docker-compose down && docker-compose up -d` |
| **Nuclear option** | `docker-compose down -v && docker system prune -a` |
| **Test health** | `curl http://localhost/health` |
| **Test UI** | `curl -u demo:demo http://localhost/` |

---

## 🆘 When to Ask for Help

If you've tried:
1. Checking logs: `docker logs presgen-ui`
2. Restarting: `docker-compose restart`
3. Rebuilding: `docker-compose build && docker-compose up -d`
4. Clean start: `docker-compose down && docker-compose up -d`

And it still doesn't work, share:
- Output of: `docker-compose ps`
- Last 100 lines: `docker logs presgen-ui --tail 100`
- Any error messages you see

---

## 📚 Related Documentation

- **Docker Logs Guide:** [LOCAL_DOCKER_LOGS_GUIDE.md](LOCAL_DOCKER_LOGS_GUIDE.md)
- **Google Workspace Setup:** [GOOGLE_WORKSPACE_STATUS.md](GOOGLE_WORKSPACE_STATUS.md)
- **AWS Deployment:** [AWS_DEPLOYMENT_CHECKLIST.md](AWS_DEPLOYMENT_CHECKLIST.md)

---

**Last Updated:** October 30, 2025
**Status:** Full operational guide for local Docker development
