"""add_generated_courses_table_sprint4

Revision ID: ce9ec16057c4
Revises: 007_presentations
Create Date: 2025-10-05 11:35:38.267469

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ce9ec16057c4'
down_revision = '007_presentations'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create generated_courses table for Sprint 4: Individual Skill Course Generation
    op.create_table(
        'generated_courses',
        sa.Column('id', sa.String(32), primary_key=True),
        sa.Column('workflow_id', sa.String(32), sa.ForeignKey('workflow_executions.id'), nullable=False),
        sa.Column('skill_id', sa.String(255), nullable=False),
        sa.Column('skill_name', sa.String(500), nullable=False),
        sa.Column('course_title', sa.String(500), nullable=True),

        # PresGen Integration
        sa.Column('presgen_core_job_id', sa.String(255), nullable=True),
        sa.Column('presgen_avatar_job_id', sa.String(255), nullable=True),
        sa.Column('presentation_url', sa.String(1000), nullable=True),
        sa.Column('video_url', sa.String(1000), nullable=True),

        # Progress & Status
        sa.Column('progress', sa.Integer(), default=0),
        sa.Column('status', sa.String(50), default='pending'),  # pending, generating_presentation, generating_video, completed, failed
        sa.Column('error_message', sa.Text(), nullable=True),

        # Timestamps (SQLite-compatible)
        sa.Column('created_at', sa.DateTime(), server_default='CURRENT_TIMESTAMP'),
        sa.Column('updated_at', sa.DateTime(), server_default='CURRENT_TIMESTAMP'),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
    )

    # Create indexes for performance
    op.create_index('ix_generated_courses_workflow_id', 'generated_courses', ['workflow_id'])
    op.create_index('ix_generated_courses_skill_id', 'generated_courses', ['skill_id'])
    op.create_index('ix_generated_courses_status', 'generated_courses', ['status'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_generated_courses_status', table_name='generated_courses')
    op.drop_index('ix_generated_courses_skill_id', table_name='generated_courses')
    op.drop_index('ix_generated_courses_workflow_id', table_name='generated_courses')

    # Drop table
    op.drop_table('generated_courses')