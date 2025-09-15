# PresGen-Training2: Production Deployment Guide

**Date:** September 15, 2025
**Phase:** 4 - Production Deployment Configuration
**Status:** ✅ COMPLETED

## Overview

This guide provides comprehensive instructions for deploying PresGen-Training2 to production with LivePortrait avatar generation, voice cloning, and three operational modes optimized for M1 Mac hardware.

## Prerequisites

### Hardware Requirements
- **Minimum:** Apple Silicon Mac (M1/M1 Pro/M1 Max/M2) with 8GB RAM
- **Recommended:** Apple M1 Pro/Max with 16GB+ RAM
- **Storage:** 25GB+ free space for models and processing
- **Network:** Reliable internet for Google Slides API access

### Software Requirements
- **macOS:** Big Sur 11.0+ (for Apple Silicon support)
- **Python:** 3.10+ with PyTorch 2.0+ and MPS support
- **Node.js:** 18+ for Next.js frontend
- **Git:** For repository management
- **FFmpeg:** For video processing (installed via Homebrew)

## Installation Steps

### 1. Environment Setup

```bash
# Clone repository
git clone <repository-url>
cd presgen-training2

# Create Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip3 install -r requirements.txt
```

### 2. LivePortrait Model Installation

```bash
# Navigate to LivePortrait directory
cd LivePortrait

# Download pretrained models (automated)
python download_models.py

# Verify model installation
ls -la pretrained_weights/liveportrait/
# Should contain: base_models/, landmark.onnx, retargeting_models/
```

### 3. Environment Configuration

Create `.env` file in project root:

```bash
# Core settings
PYTORCH_ENABLE_MPS_FALLBACK=1
OMP_NUM_THREADS=1
MKL_NUM_THREADS=1

# Google Cloud (if using cloud services)
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json

# Development flags
DEBUG_MODE=false
LOG_LEVEL=INFO
```

### 4. Google Slides OAuth Setup

```bash
# Place OAuth credentials in project root
# oauth_slides_client.json - Download from Google Cloud Console

# Authenticate (run once)
python3 -c "from src.agent.slides_google import authenticate; authenticate()"
# This will open browser for OAuth flow and save token_slides.json
```

### 5. Frontend Setup

```bash
# Navigate to UI directory
cd presgen-ui

# Install dependencies
npm install

# Build for production
npm run build

# Start production server
npm start
```

## Production Configuration

### 1. FastAPI Service Configuration

**File:** `src/service/http.py`

Production settings:
```python
# Production environment variables
DEBUG_BYPASS_SLACK_SIG = False  # Disable debug mode
PRESGEN_USE_CACHE = True        # Enable caching
LOG_LEVEL = "INFO"              # Production logging
```

**Start command:**
```bash
uvicorn src.service.http:app --host 0.0.0.0 --port 8080 --workers 1
```

### 2. Next.js Frontend Configuration

**File:** `presgen-ui/next.config.ts`

```typescript
const nextConfig = {
  output: 'standalone',
  env: {
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8080'
  }
}
```

**Environment variables for production:**
```bash
NEXT_PUBLIC_API_BASE_URL=https://your-api-domain.com
```

### 3. Process Management

**Using PM2 (recommended):**

```bash
# Install PM2
npm install -g pm2

# Create ecosystem file
cat > ecosystem.config.js << EOF
module.exports = {
  apps: [
    {
      name: 'presgen-api',
      script: 'uvicorn',
      args: 'src.service.http:app --host 0.0.0.0 --port 8080',
      cwd: '/path/to/presgen-training2',
      env: {
        PYTORCH_ENABLE_MPS_FALLBACK: '1',
        OMP_NUM_THREADS: '1',
        MKL_NUM_THREADS: '1'
      }
    },
    {
      name: 'presgen-ui',
      script: 'npm',
      args: 'start',
      cwd: '/path/to/presgen-training2/presgen-ui',
      env: {
        PORT: '3001',
        NEXT_PUBLIC_API_BASE_URL: 'http://localhost:8080'
      }
    }
  ]
}
EOF

# Start services
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

## Security Configuration

### 1. API Security

```python
# Add to FastAPI app
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend-domain.com"],  # Restrict origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["*"],
)
```

### 2. File Upload Security

```python
# Validate file types and sizes
ALLOWED_VIDEO_TYPES = {'.mp4', '.mov', '.avi', '.mkv'}
MAX_VIDEO_SIZE = 200 * 1024 * 1024  # 200MB

