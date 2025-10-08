"""Add PresGen-Core metadata fields to generated courses

Revision ID: 6c7d0d3a4b2b
Revises: ce9ec16057c4
Create Date: 2026-02-15 10:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6c7d0d3a4b2b"
down_revision: Union[str, None] = "2af7dd294b0f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "generated_courses",
        sa.Column("presgen_core_download_url", sa.String(length=1000), nullable=True),
    )
    op.add_column(
        "generated_courses",
        sa.Column("presgen_core_processing_time_ms", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("generated_courses", "presgen_core_processing_time_ms")
    op.drop_column("generated_courses", "presgen_core_download_url")
