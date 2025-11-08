"""add_drive_download_url_to_generated_courses

Revision ID: 008_drive_url
Revises: 6c7d0d3a4b2b
Create Date: 2025-11-08 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008_drive_url'
down_revision = '6c7d0d3a4b2b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add drive_download_url column to generated_courses table
    # This stores the public Google Drive download link for the generated video
    op.add_column(
        'generated_courses',
        sa.Column('drive_download_url', sa.String(1000), nullable=True)
    )


def downgrade() -> None:
    # Remove drive_download_url column
    op.drop_column('generated_courses', 'drive_download_url')
