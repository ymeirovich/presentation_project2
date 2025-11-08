"""Utilities for generating and validating certification collection slugs."""

from __future__ import annotations

import re
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.certification import CertificationProfile

SLUG_MAX_LENGTH = 80


def slugify_name(value: Optional[str]) -> str:
    """Create a filesystem/API-safe slug from the provided value."""
    if not value:
        return f"cert-{uuid.uuid4().hex[:8]}"

    normalized = value.lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    normalized = normalized.strip("-")

    if not normalized:
        normalized = f"cert-{uuid.uuid4().hex[:8]}"

    return normalized[:SLUG_MAX_LENGTH]


async def ensure_unique_slug(db: AsyncSession, base_slug: str) -> str:
    """
    Ensure the slug is unique within certification_profiles.

    Appends a numeric suffix if necessary.
    """
    slug = base_slug
    counter = 2

    while True:
        existing = await db.scalar(
            select(CertificationProfile.id).where(CertificationProfile.collection_name == slug)
        )
        if existing is None:
            return slug

        slug = f"{base_slug}-{counter}"[:SLUG_MAX_LENGTH]
        counter += 1
