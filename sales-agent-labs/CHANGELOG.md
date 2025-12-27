# Changelog

All notable changes to the PresGen Sales Agent Labs project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added - 2025-12-27

#### AWS Lightsail Infrastructure & Deployment

- **New deployment scripts** for AWS Lightsail management:
  - `aws_migration/scripts/restart-services.sh` - Docker service restart automation
  - `aws_migration/scripts/restore-from-snapshot.sh` - Database snapshot restoration
  - `aws_migration/scripts/setup-auto-restart.sh` - Automated service recovery
  - `aws_migration/scripts/fix-deployment.sh` - Deployment troubleshooting utilities
- **Restart instructions** (`aws_migration/RESTART_INSTRUCTIONS.md`) for production instance recovery
- **Database management utilities**:
  - `fix_chromadb_dimensions.py` - ChromaDB vector dimension correction script
  - `run_chromadb_fix.sh` - Automated ChromaDB fix execution
  - `backup_20251109_162032.sql` - Database backup for disaster recovery
- **Voice profile testing** (`test_voice_profile.py`) for voice generation validation
- **Voice manager logging patch** (`voice_manager_logging_patch.py`) for enhanced debugging
- **Configuration backups**:
  - `nginx.conf.backup` - Nginx configuration backup
  - `nginx/nginx.conf.bak` - Alternative nginx configuration backup
- **SSH key management** (`presgen-prod-key.pub`) for secure instance access
- **Data directory** for application data storage

### Changed - 2025-12-27

#### AWS Migration & Infrastructure Updates

- **Enhanced `start-lightsail.sh`** with comprehensive SSH connectivity testing and automated Docker service restart
  - Added fresh SSH key download from AWS Lightsail
  - Implemented base64 key decoding with padding issue handling
  - Added automatic Docker container restart on instance start
  - Added web service health check verification
  - Improved error handling with manual restart fallback instructions
- **Updated `PHASE3_MANUAL_INSTRUCTIONS.md`** with production deployment details:
  - Added Google Cloud service account JSON credentials transfer steps
  - Added S3 bucket cleanup commands
  - Updated temporary S3 bucket names to actual values (`presgen-temp-1763110232`)
  - Added credential file verification commands with `jq` validation
  - Documented OpenAI API key configuration
  - Added complete service account setup with heredoc examples

#### Configuration & Documentation

- **Updated `scratch.txt`** with production access information:
  - Added SSH connection commands and methods
  - Documented Lightsail instance details (IP: 35.175.156.231)
  - Added useful Docker commands for service management
  - Documented project location on server
  - Added workflow submission response examples

### Fixed - 2025-12-27

- **SSH connectivity issues** in Lightsail startup script with automatic key management
- **Service restart automation** to ensure containers start properly after instance start
- **Google Cloud credentials** transfer process with validation steps
- **Production environment configuration** with proper API keys and service accounts

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
