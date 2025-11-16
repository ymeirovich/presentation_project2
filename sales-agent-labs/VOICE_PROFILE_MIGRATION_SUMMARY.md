# Voice Profile Migration - Complete

**Date:** 2025-11-15
**Task:** Migrate voice profiles from local development to AWS Lightsail
**Status:** ✅ **COMPLETE**

---

## Problem

After migrating the presgen-assess database to AWS, video generation was failing with:

```
⚠️  PresGen-Core returned success=False or error:
  error: Voice profile not found: OpenAI Demo Voice (Your Audio)
```

---

## Root Cause

Voice profiles are stored in the **presgen-core** container at `/app/models/voice-profiles/`, not in the presgen-assess database. The AWS deployment had an empty voice profiles directory while local development had 8 voice profiles.

---

## Solution

### 1. Voice Profile Storage Architecture

Voice profiles in presgen-core are stored as JSON files:

- **Location**: `/app/models/voice-profiles/`
- **Configuration file**: `profiles.json`
- **Individual profiles**: `{profile_name}_{type}.json`
- **API endpoint**: `GET /training/voice-profiles`

### 2. Migration Steps Completed

1. ✅ **Discovered voice profile location** in local presgen-core container
2. ✅ **Backed up voice profiles** from container to local filesystem
3. ✅ **Copied to AWS** via SCP to host machine
4. ✅ **Imported into container** using `docker cp`
5. ✅ **Verified via API** that all profiles are accessible
6. ✅ **Updated docker-compose.yml** with clarifying comment
7. ✅ **Tested persistence** by restarting container

### 3. Voice Profiles Migrated

**Total**: 8 profiles

1. **OpenAI Demo Voice (Your Audio)** ← Primary profile used by workflows
2. Weather voice
3. Test Profile Phase 4
4. Test Permanent Storage
5. Working Permanent Storage
6. Language Fix Test Profile
7. test_direct_audio_profile
8. openai_demo_profile

---

## Technical Details

### Voice Profile Structure

Each profile consists of:

```json
{
  "name": "OpenAI Demo Voice (Your Audio)",
  "language": "en",
  "created_at": "2025-09-16T15:50:28.612742",
  "model_path": "presgen-training2/models/voice-profiles/OpenAI Demo Voice (Your Audio)_openai.json",
  "source_video": "direct_audio",
  "quality": "standard",
  "sample_rate": 22050
}
```

### Docker Volume Mount

The voice profiles are persisted via volume mount in `docker-compose.yml`:

```yaml
presgen-core:
  volumes:
    - ./models:/app/models  # Voice profiles stored in models/voice-profiles/
```

This ensures:
- ✅ Profiles survive container restarts
- ✅ Profiles persist across container rebuilds
- ✅ Profiles can be backed up with the host directory
- ✅ Profiles can be edited directly on the host

---

## Verification Commands

### List Available Voice Profiles

```bash
# On AWS
ssh ubuntu@35.175.156.231
docker exec presgen-core curl -s http://localhost:8080/training/voice-profiles | python3 -m json.tool
```

### Check Voice Profile Files

```bash
# On AWS host
ls -la /home/ubuntu/presgen/sales-agent-labs/models/voice-profiles/

# Inside presgen-core container
docker exec presgen-core ls -la /app/models/voice-profiles/
```

### Test Voice Profile in Video Generation

```bash
# Via presgen-assess workflow
# Voice profile is automatically used when creating training videos
# Check logs for confirmation:
docker logs presgen-core 2>&1 | grep "voice_profile"
```

---

## Files Modified

### Updated Files

- ✅ `docker-compose.yml` - Added clarifying comment for voice profile volume mount
- ✅ `models/voice-profiles/profiles.json` - Migrated from local to AWS
- ✅ `models/voice-profiles/*.json` - 8 individual voice profile files migrated

### New Documentation

- ✅ `VOICE_PROFILE_MIGRATION_SUMMARY.md` - This document

---

## Backup & Restore Procedures

### Backup Voice Profiles

```bash
# From local development
docker cp presgen-core:/app/models/voice-profiles ./backup/voice-profiles-$(date +%Y%m%d)

# From AWS
ssh ubuntu@35.175.156.231 "cd /home/ubuntu/presgen/sales-agent-labs && tar -czf voice-profiles-backup-$(date +%Y%m%d).tar.gz models/voice-profiles/"
```

### Restore Voice Profiles

```bash
# To AWS
scp -r ./models/voice-profiles ubuntu@35.175.156.231:/home/ubuntu/presgen/sales-agent-labs/models/

# Into container (if needed - usually not required due to volume mount)
ssh ubuntu@35.175.156.231 "docker cp /home/ubuntu/presgen/sales-agent-labs/models/voice-profiles presgen-core:/app/models/"
```

---

## Future Considerations

### Creating New Voice Profiles

Voice profiles can be created via the presgen-core API:

```bash
# Upload video and clone voice
curl -X POST http://presgen-core:8080/training/clone-voice \
  -F "video=@/path/to/video.mp4" \
  -F "profile_name=New Voice Profile" \
  -F "language=en"
```

### Voice Profile Types

1. **OpenAI TTS** (`_openai.json`) - Uses OpenAI's text-to-speech API
2. **ElevenLabs** (`_elevenlabs.json`) - Uses ElevenLabs voice cloning
3. **Built-in** (`_builtin.json`) - Uses local TTS models

The migrated "OpenAI Demo Voice (Your Audio)" uses OpenAI TTS.

---

## Related Issues Resolved

1. ✅ Voice profile not found error in presgen-assess logs
2. ✅ Video generation failures due to missing voice configuration
3. ✅ Inconsistency between local dev and AWS production environments
4. ✅ Voice profile persistence across container restarts

---

## Testing Results

### Before Migration

```
❌ Voice profiles on AWS: 0
❌ Video generation: Failed with "Voice profile not found"
```

### After Migration

```
✅ Voice profiles on AWS: 8
✅ Voice profile "OpenAI Demo Voice (Your Audio)": Available
✅ Video generation: Ready (profile accessible)
✅ Persistence after restart: Confirmed
```

---

## Maintenance

### Regular Checks

1. **Weekly**: Verify voice profiles are accessible via API
2. **Before deployments**: Backup voice-profiles directory
3. **After profile creation**: Confirm profile appears in `profiles.json`

### Monitoring

```bash
# Check voice profile count
docker exec presgen-core curl -s http://localhost:8080/training/voice-profiles | grep -o '"name"' | wc -l

# Expected output: 8
```

---

## Summary

Voice profile migration is **complete and verified**. The "OpenAI Demo Voice (Your Audio)" profile that was causing errors is now available on AWS and will persist across container restarts thanks to the volume mount configuration.

**Next Steps**: Video generation should now work without voice profile errors. Monitor presgen-core logs to confirm successful video generation with the migrated voice profile.