def validate_upload(file: UploadFile):
    if file.size > MAX_VIDEO_SIZE:
        raise HTTPException(400, "File too large")

    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_VIDEO_TYPES:
        raise HTTPException(400, "Invalid file type")
```

### 3. Google OAuth Security

- Store credentials securely (not in git)
- Use environment variables for sensitive data
- Implement token refresh logic
- Restrict OAuth scopes to minimum required

## Performance Optimization

### 1. M1 Mac Optimizations

**Environment variables:**
```bash
export PYTORCH_ENABLE_MPS_FALLBACK=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0
```

**Memory management:**
```python
import torch

# Clear cache periodically
if torch.backends.mps.is_available():
    torch.mps.empty_cache()

# Use memory-efficient settings
torch.set_num_threads(1)
```

### 2. Caching Strategy

```python
# Enable caching for expensive operations
CACHE_CONFIG = {
    'voice_profiles': 3600,      # 1 hour
    'slide_processing': 1800,    # 30 minutes
    'avatar_generation': 600     # 10 minutes
}
```

### 3. Quality vs Speed Settings

```python
QUALITY_PROFILES = {
    'fast': {
        'resolution': '720p',
        'fps': 25,
        'bitrate': '2M'
    },
    'standard': {
        'resolution': '1080p',
        'fps': 30,
        'bitrate': '4M'
    },
    'high': {
        'resolution': '1080p',
        'fps': 30,
        'bitrate': '8M'
    }
}
```

## Monitoring and Logging

### 1. Application Logging

```python
import logging
from src.common.jsonlog import jlog

# Configure production logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/presgen/app.log'),
        logging.StreamHandler()
    ]
)

# Use structured logging
logger = logging.getLogger("presgen_training2")
jlog(logger, logging.INFO, event="video_generation_start", job_id=job_id)
```

### 2. Performance Monitoring

```python
import psutil
import time

def monitor_resources():
    return {
        'cpu_percent': psutil.cpu_percent(),
        'memory_percent': psutil.virtual_memory().percent,
        'disk_usage': psutil.disk_usage('/').percent
    }

