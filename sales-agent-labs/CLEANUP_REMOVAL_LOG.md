# Repository Cleanup Removal Log
*Generated: 2025-09-20*

This document tracks all files and directories removed during the comprehensive cleanup process for rollback purposes.

## Phase 1: Cache and System Files (COMPLETED)
**Committed in:** 248d679

### Removed:
- **49 .DS_Store files** - macOS system files scattered throughout repository
- **2,772 __pycache__ directories** - Python bytecode cache
- **All .pyc files** - Python compiled bytecode
- **81 cache files from out/state/cache/** including:
  - 61 imagen cache files (out/state/cache/imagen/*.json)
  - 16 llm_summarize cache files (out/state/cache/llm_summarize/*.json)

### Space Recovered: ~200MB

## Phase 2: SadTalker and MuseTalk Models (PENDING)

### To Be Removed:
- **sadtalker-api/ directory (51MB)**
  - Complete SadTalker API implementation
  - Superseded by MuseTalk integration

- **MuseTalk model cache files:**
  - `models/.cache/huggingface/download/musetalk/`
  - `models/.cache/huggingface/download/musetalkV15/`
  - Associated lock and metadata files

### Preserved:
- `start_presgen_with_musetalk.sh` - Active MuseTalk integration script
- LivePortrait/ directory - Current active video generation system
- Core MuseTalk integration code in presgen-training2/

## Phase 3: Debug and Temp Files (PENDING)

### To Be Removed:
- **Debug scripts (root level):**
  - `debug_drive_upload.py`
  - `debug_ffmpeg.py`
  - `debug_openmp.py`
  - `debug_speaker_notes.py`
  - `debug_upload_test.py`
  - `comprehensive_speaker_notes_test.py`

- **Temp artifacts:**
  - `temp/training_*` directories (stale training sessions)
  - `temp/test-*` directories (test artifacts)
  - `temp/*.log` files

- **Obsolete config:**
  - `temp_config.yaml`

### Preserved:
- All .md documentation files (per user request)
- Active configuration files
- Current temp/ processing artifacts

## Rollback Instructions

### To restore removed cache files:
```bash
git checkout HEAD~1 -- out/state/cache/
```

### To restore SadTalker (when removed):
```bash
git checkout HEAD~n -- sadtalker-api/
git checkout HEAD~n -- models/.cache/huggingface/download/musetalk*
```

### To restore debug files (when removed):
```bash
git checkout HEAD~n -- debug_*.py comprehensive_speaker_notes_test.py
```

## Notes
- Each phase is committed separately for granular rollback capability
- All removals preserve current system functionality
- LivePortrait and presgen-training2 systems remain intact
- MuseTalk integration script preserved for active use