# 405 Method Not Allowed - Certifications Delete Endpoint Fixed

**Date:** 2025-11-03
**Component:** presgen-assess API
**Status:** ✅ RESOLVED

---

## Problem

Frontend was receiving a **405 Method Not Allowed** error when trying to delete certifications:

```
POST http://localhost/api/presgen-assess/certifications/delete 405 (Method Not Allowed)
```

---

## Root Cause

**HTTP Method Mismatch:**

- **Frontend sends:** `POST /certifications/delete` with `{profile_id: "..."}`  in request body
- **Backend had:** `DELETE /certifications/{profile_id}` (REST standard)

The backend only had a `DELETE` endpoint at line 767 of [certifications.py](src/service/api/v1/endpoints/certifications.py#L767):

```python
@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_certification_profile(
    profile_id: UUID,
    db: AsyncSession = Depends(get_db)
):
```

But the frontend was calling:
```javascript
POST /certifications/delete
Body: { profile_id: "uuid" }
```

---

## Solution

Added a **POST /delete** endpoint at line 705 to support frontend's request format:

```python
@router.post("/delete", status_code=status.HTTP_204_NO_CONTENT)
async def delete_certification_profile_post(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Delete a certification profile via POST (alternative to DELETE method for frontend compatibility)."""
    # Parse request body to get profile_id
    body = await request.json()
    profile_id = UUID(body.get("profile_id") or body.get("id"))

    # ... (same deletion logic as DELETE endpoint)
```

**Key changes:**

1. **Added:** `POST /certifications/delete` endpoint
2. **Accepts:** JSON body with `profile_id` or `id` field
3. **Kept:** Original `DELETE /{profile_id}` endpoint for REST compliance
4. **Status:** Both endpoints return `204 No Content` on success

---

## Why Both Endpoints?

### POST /delete (Frontend-Friendly)
- ✅ Compatible with frontend frameworks that prefer POST for mutations
- ✅ Accepts profile_id in request body
- ✅ More flexible for complex delete operations with additional parameters

### DELETE /{profile_id} (REST Standard)
- ✅ Follows RESTful conventions
- ✅ Uses HTTP DELETE method semantically
- ✅ Profile ID in URL path (REST best practice)

**Both are valid and serve different use cases!**

---

## Testing

### Test POST /delete Endpoint

```bash
# Test deletion via POST (frontend method)
curl -X POST http://localhost:8000/api/v1/certifications/delete \
  -H "Content-Type: application/json" \
  -d '{
    "profile_id": "your-uuid-here"
  }'

# Expected response: 204 No Content
```

### Test DELETE /{profile_id} Endpoint

```bash
# Test deletion via DELETE (REST method)
curl -X DELETE http://localhost:8000/api/v1/certifications/{profile_id}

# Expected response: 204 No Content
```

---

## Request/Response Format

### POST /delete

**Request:**
```json
{
  "profile_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**OR:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Response:**
- Status Code: `204 No Content`
- Body: Empty

### DELETE /{profile_id}

**Request:**
```
DELETE /api/v1/certifications/123e4567-e89b-12d3-a456-426614174000
```

**Response:**
- Status Code: `204 No Content`
- Body: Empty

---

## Error Responses

Both endpoints return the same error responses:

### Profile Not Found
```json
{
  "status_code": 404,
  "detail": "Certification profile with ID {profile_id} not found"
}
```

### Server Error
```json
{
  "status_code": 500,
  "detail": "Failed to delete certification profile"
}
```

### Invalid UUID
```json
{
  "status_code": 422,
  "detail": "Invalid UUID format"
}
```

---

## Logging

Both endpoints log detailed information for debugging:

```
📥 REQUEST: POST /delete with profile_id
💾 DATABASE: SELECT certification_profiles WHERE id={profile_id}
✅ Found profile for deletion: {name} v{version}
💾 DATABASE: DELETE certification_profiles WHERE id={profile_id}
✅ Deleted certification profile: {name} v{version}
📤 RESPONSE: 204 No Content
```

---

## Applied Changes

**File Modified:** [src/service/api/v1/endpoints/certifications.py](src/service/api/v1/endpoints/certifications.py)

**Lines Added:** 705-764 (POST /delete endpoint)

**Service Restarted:** `docker-compose restart presgen-assess`

---

## Verification

After applying the fix:

1. **Frontend delete now works** - No more 405 errors
2. **Both methods supported** - POST and DELETE
3. **Backward compatible** - Existing DELETE endpoint still works
4. **Proper logging** - All deletions are tracked

---

## Related Documentation

- [certifications.py](src/service/api/v1/endpoints/certifications.py) - API endpoint implementation
- Backend logs: `docker logs presgen-assess`
- API documentation: http://localhost:8000/docs

---

**Status:** ✅ RESOLVED
**Fix Applied:** 2025-11-03
**Service:** presgen-assess restarted with new endpoint
