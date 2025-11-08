#!/usr/bin/env python
"""
Populate missing certification collection slugs and align knowledge base paths.

Usage:
    docker compose exec presgen-assess python -m scripts.backfill_collection_slugs
"""

import asyncio
from typing import List

from sqlalchemy import select

from src.models.certification import CertificationProfile
from src.service.database import AsyncSessionLocal
from src.services.slug_utils import slugify_name, ensure_unique_slug


async def _backfill() -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(CertificationProfile))
        profiles: List[CertificationProfile] = result.scalars().all()

        updated = 0
        for profile in profiles:
            if profile.collection_name:
                continue

            base_slug = slugify_name(f"{profile.name}-{profile.version}")
            profile.collection_name = await ensure_unique_slug(session, base_slug)
            profile.knowledge_base_path = f"knowledge_base/{profile.collection_name}"
            updated += 1

        if updated:
            await session.commit()

        print(f"✅ Backfill completed. Updated {updated} certification profiles.")


def main() -> None:
    asyncio.run(_backfill())


if __name__ == "__main__":
    main()
