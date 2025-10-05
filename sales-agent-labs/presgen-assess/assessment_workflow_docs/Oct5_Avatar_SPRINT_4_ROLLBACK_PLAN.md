# Sprint 4: Rollback Plan & Change Documentation

**Created**: 2025-10-05
**Purpose**: Document all changes for easy rollback if needed

## 🔄 Rollback Strategy

### Quick Rollback Command
```bash
# If anything breaks, rollback to this commit:
git log --oneline | head -1  # Current stable commit before Sprint 4

# To rollback:
git reset --hard <commit-hash>
git push --force-with-lease
```

### Current Stable State
- **Last Stable Commit**: `e0778e0` - Fix workflow progression: Implement question-answer validation pipeline
- **Database State**: All migrations up to `007_add_generated_presentations_table_sprint3.py` applied
- **Working Features**:
  - ✅ Gap Analysis → Content Outlines → Recommended Courses → Presentations
  - ✅ Question-answer validation
  - ✅ Order-based response matching

---

## 📝 Phase 1: Database Schema Changes

### Change 1.1: Create Migration File
**File**: `alembic/versions/008_add_generated_courses_table_sprint4.py`

**Action**: CREATE NEW FILE
**Risk**: LOW (new migration, doesn't modify existing tables)

**Rollback**:
```bash
# If migration fails or causes issues:
alembic downgrade -1

# Or delete the migration file:
rm alembic/versions/008_add_generated_courses_table_sprint4.py
```

**Pre-execution Backup**:
```bash
# Backup database before migration
cp test_database.db test_database.db.backup-before-sprint4-$(date +%Y%m%d-%H%M%S)
```

### Change 1.2: Create SQLAlchemy Model
**File**: `src/models/generated_course.py`

**Action**: CREATE NEW FILE
**Risk**: LOW (new model, no changes to existing models)

**Rollback**:
```bash
# If model causes import errors:
rm src/models/generated_course.py
# Restart server - imports will work without this file
```

**Safety Check Before Creating**:
```bash
# Verify no existing generated_course.py
ls src/models/generated_course.py 2>/dev/null && echo "⚠️ File exists!" || echo "✅ Safe to create"
```

---

## 📝 Phase 2: PresGen-Avatar Client Changes

### Change 2.1: Create Avatar Client Directory
**Directory**: `src/integrations/presgen_avatar/`

**Action**: CREATE NEW DIRECTORY
**Risk**: LOW (new integration, isolated from existing code)

**Files to Create**:
- `src/integrations/presgen_avatar/__init__.py`
- `src/integrations/presgen_avatar/client.py`
- `src/integrations/presgen_avatar/schemas.py`

**Rollback**:
```bash
# Remove entire directory if issues occur:
rm -rf src/integrations/presgen_avatar/
```

**Safety Check**:
```bash
# Verify directory doesn't exist
ls -d src/integrations/presgen_avatar 2>/dev/null && echo "⚠️ Already exists!" || echo "✅ Safe to create"
```

---

## 📝 Phase 3: Enhanced Logging Changes

### Change 3.1: Course Generation Service
**File**: `src/services/course_generation_service.py`

**Action**: CREATE NEW FILE
**Risk**: LOW (new service, no modifications to existing services)

**Rollback**:
```bash
rm src/services/course_generation_service.py
```

### Change 3.2: Logs Directory
**Directory**: `logs/`

**Action**: CREATE DIRECTORY (if not exists)
**Risk**: NONE (directory only, no code impact)

**Created Files**:
- `logs/course_generation.log` (auto-created by logging)

**Rollback**: Not needed (logs are data, not code)

---

## 📝 Phase 4: API Endpoint Changes

### Change 4.1: Modify workflows.py
**File**: `src/service/api/v1/endpoints/workflows.py`

**Action**: ADD NEW ENDPOINTS (append only, no modifications to existing endpoints)
**Risk**: MEDIUM (modifies existing file)

**Backup Strategy**:
```bash
# Create backup before editing
cp src/service/api/v1/endpoints/workflows.py \
   src/service/api/v1/endpoints/workflows.py.backup-sprint4
```

**New Endpoints to Add** (line numbers will be documented):
1. `POST /{workflow_id}/skills/{skill_id}/generate-course`
2. `GET /{workflow_id}/courses/{course_id}/status`
3. `GET /{workflow_id}/courses`

**Rollback**:
```bash
# Restore from backup:
cp src/service/api/v1/endpoints/workflows.py.backup-sprint4 \
   src/service/api/v1/endpoints/workflows.py

# Restart server
```

### Change 4.2: Add Response Schemas
**File**: `src/schemas/course_generation.py`

**Action**: CREATE NEW FILE
**Risk**: LOW (new schemas file)

**Rollback**:
```bash
rm src/schemas/course_generation.py
```

---

## 📝 Phase 5: Frontend Changes

### Change 5.1: Frontend Components
**Files** (to be created/modified):
- `presgen-ui/src/components/assess/RecommendedCoursesTab.tsx` (MODIFY)
- `presgen-ui/src/lib/assess-api.ts` (ADD functions)

**Backup Strategy**:
```bash
# Backup before modifying
cp presgen-ui/src/components/assess/RecommendedCoursesTab.tsx \
   presgen-ui/src/components/assess/RecommendedCoursesTab.tsx.backup-sprint4
```

**Rollback**:
```bash
# Restore frontend files
cp presgen-ui/src/components/assess/RecommendedCoursesTab.tsx.backup-sprint4 \
   presgen-ui/src/components/assess/RecommendedCoursesTab.tsx
```

---

## 🛡️ Safety Measures

### Pre-Implementation Checklist
- [x] Document current stable commit hash
- [ ] Backup database before migration
- [ ] Backup workflows.py before modifications
- [ ] Create feature branch for Sprint 4
- [ ] Test rollback procedure

### During Implementation
- [ ] Create files incrementally (one phase at a time)
- [ ] Test after each phase before proceeding
- [ ] Keep backups of all modified files
- [ ] Document line numbers of changes

### Post-Implementation Testing
- [ ] Verify existing workflows still work
- [ ] Test gap analysis → outlines → courses → presentations
- [ ] Run manual TDD tests
- [ ] Check logs for errors

---

## 🔧 Rollback Procedures

### Level 1: File-Level Rollback (Safest)
```bash
# Rollback specific file
cp <file>.backup-sprint4 <file>
```

### Level 2: Migration Rollback
```bash
# Rollback last migration
alembic downgrade -1

# Or restore database
cp test_database.db.backup-before-sprint4-* test_database.db
```

### Level 3: Git Rollback (Nuclear Option)
```bash
# Rollback all Sprint 4 changes
git reset --hard e0778e0
git clean -fd
```

### Level 4: Service Restart
```bash
# Sometimes just restarting fixes issues
pkill -f "uvicorn.*8000"
./venv/bin/uvicorn src.service.app:app --reload --port 8000
```

---

## 📊 Change Log

### 2025-10-05 - Pre-Sprint 4
- **Status**: Stable
- **Commit**: e0778e0
- **Features Working**: All Sprint 3+ features operational

### 2025-10-05 - Phase 1 Start
- **Changes**: TBD
- **Files Modified**: TBD
- **Rollback Tested**: TBD

---

## ⚠️ Known Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Migration breaks database | HIGH | Backup DB before migration, test downgrade |
| New endpoints conflict with existing | MEDIUM | Use unique paths, test existing endpoints |
| Import errors from new models | MEDIUM | Isolate new code, optional imports |
| Frontend breaks existing UI | LOW | Backup components, feature flag |
| Logging fills disk | LOW | Rotate logs, 10MB limit |

---

## 🧪 Rollback Test Plan

### Test 1: Migration Rollback
```bash
# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1

# Verify
sqlite3 test_database.db "SELECT name FROM sqlite_master WHERE type='table';"
# Should NOT show 'generated_courses'
```

### Test 2: File Rollback
```bash
# Make backup
cp src/service/api/v1/endpoints/workflows.py workflows.py.backup

# Modify file
echo "# test change" >> src/service/api/v1/endpoints/workflows.py

# Rollback
cp workflows.py.backup src/service/api/v1/endpoints/workflows.py

# Verify
git diff src/service/api/v1/endpoints/workflows.py
# Should show no changes
```

### Test 3: Full Git Rollback
```bash
# Create test branch
git checkout -b sprint4-test

# Make changes
touch test-file.txt
git add test-file.txt
git commit -m "test"

# Rollback
git reset --hard HEAD~1

# Verify
ls test-file.txt
# Should not exist
```

---

## 📞 Emergency Contacts

**If rollback fails**:
1. Check this document for appropriate rollback level
2. Verify backups exist before executing rollback
3. Test in separate terminal before production rollback
4. Document what went wrong for future reference

---

**Document Status**: Active Safety Net
**Last Updated**: 2025-10-05
**Purpose**: Ensure Sprint 4 changes are reversible
