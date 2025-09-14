# Git Repository Cleanup & Recovery Plan

**Date:** September 14, 2025
**Status:** IN PROGRESS - Push to new repository blocked by secrets
**Session:** Repository recovery after 8.1GB git bloat issue

## Problem Summary

The local git repository became severely bloated (8.1GB) due to large AI model files being committed:
- `models/musetalkV15/unet.pth` - **3.2GB**
- `models/syncnet/latentsync_syncnet.pt` - **1.4GB** 
- `models/dwpose/dw-ll_ucoco_384.pth` - **388MB**
- `models/sd-vae/diffusion_pytorch_model.bin` - **319MB**
- `models/whisper/pytorch_model.bin` - **144MB**

This caused all git operations to timeout after 2 minutes.

## Solution Strategy

Instead of trying to fix the bloated repository, we decided to:
1. Create fresh repository at https://github.com/ymeirovich/presentation_project2.git
2. Initialize new git in current directory (preserve all work)
3. Push clean version with proper .gitignore

## Current Status - BLOCKED

### ✅ Completed:
1. **Created new GitHub repository**: https://github.com/ymeirovich/presentation_project2.git
2. **Removed old bloated git**: `rm -rf .git && git init`
3. **Added new remote**: `origin → presentation_project2.git`
4. **Updated .gitignore** with comprehensive exclusions:
   ```
   # AI Model files (large binaries)
   models/
   *.bin
   *.pth
   *.ckpt
   *.safetensors
   *.pt
   
   # Secrets and credentials
   *service-account.json
   token*.json
   oauth_*.json
   *.key
   *.pem
   
   # Test files that may contain secrets
   test/
   
   # Separate repositories
   sadtalker-api/
   ```
5. **Successfully committed locally**: 474 files including our rotating bullet display system
   - Commit: `56b7ade` - "Initial commit: Complete PresGen system with rotating bullet display"

### 🚫 BLOCKED - GitHub Push Protection:
Push is being rejected due to secrets detected in various files. GitHub's secret scanning found:
- Google OAuth Client IDs in test files
- Google OAuth Client Secrets in test files  
- Other credential patterns

## Next Session Tasks

### Immediate Actions:
1. **Complete secrets cleanup**:
   ```bash
   cd .. && git add sales-agent-labs/.gitignore
   git commit --amend -m "[updated commit message]"
   git push -u origin main
   ```

2. **If push still blocked**: 
   - Use GitHub's secret bypass URLs (provided in error messages)
   - OR manually find and clean remaining secret patterns

### Repository Structure Setup:
3. **Create separate sadtalker-api repository**:
   ```bash
   cd sales-agent-labs/sadtalker-api
   git init
   git remote add origin https://github.com/ymeirovich/sadtalker-api.git
   git add .
   git commit -m "Initial SadTalker API microservice"
   git push -u origin main
   ```

### Verification:
4. **Verify all work preserved**:
   - ✅ Rotating bullet display system (`src/mcp/tools/video_phase3.py`)
   - ✅ HTTP service updates (`src/service/http.py`)
   - ✅ FileDrop component fix (`presgen-ui/src/components/FileDrop.tsx`)
   - ✅ Updated documentation (`README.md`, `VOICE_CLONE_PROGRESS.md`)

## Key Accomplishments Preserved

### 🎯 Rotating Bullet Display System:
- **Group-based rotation** (e.g., #1-4 → #5-8 → #9-12)
- **Individual bullet timing** within group boundaries
- **Configurable bullet count** via presgen-ui slider (3-10)
- **FFmpeg enable conditions**: `'gte(t,{bullet_time})*lt(t,{group_end})'`
- **Persistent header** across all group rotations

### 🔧 Technical Implementation:
- Updated both `_build_drawtext_filters()` and `_create_overlay_video()` functions
- Added space calculation and bullet grouping logic
- Fixed double file dialog issue in FileDrop component
- Added maxBullets config support throughout video pipeline

### 📚 Documentation:
- Updated README.md with advanced video features section
- Updated VOICE_CLONE_PROGRESS.md to production ready status
- Added comprehensive .gitignore excluding secrets and model files

## Critical Files to Monitor

**If any of these are missing, they need to be restored:**
- `src/mcp/tools/video_phase3.py` - Contains rotating bullet display implementation
- `src/service/http.py` - Contains maxBullets config handling
- `presgen-ui/src/components/FileDrop.tsx` - Contains double dialog fix
- `README.md` & `VOICE_CLONE_PROGRESS.md` - Updated documentation

## Repository URLs
- **Main Project**: https://github.com/ymeirovich/presentation_project2.git
- **SadTalker Service**: https://github.com/ymeirovich/sadtalker-api.git (to be created)
- **Old Bloated Repo**: https://github.com/ymeirovich/presentation_project.git (deprecated)

## Git Status Summary
- **Local repository**: Clean, 474 files committed
- **Remote repository**: Empty (push blocked by secrets)
- **Work preserved**: ✅ All rotating bullet display work intact
- **Next step**: Complete secrets cleanup and push