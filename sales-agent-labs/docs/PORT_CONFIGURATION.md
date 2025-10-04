# Port Configuration Standardization

**Date**: 2025-10-04
**Status**: ✅ Implemented

## Overview

Standardized port configuration across all PresGen services to use a centralized `.env` file. This eliminates hardcoded port references and makes the architecture easier to manage.

## Architecture

### Service Port Assignments

| Service | Port | URL | Purpose |
|---------|------|-----|---------|
| **PresGen-Assess** | 8000 | http://localhost:8000 | Assessment API (FastAPI) |
| **PresGen-Core** | 8080 | http://localhost:8080 | Video generation service (FastAPI) |
| **PresGen-UI** | 3000 | http://localhost:3000 | Frontend (Next.js) |

### Service Communication Flow

```
┌─────────────┐
│ PresGen-UI  │ :3000
│  (Next.js)  │
└──────┬──────┘
       │
       ├─────► PresGen-Assess :8000
       │         (Assessment API)
       │              │
       └──────────────┴─────► PresGen-Core :8080
                              (Video Generation)
```

## Implementation

### 1. Centralized Environment Variables

**Location**: `/.env`

```bash
# Service Ports Configuration
PRESGEN_ASSESS_PORT=8000
PRESGEN_CORE_PORT=8080
PRESGEN_UI_PORT=3000

# Service URLs (Internal Communication)
PRESGEN_ASSESS_URL=http://localhost:8000
PRESGEN_CORE_URL=http://localhost:8080

# External Service URLs (Public Access - for Next.js)
NEXT_PUBLIC_PRESGEN_ASSESS_URL=http://localhost:8000
NEXT_PUBLIC_PRESGEN_CORE_URL=http://localhost:8080
```

### 2. Configuration Libraries

#### PresGen-UI: `presgen-ui/src/lib/config.ts`

```typescript
export const PRESGEN_ASSESS_URL =
  process.env.NEXT_PUBLIC_PRESGEN_ASSESS_URL || 'http://localhost:8000';

export const PRESGEN_CORE_URL =
  process.env.NEXT_PUBLIC_PRESGEN_CORE_URL || 'http://localhost:8080';

export const ASSESS_API_URL = PRESGEN_ASSESS_URL;
```

**Usage in route handlers**:
```typescript
import { ASSESS_API_URL } from '@/lib/config';

const response = await fetch(`${ASSESS_API_URL}/health`);
```

#### PresGen-Core: `src/common/config.py`

```python
def get_presgen_assess_port() -> int:
    return int(os.getenv("PRESGEN_ASSESS_PORT", "8000"))

def get_presgen_core_port() -> int:
    return int(os.getenv("PRESGEN_CORE_PORT", "8080"))

def get_presgen_assess_url() -> str:
    return os.getenv("PRESGEN_ASSESS_URL", f"http://localhost:{get_presgen_assess_port()}")
```

#### PresGen-Assess: `presgen-assess/src/common/config.py`

Uses Pydantic Settings with enhanced logging:

```python
class Settings(BaseSettings):
    presgen_core_url: str = Field(default="http://localhost:8080", alias="PRESGEN_CORE_URL")
    presgen_avatar_url: str = Field(default="http://localhost:8002", alias="PRESGEN_AVATAR_URL")
```

### 3. Enhanced Logging

All services now log their port configuration on startup:

**PresGen-Assess**:
```
🔧 Port Configuration (Standardized 2025-10-04):
  📡 PresGen-Core URL: http://localhost:8080
  📡 PresGen-Avatar URL: http://localhost:8002
  📡 PresGen-Core Max Slides: 40
```

**PresGen-Core**:
```python
from src.common.config import log_port_configuration
log_port_configuration()
```

### 4. Startup Script

**Location**: `/start_services.sh`

```bash
./start_services.sh
```

Features:
- ✅ Checks if ports are available before starting
- ✅ Starts services in correct order
- ✅ Logs to separate files per service
- ✅ Provides helpful status messages
- ✅ Shows URLs and log locations

## Changes Made

### Files Created

1. `/.env.template` - Template for environment configuration
2. `/start_services.sh` - Service startup script
3. `/update_port_refs.py` - Script to update hardcoded references
4. `/presgen-ui/src/lib/config.ts` - UI configuration library
5. `/docs/PORT_CONFIGURATION.md` - This documentation

### Files Modified

1. **Root `.env`** - Added port configuration section
2. **presgen-ui/.env.local** - Updated to use standardized ports (8000, 8080, 3000)
3. **presgen-assess/src/common/config.py** - Added enhanced logging
4. **src/common/config.py** - Added port configuration helpers
5. **18 route.ts files in presgen-ui** - Replaced hardcoded `8081` with config import

### Port Reference Updates

Updated **18 files** from:
```typescript
const ASSESS_API_URL = process.env.NEXT_PUBLIC_ASSESS_API_URL || 'http://localhost:8081'
```

To:
```typescript
import { ASSESS_API_URL } from '@/lib/config'
```

## Migration Guide

### For Developers

1. **Pull latest changes**:
   ```bash
   git pull origin main
   ```

2. **Update your `.env` file**:
   ```bash
   cp .env.template .env
   # Add your API keys and credentials
   ```

3. **Stop old services**:
   ```bash
   pkill -f uvicorn
   pkill -f next
   ```

4. **Start services using new script**:
   ```bash
   ./start_services.sh
   ```

### Verifying Configuration

Check that services are using correct ports:

```bash
# Check running services
lsof -i :8000  # PresGen-Assess
lsof -i :8080  # PresGen-Core
lsof -i :3000  # PresGen-UI

# Check logs
tail -f logs/presgen-assess.log
tail -f logs/presgen-core.log
tail -f logs/presgen-ui.log
```

## Benefits

1. ✅ **Single source of truth** - All port configuration in one place
2. ✅ **Easy to change** - Update `.env` instead of searching code
3. ✅ **Consistent across services** - No more port mismatches
4. ✅ **Better logging** - Port configuration logged on startup
5. ✅ **Simplified deployment** - One script to start all services

## Breaking Changes

⚠️ **Port 8081 is no longer used** - PresGen-Assess now runs on port 8000

If you have bookmarks or scripts using port 8081, update them to use port 8000.

## Troubleshooting

### Port Already in Use

```bash
# Free specific ports
lsof -ti:8000 | xargs kill
lsof -ti:8080 | xargs kill
lsof -ti:3000 | xargs kill

# Or kill all instances
pkill -f 'uvicorn.*8000'
pkill -f 'uvicorn.*8080'
pkill -f 'next.*3000'
```

### Services Not Finding Each Other

Check that `.env` has correct URLs:
```bash
grep PRESGEN .env
```

Verify services are logging the correct configuration on startup.

### Old Hardcoded References

If you find port references not updated:
```bash
# Search for remaining hardcoded ports
grep -r "8081" presgen-ui/src/
grep -r "8001" src/
```

## Related Documentation

- [Service Architecture](./ARCHITECTURE.md)
- [Development Setup](./DEVELOPMENT.md)
- [Deployment Guide](./DEPLOYMENT.md)

## Future Improvements

- [ ] Add Docker Compose configuration
- [ ] Add health check endpoint to startup script
- [ ] Add graceful shutdown handler
- [ ] Add service dependency checking (wait for PresGen-Core before starting PresGen-Assess)
