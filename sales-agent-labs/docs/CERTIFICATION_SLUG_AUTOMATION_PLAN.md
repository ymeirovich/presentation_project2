# Certification Profile Slug Automation Plan

Implement automatic `collection_name` (RAG slug) generation for PresGen-Assess certification profiles, ensure cleanup on deletion, and retain compatibility with Chroma collections.

---

## 1. Baseline Audit

1. Inspect the current ORM model to confirm the `collection_name` column and constraints.  
   ```bash
   sed -n '1,200p' presgen-assess/src/models/certification.py
   ```
2. Locate the API handlers that create/update/delete certification profiles.  
   ```bash
   rg -n "CertificationProfile" presgen-assess/src/service/api/v1/endpoints
   ```

---

## 2. Slug Generation Utility

1. Create `presgen-assess/src/services/slug_utils.py` (or similar shared module) with:
   - `slugify_name(name: str) -> str` to lowercase, replace non-alphanumerics with `-`, limit length, and default to `cert-<uuid>` when the name is unusable.
   - `ensure_unique_slug(session: AsyncSession, base_slug: str) -> str` that checks `CertificationProfile.collection_name` for collisions and appends `-2`, `-3`, etc. as needed.

```python
import re
import uuid
from sqlalchemy import select
from src.models.certification import CertificationProfile

def slugify_name(name: str) -> str:
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    return slug or f'cert-{uuid.uuid4().hex[:8]}'

async def ensure_unique_slug(session, base_slug: str) -> str:
    slug = base_slug
    counter = 2
    while True:
        exists = await session.scalar(
            select(CertificationProfile.id).where(CertificationProfile.collection_name == slug)
        )
        if not exists:
            return slug
        slug = f"{base_slug}-{counter}"
        counter += 1
```

---

## 3. Apply Slug at Creation

1. In the certification profile creation endpoint:
   - After validating the payload but before instantiating the ORM model, set `collection_name` if missing.

```python
from src.services.slug_utils import slugify_name, ensure_unique_slug

if not profile_data.collection_name:
    base_slug = slugify_name(profile_data.name)
    profile_data.collection_name = await ensure_unique_slug(db, base_slug)
```

2. Ensure this runs inside the same transaction as the profile insert to avoid race conditions.
3. Consider adding a DB unique constraint on `collection_name` for extra protection.

---

## 4. Update & Delete Behavior

1. **Updates**  
   - Prevent accidental slug edits: if the update payload tries to change `collection_name`, either reject with `HTTP 400` or require an explicit `force_slug_update` flag.
   - Document that changing the slug will orphan existing Chroma collections unless a migration runs.

2. **Deletes**  
   - After deleting the profile record:
     - Use `ChromaDBCollectionManager` to delete all collections with prefix `assess__{slug}_`.
     - Remove knowledge prompt records referencing the slug.
   - Example delete hook:
     ```python
     if profile.collection_name:
         collection_manager.delete_certification_collections(profile.collection_name)
         await db.execute(
             delete(KnowledgeBasePrompts).where(
                 KnowledgeBasePrompts.collection_name == profile.collection_name
             )
         )
     ```

---

## 5. Backfill Existing Profiles

1. Create `presgen-assess/scripts/backfill_collection_slugs.py` to populate missing slugs.

```python
async with AsyncSessionLocal() as session:
    profiles = (await session.execute(select(CertificationProfile))).scalars()
    for profile in profiles:
        if not profile.collection_name:
            base = slugify_name(profile.name or profile.id)
            profile.collection_name = await ensure_unique_slug(session, base)
    await session.commit()
```

2. Run inside the container:
   ```bash
   docker compose exec presgen-assess python -m scripts.backfill_collection_slugs
   ```
3. If Chroma collections were previously named after UUIDs, either rename them to `assess__<slug>_*` or wipe `data/assess/chroma` and re-ingest content after backfill.

---

## 6. Align Chroma Collection Creation

1. Update `ChromaDBCollectionManager` so `generate_collection_name` takes the slug (not raw UUID) and produces names like `assess__{slug}_v1.0`.
2. Ensure ingestion metadata uses `cert_id=slug` so `_query_with_fallback` filters match.

---

## 7. Testing

1. **Unit Tests**
   - `tests/unit/test_slug_utils.py` covering slug sanitization, uniqueness, and fallback behavior.
2. **Integration Tests**
   - Scenario: create profile → verify slug stored → upload document → confirm Chroma collection uses slug → run RAG query → delete profile → ensure collections and prompts removed.
3. Run:
   ```bash
   cd presentation_project/sales-agent-labs
   pytest -k slug
   ```

---

## 8. Documentation & UI

1. Update `README.md` or runbooks to mention auto-generated slugs and where they appear.
2. Optionally expose the slug (read-only) in the certification profile UI so admins can copy/reference it.
3. Note that manual slug overrides require API access until the UI adds support.

---

## 9. Verification Checklist

1. Create a new certification profile via UI/API → inspect DB (`sqlite3 data/assess/presgen_assess.db "SELECT id, collection_name FROM certification_profiles"`).
2. Upload knowledge files for that profile → check Chroma logs for `assess__<slug>_...`.
3. Run `docker compose exec presgen-assess python -m scripts.debug_chroma_query --collection assess__<slug>_v1.0 --query "sample"` to confirm retrieval.
4. Trigger workflow → ensure `_get_cert_slug` no longer warns and RAG results contain chunks.
5. Delete the profile → verify Chroma collections and knowledge prompts no longer list the slug.
