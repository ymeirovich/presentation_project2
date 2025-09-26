# Assessment Prompt Debugging Analysis

## Problem Summary
User reports that when saving an assessment prompt value of "12345", the form confirms success but reloading the profile shows the default AWS prompt instead of the saved value.

## Root Cause Analysis

### Issue 1: UUID JSON Serialization Error (FIXED ✅)
**Problem**: API was failing with `TypeError: Object of type UUID is not JSON serializable`
**Location**: `certifications.py:89` in `log_response_details()`
**Cause**: UUID objects were not being converted to strings before JSON serialization
**Fix**: Modified `log_response_details()` to convert UUID to string: `str(data_dict.get("id"))`

### Issue 2: Missing Prompt Fields in Pydantic Schema (FIXED ✅)
**Problem**: Prompt fields were not included in the `CertificationProfileBase` schema
**Location**: `src/schemas/certification.py`
**Cause**: The API response construction included prompt fields but the Pydantic model didn't define them
**Fix**: Added missing fields to schema:
```python
assessment_prompt: Optional[str] = Field(None, description="Assessment prompt for generating questions")
presentation_prompt: Optional[str] = Field(None, description="Presentation prompt for generating learning materials")
gap_analysis_prompt: Optional[str] = Field(None, description="Gap analysis prompt for knowledge assessment")
```

### Issue 3: Inconsistent API Response Construction (FIXED ✅)
**Problem**: Different endpoints returned different fields, causing schema validation failures
**Locations**:
- `create_certification_profile()` - Missing prompt fields
- `list_certification_profiles()` - Missing prompt fields
- `update_certification_profile()` - Had prompt fields ✅
- `get_certification_profile()` - Had prompt fields ✅

**Fix**: Added prompt fields to all endpoint responses:
```python
# Include prompt fields from database columns
'assessment_prompt': profile.assessment_prompt,
'presentation_prompt': profile.presentation_prompt,
'gap_analysis_prompt': profile.gap_analysis_prompt
```

### Issue 4: Update Schema Dropping Prompt Fields (FIXED ✅)
**Problem**: `CertificationProfileUpdate` schema omitted the prompt and `resource_binding_enabled` fields, so Pydantic stripped them from incoming requests.
**Location**: `src/schemas/certification.py`
**Evidence**:
- Browser network inspector confirms PUT payload includes `assessment_prompt: "12345"`.
- Backend warning (`update_certification_profile:536`) logs `⚠️ Prompt fields missing from validated payload` and shows only `['name', 'version', 'exam_domains']` surviving validation.
**Fix**: Added the missing optional fields to `CertificationProfileUpdate`, allowing the prompts (and resource binding flag) to reach the persistence layer.

### Issue 5: Next.js Proxy Stripping Prompt Fields (FIXED ✅)
**Problem**: The frontend proxy (`presgen-ui/src/app/api/presgen-assess/certifications/[id]/route.ts`) rebuilt the PUT payload with only `name`, `version`, and `exam_domains`, overwriting prompts and crashing when those fields were omitted.
**Evidence**: Proxy log showed `Update data received` with only prompt fields, followed by `TypeError: Cannot read properties of undefined (reading 'toLowerCase')` and backend logs updating just three fields.
**Fix**: Updated the proxy to forward only defined fields, guard the `knowledge_base_path` fallback, and include prompt columns at the top level so the backend persists them.

## Current Status

### What's Working ✅
1. **No more JSON serialization errors** - UUIDs are properly converted to strings
2. **No more schema validation errors** - All endpoints include prompt fields
3. **Database contains prompt values** - Default prompts exist in database:
   - Assessment: "Generate comprehensive AWS Machine Learning assessment questions..."
   - Presentation: "Create engaging AWS Machine Learning learning presentations..."
   - Gap Analysis: "Analyze AWS Machine Learning knowledge gaps..."

### What's Still Broken ❌
**Primary Issue**: User-entered prompt values are not being persisted to the database

**Evidence (pre-fix)**:
1. **Frontend logs / network inspector**: PUT payload includes `assessment_prompt: "12345"` (full request captured on 2025-09-25 22:34:01).
2. **Backend warning**: `⚠️ Prompt fields missing from validated payload` (same timestamp) shows prompts dropped during Pydantic validation.
3. **Database update log**: `prompt_fields` all `"NOT_SET"`, confirming the values never reached the ORM update.
4. **API response**: Still returns the default prompt text from the database.

**Post-fix expectation**: After the schema and proxy fixes, re-saving should persist the custom prompt. Needs verification.

## Next Steps Required

### Investigation Needed 🔍
1. **Verify persistence after schema fix**: Submit a new prompt value and confirm it survives reload.
2. **Double-check ORM persistence**: Ensure SQLAlchemy model reflects the new values (inspect DB or log `profile.assessment_prompt` before commit).

### Suspected Issues (resolved) 🤔
- Frontend payload is correct; problem was backend validation stripping fields.
- New logging confirms when prompt fields are missing; should now stay quiet once fix is validated.

### Follow-up Steps 📋
1. Re-run the PUT request with a distinct prompt (e.g., "12345" or timestamp) and confirm no warning logs appear.
2. Inspect `certifications.log` / database state to verify prompts update.
3. Remove or downgrade the temporary warning once behaviour is confirmed.

## Technical Details

### Database Schema
Prompt fields are nullable `Text` columns in `certification_profiles` table:
```sql
assessment_prompt TEXT,
presentation_prompt TEXT,
gap_analysis_prompt TEXT
```

### API Endpoints Status
- ✅ `POST /` (create) - Includes prompt fields
- ✅ `GET /` (list) - Includes prompt fields
- ✅ `GET /{id}` (get) - Includes prompt fields
- ✅ `PUT /{id}` (update) - Includes prompt fields
- ✅ `GET /search/{name}` (search) - Uses model_validate (should work)
- ✅ `POST /{id}/duplicate` (duplicate) - Uses model_validate (should work)

## Files Modified
1. `src/service/api/v1/endpoints/certifications.py` - Fixed logging, API responses, and added payload-drop warning.
2. `src/schemas/certification.py` - Added prompt and resource binding fields to the update schema.
3. `presgen-ui/src/app/api/presgen-assess/certifications/[id]/route.ts` - Proxy now forwards prompt fields safely and avoids empty-field crashes.

## Testing Required
1. Try saving "12345" (or another unique value) again and confirm the API response echoes it.
2. Check backend logs for absence of the payload-drop warning during the update and ensure the proxy logs include the persisted prompts.
3. Verify the database reflects the new prompt value.
