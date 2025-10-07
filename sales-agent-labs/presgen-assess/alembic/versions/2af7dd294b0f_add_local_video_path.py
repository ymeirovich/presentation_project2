"""add local video path

Revision ID: 2af7dd294b0f
Revises: ce9ec16057c4
Create Date: 2025-10-07 15:53:51.450865

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2af7dd294b0f'
down_revision = 'ce9ec16057c4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'generated_courses',
        sa.Column('local_video_path', sa.String(length=1024), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('generated_courses', 'local_video_path')
