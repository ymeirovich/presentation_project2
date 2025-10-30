# ⚡ Quick Start Guide - PresGen Local Development

**Get up and running in 2 minutes!**

---

## 🚀 Start the Application

```bash
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs
docker-compose up -d
sleep 70  # Wait for services
```

**Access:** http://localhost/ (Login: `demo` / `demo`)

---

## 🛑 Stop the Application

```bash
docker-compose down
```

---

## 🔄 Restart After Code Changes

```bash
# Rebuild and restart specific service
docker-compose build presgen-ui
docker-compose up -d presgen-ui

# Or rebuild everything
docker-compose build
docker-compose up -d
```

---

## 📋 Check Status

```bash
# View all services
docker-compose ps

# View logs
docker-compose logs -f

# Test health
curl http://localhost/health
```

---

## 🆘 Something's Broken?

```bash
# 1. Check logs
docker logs presgen-ui

# 2. Restart
docker-compose restart presgen-ui

# 3. Clean start
docker-compose down && docker-compose up -d

# 4. Nuclear option (deletes data!)
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

---

## 📚 Full Documentation

- **Complete Operations Guide:** [DOCKER_OPERATIONS_GUIDE.md](DOCKER_OPERATIONS_GUIDE.md)
- **Viewing Logs:** [LOCAL_DOCKER_LOGS_GUIDE.md](LOCAL_DOCKER_LOGS_GUIDE.md)
- **Google Workspace Setup:** [GOOGLE_WORKSPACE_STATUS.md](GOOGLE_WORKSPACE_STATUS.md)
- **AWS Deployment:** [AWS_DEPLOYMENT_CHECKLIST.md](AWS_DEPLOYMENT_CHECKLIST.md)

---

## 🎯 Common Tasks

| Task | Command |
|------|---------|
| Start | `docker-compose up -d` |
| Stop | `docker-compose down` |
| Logs | `docker-compose logs -f` |
| Status | `docker-compose ps` |
| Restart | `docker-compose restart` |
| Rebuild | `docker-compose build` |

---

**Need Help?** See [DOCKER_OPERATIONS_GUIDE.md](DOCKER_OPERATIONS_GUIDE.md) for detailed troubleshooting!