# Log resource usage
@app.middleware("http")
async def monitor_middleware(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    logger.info(f"Request processed in {process_time:.2f}s", extra={
        'endpoint': request.url.path,
        'method': request.method,
        'processing_time': process_time,
        'resources': monitor_resources()
    })

    return response
```

### 3. Health Check Endpoints

```python
@app.get("/health")
async def health_check():
    """System health check"""
    return {
        'status': 'healthy',
        'timestamp': time.time(),
        'services': {
            'liveportrait': check_liveportrait_availability(),
            'voice_cloning': check_voice_system(),
            'google_slides': check_oauth_validity()
        },
        'resources': monitor_resources()
    }

@app.get("/training/health")
async def training_health():
    """Training-specific health check"""
    try:
        # Quick test of core functionality
        profiles = await get_voice_profiles()
        return {
            'status': 'healthy',
            'voice_profiles_count': len(profiles.profiles),
            'models_loaded': True
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }
```

## Backup and Recovery

### 1. Model Backup

```bash
#!/bin/bash
# backup_models.sh

BACKUP_DIR="/backup/presgen-models/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# Backup LivePortrait models
rsync -av LivePortrait/pretrained_weights/ "$BACKUP_DIR/liveportrait/"

# Backup voice profiles
rsync -av presgen-training2/models/voice-profiles/ "$BACKUP_DIR/voice-profiles/"

# Backup configuration
cp .env "$BACKUP_DIR/"
cp oauth_slides_client.json "$BACKUP_DIR/"
cp token_slides.json "$BACKUP_DIR/"
```

### 2. Data Recovery

```bash
#!/bin/bash
# restore_models.sh

BACKUP_DIR="$1"

if [ -z "$BACKUP_DIR" ]; then
    echo "Usage: $0 <backup_directory>"
    exit 1
fi

# Restore LivePortrait models
rsync -av "$BACKUP_DIR/liveportrait/" LivePortrait/pretrained_weights/

# Restore voice profiles
rsync -av "$BACKUP_DIR/voice-profiles/" presgen-training2/models/voice-profiles/

# Restore configuration
cp "$BACKUP_DIR/.env" .
cp "$BACKUP_DIR/oauth_slides_client.json" .
cp "$BACKUP_DIR/token_slides.json" .
```

## Troubleshooting

### Common Issues

#### 1. PyTorch MPS Issues
```bash
# Error: "MPS backend out of memory"
export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0

# Error: "MPS operation not supported"
export PYTORCH_ENABLE_MPS_FALLBACK=1
```

#### 2. LivePortrait Model Loading
```bash
# Verify models downloaded
ls -la LivePortrait/pretrained_weights/liveportrait/

# Re-download if missing
cd LivePortrait && python download_models.py
```

#### 3. Google Slides Authentication
```bash
# Refresh OAuth token
python3 -c "from src.agent.slides_google import authenticate; authenticate()"

# Check token validity
python3 -c "
import json
from datetime import datetime
token = json.load(open('token_slides.json'))
expiry = datetime.fromisoformat(token['expiry'].replace('Z', '+00:00'))
print(f'Token expires: {expiry}')
print(f'Valid: {expiry > datetime.now().astimezone()}')
"
```

### Performance Issues

#### 1. Slow Generation
- Check quality_level setting (use 'fast' for development)
- Verify M1 optimizations are enabled
- Monitor memory usage during generation

#### 2. High Memory Usage
- Enable periodic cache clearing
- Reduce concurrent processing
- Check for memory leaks in long-running processes

## Production Checklist

### Pre-Deployment
- [ ] LivePortrait models downloaded and verified
- [ ] Google OAuth credentials configured and tested
- [ ] Environment variables set for production
- [ ] SSL certificates configured (if applicable)
- [ ] Firewall rules configured
- [ ] Backup strategy implemented

### Post-Deployment
- [ ] Health checks responding correctly
- [ ] All three modes tested in production environment
- [ ] Voice cloning workflow verified
- [ ] Google Slides integration tested with real presentations
- [ ] Performance monitoring active
- [ ] Log rotation configured
- [ ] Alerting system configured

### Ongoing Maintenance
- [ ] Regular model updates
- [ ] OAuth token refresh monitoring
- [ ] Performance metric review
- [ ] Security update schedule
- [ ] Backup verification schedule

## Support and Maintenance

### Contact Information
- **Technical Support:** Development Team
- **Documentation:** Complete project documentation in presgen-training2/
- **Repository:** Git repository with full implementation
- **Issue Tracking:** GitHub Issues (if applicable)

### Maintenance Schedule
- **Daily:** Health check monitoring
- **Weekly:** Performance review and optimization
- **Monthly:** Security updates and model updates
- **Quarterly:** Full system review and backup verification

---

**Status:** ✅ PRODUCTION READY
**Deployment Guide Version:** 1.0
**Last Updated:** September 15, 2025

**Next Steps:**
1. Deploy to production environment following this guide
2. Configure monitoring and alerting systems
3. Conduct final production testing
4. Begin user onboarding and training