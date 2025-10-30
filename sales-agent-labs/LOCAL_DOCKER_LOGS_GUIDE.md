# Docker Logs Guide - PresGen Local Development

## Quick Commands to View Logs

### View All Services Logs
```bash
# View all logs
docker-compose logs

# Follow logs in real-time (Ctrl+C to exit)
docker-compose logs -f

# View last 100 lines from all services
docker-compose logs --tail=100

# Follow logs with timestamps
docker-compose logs -f -t
```

### View Individual Service Logs

```bash
# presgen-assess (Assessment API)
docker logs presgen-assess
docker logs -f presgen-assess  # Follow in real-time
docker logs --tail 50 presgen-assess  # Last 50 lines
docker logs -t presgen-assess  # With timestamps

# presgen-core (Core API)
docker logs presgen-core
docker logs -f presgen-core

# presgen-ui (Next.js Frontend)
docker logs presgen-ui
docker logs -f presgen-ui

# nginx (Reverse Proxy)
docker logs presgen-nginx
docker logs -f presgen-nginx

# Redis
docker logs presgen-redis
```

### Filter Logs

```bash
# Search for errors
docker logs presgen-assess 2>&1 | grep -i error

# Search for specific text
docker logs presgen-assess 2>&1 | grep "Failed to"

# View only stderr
docker logs presgen-assess 2>&1 | grep "ERROR"

# Show logs from last 5 minutes
docker logs --since 5m presgen-assess

# Show logs until 10 minutes ago
docker logs --until 10m presgen-assess
```

### Save Logs to File

```bash
# Save logs for debugging
docker logs presgen-assess > assess-logs.txt 2>&1

# Save all services
docker-compose logs > all-services.log 2>&1
```

### Monitor Multiple Services

```bash
# Watch logs from multiple services
docker-compose logs -f presgen-assess presgen-core nginx
```

## Current Known Issues

### 1. UI "Failed to Fetch" Errors

**Error in Browser Console:**
```
TypeError: Failed to fetch
at useReportPrompt.useEffect
```

**Cause:** UI is trying to call API endpoints that haven't been implemented yet:
- `/api/v1/prompts/report` → 404
- `/api/v1/certifications` → 404
- `/api/v1/workflows` → 404

**Status:** Expected for work-in-progress. These endpoints need to be implemented in presgen-assess.

**Workaround:** Ignore these errors for now. The UI still renders and basic functionality works.

### 2. Missing 'common' Module Warning

**Error in presgen-assess logs:**
```
ModuleNotFoundError: No module named 'common'
⚠️  Google Slides integration module not found
```

**Cause:** The `common` module import path issue in startup checks.

**Impact:** Non-blocking. Service starts and runs despite the warning.

**Workaround:** Set `PRESGEN_USE_MOCK=true` to use mock mode.

### 3. presgen-ui Health Check

**Status:** UI container shows as "unhealthy" but application works fine

**Cause:** Health check using nc (netcat) having issues with Next.js standalone server

**Impact:** None on functionality. nginx and UI work correctly.

## Accessing Services

### URLs
- **Frontend (UI):** http://localhost/
- **Health Check:** http://localhost/health (no auth)
- **Core API:** http://localhost/core/*
- **Assess API:** http://localhost/api/*

### Authentication
- **Username:** demo
- **Password:** demo

### Testing with curl

```bash
# Health check (no auth)
curl http://localhost/health

# UI with auth
curl -u demo:demo http://localhost/

# Core API health
curl -u demo:demo http://localhost/core/healthz

# Assess API (example endpoint)
curl -u demo:demo http://localhost/api/v1/health
```

## Checking Service Status

```bash
# View all containers
docker ps

# Check specific container status
docker ps -f name=presgen-assess

# View container health
docker inspect presgen-assess | grep -A 10 "Health"

# See what ports are mapped
docker port presgen-nginx
```

## Troubleshooting Commands

### Container Not Running

```bash
# Check why container stopped
docker ps -a | grep presgen-assess

# View logs from stopped container
docker logs presgen-assess

# Restart container
docker restart presgen-assess

# Restart all services
docker-compose restart
```

### Container Keeps Restarting

```bash
# Watch real-time restarts
watch -n 1 'docker ps | grep presgen'

# Check last 100 lines of logs
docker logs --tail 100 presgen-assess

# Follow logs to see crash
docker logs -f presgen-assess
```

### Network Issues

```bash
# Check network
docker network ls
docker network inspect sales-agent-labs_presgen-network

# Test connectivity between containers
docker exec presgen-nginx ping -c 3 presgen-assess
```

### Resource Usage

```bash
# Check resource usage
docker stats

# Check specific container
docker stats presgen-assess

# View disk usage
docker system df
```

## nginx Access Logs

nginx logs all HTTP requests. Very useful for debugging API issues!

```bash
# View recent requests
docker logs presgen-nginx 2>&1 | tail -50

# Follow access log in real-time
docker logs -f presgen-nginx

# Filter for API calls
docker logs presgen-nginx 2>&1 | grep "GET /api"

# Filter for errors (4xx, 5xx)
docker logs presgen-nginx 2>&1 | grep -E " (4|5)[0-9]{2} "

# See what the UI is calling
docker logs presgen-nginx 2>&1 | grep -E "GET|POST" | tail -20
```

### Example nginx Log Entry:
```
192.168.65.1 - demo [30/Oct/2025:09:27:10 +0000] "GET /api/presgen/prompts/report HTTP/1.1"
404 53 "http://localhost/" "Mozilla/5.0..." "-" rt=0.023 uct="0.008"
```

**Fields:**
- `192.168.65.1` - Client IP
- `demo` - Username (basic auth)
- `GET /api/presgen/prompts/report` - Request
- `404` - HTTP status code
- `53` - Response size in bytes
- `rt=0.023` - Total request time (seconds)

## Useful Development Workflows

### Start Fresh
```bash
# Stop everything
docker-compose down

# Remove volumes (WARNING: deletes data)
docker-compose down -v

# Rebuild and start
docker-compose build
docker-compose up -d

# Check status
docker ps
```

### Test Changes
```bash
# Rebuild specific service
docker-compose build presgen-assess

# Restart just that service
docker-compose up -d presgen-assess

# Watch logs
docker logs -f presgen-assess
```

### Debug API Issues
```bash
# 1. Check nginx logs to see requests
docker logs presgen-nginx 2>&1 | grep -E "GET|POST" | tail -20

# 2. Check backend logs
docker logs presgen-assess --tail 50

# 3. Test endpoint directly
curl -u demo:demo -v http://localhost/api/v1/health
```

## Log Locations Inside Containers

If you need to exec into a container:

```bash
# Enter container shell
docker exec -it presgen-assess sh

# Common log locations
ls /app/logs/
ls /var/log/

# View environment variables
env | grep -i presgen

# Check Python processes
ps aux | grep python
```

## Production Log Management

For AWS deployment, consider:

1. **Log Rotation** - Prevent logs from filling disk
```yaml
# In docker-compose.yml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

2. **Centralized Logging** - Send to CloudWatch or ELK stack

3. **Log Levels** - Use INFO in prod, DEBUG only when needed

4. **Structured Logging** - JSON format for easier parsing

---

**Last Updated:** October 30, 2025
**Status:** Full stack running locally with minor API 404s (expected for WIP)
