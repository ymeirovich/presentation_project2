# Changelog

All notable changes to the PresGen Sales Agent Labs project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added - 2025-10-04

#### Port Configuration Standardization
- **Centralized .env configuration** for all service ports and URLs
- **Configuration libraries** for each service:
  - `presgen-ui/src/lib/config.ts` for Next.js frontend
  - `src/common/config.py` port helpers for PresGen-Core
  - Enhanced logging in `presgen-assess/src/common/config.py`
- **Startup script** (`start_services.sh`) to manage all services
- **Enhanced logging** showing port configuration on service startup
- **Documentation** (`docs/PORT_CONFIGURATION.md`) for port configuration system
- **.env.template** with standardized port configuration

### Changed - 2025-10-04

#### Port Assignments
- PresGen-Assess: Port **8081 → 8000** (standardized)
- PresGen-Core: Remains on port **8080** (confirmed)
- PresGen-UI: Remains on port **3000** (confirmed)

#### Code Updates
- Updated **18 route handler files** in presgen-ui to use centralized config
  - Replaced hardcoded `const ASSESS_API_URL = ... || 'http://localhost:8081'`
  - With `import { ASSESS_API_URL } from '@/lib/config'`
- Updated `presgen-ui/.env.local` to use ports 8000 and 8080
- Updated `presgen-assess/src/common/config.py` default from 8001 to 8080

### Fixed - 2025-10-04

- Fixed port mismatch: PresGen-Assess config was calling PresGen-Core on wrong port (8001 instead of 8080)
- Eliminated hardcoded port references across the codebase
- Improved consistency between development and production environments

### Developer Experience - 2025-10-04

- Single command to start all services: `./start_services.sh`
- Port configuration visible on startup via enhanced logging
- Centralized configuration makes port changes easier
- Automated script (`update_port_refs.py`) for future port reference updates

---

## Migration Notes

### Breaking Changes
⚠️ **PresGen-Assess now runs on port 8000 instead of 8081**

If you have:
- Bookmarks to `localhost:8081`
- Scripts calling PresGen-Assess
- External services configured to use port 8081

Update them to use **port 8000**.

### Migration Steps
1. Pull latest changes
2. Update your `.env` file (use `.env.template` as reference)
3. Stop old services: `pkill -f uvicorn && pkill -f next`
4. Start services: `./start_services.sh`

See `docs/PORT_CONFIGURATION.md` for full migration guide.
