"""add_generated_presentations_table_sprint3

Revision ID: 007_presentations
Revises: 006_gap_analysis
Create Date: 2025-10-02

Sprint 3 Deliverable: Database schema for per-skill presentation generation.

This migration creates the generated_presentations table to support:
- One presentation per skill gap (not one comprehensive presentation)
- Human-readable Drive folder naming (assessment_title + user_email + workflow_id)
- 1:1 mapping between courses and presentations
- Short-form presentations (3-7 minutes, 7-11 slides)
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '007_presentations'
down_revision = '006_gap_analysis'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create generated_presentations table for Sprint 3."""

    # Create generated_presentations table
    op.create_table(
        'generated_presentations',
        sa.Column('id', sa.String(36), primary_key=True),  # UUID as string
        sa.Column('workflow_id', sa.String(36), nullable=False),

        # Skill mapping (ONE presentation per skill)
        sa.Column('skill_id', sa.String(255), nullable=False),
        sa.Column('skill_name', sa.String(500), nullable=False),
        sa.Column('course_id', sa.String(36), nullable=True),  # 1:1 course mapping

        # Drive folder naming (human-readable)
        sa.Column('assessment_title', sa.String(500), nullable=True),
        sa.Column('user_email', sa.String(255), nullable=True),
        sa.Column('drive_folder_path', sa.Text(), nullable=True),

        # Presentation metadata
        sa.Column('presentation_title', sa.String(500), nullable=False),
        sa.Column('presentation_url', sa.Text(), nullable=True),
        sa.Column('download_url', sa.Text(), nullable=True),
        sa.Column('drive_file_id', sa.String(255), nullable=True),
        sa.Column('drive_folder_id', sa.String(255), nullable=True),

        # Generation metadata
        sa.Column('generation_status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('generation_started_at', sa.DateTime(), nullable=True),
        sa.Column('generation_completed_at', sa.DateTime(), nullable=True),
        sa.Column('generation_duration_ms', sa.Integer(), nullable=True),
        sa.Column('estimated_duration_minutes', sa.Integer(), nullable=True),  # 3-7 minutes

        # Job tracking
        sa.Column('job_id', sa.String(36), nullable=True),
        sa.Column('job_progress', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('job_error_message', sa.Text(), nullable=True),

        # Template and content (SHORT-FORM)
        sa.Column('template_id', sa.String(100), nullable=True, server_default='short_form_skill'),
        sa.Column('template_name', sa.String(255), nullable=True, server_default='Skill-Focused Presentation'),
        sa.Column('total_slides', sa.Integer(), nullable=True),  # Expected: 7-11 slides
        sa.Column('content_outline_id', sa.String(36), nullable=True),

        # Metadata
        sa.Column('file_size_mb', sa.Float(), nullable=True),
        sa.Column('thumbnail_url', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),

        # Foreign keys
        sa.ForeignKeyConstraint(['workflow_id'], ['workflow_executions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['course_id'], ['recommended_courses.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['content_outline_id'], ['content_outlines.id'], ondelete='SET NULL'),

        # Check constraints
        sa.CheckConstraint(
            "generation_status IN ('pending', 'generating', 'completed', 'failed', 'cancelled')",
            name='check_generation_status'
        ),
        sa.CheckConstraint(
            'job_progress >= 0 AND job_progress <= 100',
            name='check_job_progress_range'
        ),
    )

    # Create indexes for performance
    op.create_index('idx_presentations_workflow', 'generated_presentations', ['workflow_id'])
    op.create_index('idx_presentations_skill', 'generated_presentations', ['skill_id'])
    op.create_index('idx_presentations_course', 'generated_presentations', ['course_id'])
    op.create_index('idx_presentations_status', 'generated_presentations', ['generation_status'])
    op.create_index('idx_presentations_job', 'generated_presentations', ['job_id'])
    op.create_index('idx_presentations_created', 'generated_presentations', ['created_at'])

    # Note: SQLite doesn't support partial unique indexes like PostgreSQL
    # The unique constraint for (workflow_id, skill_id, status='completed')
    # will be enforced at the application level in the API

    # Create unique index for job_id (only non-null values)
    # SQLite will ignore NULL values in unique indexes by default
    op.create_index('idx_presentations_job_unique', 'generated_presentations', ['job_id'], unique=True)

    # SQLite doesn't support triggers with functions like PostgreSQL
    # The updated_at field will be managed at the application level
    # or via SQLAlchemy's onupdate parameter in the model

    # Update recommended_courses table to add presentation linking
    # Note: presentation_id and presentation_url columns already exist from previous migration
    # Just create the index (foreign key constraint will be enforced at application level)

    op.create_index('idx_courses_presentation', 'recommended_courses', ['presentation_id'])


def downgrade() -> None:
    """Remove generated_presentations table and related changes."""

    # Drop indexes on recommended_courses
    op.drop_index('idx_courses_presentation', table_name='recommended_courses')

    # Note: Not dropping presentation_id and presentation_url columns as they existed before this migration
    # Not dropping foreign key as it wasn't created (SQLite limitation)

    # Drop indexes on generated_presentations
    # Note: idx_presentations_unique_skill_completed was not created (SQLite partial index limitation)
    op.drop_index('idx_presentations_created', table_name='generated_presentations')
    op.drop_index('idx_presentations_job_unique', table_name='generated_presentations')
    op.drop_index('idx_presentations_job', table_name='generated_presentations')
    op.drop_index('idx_presentations_status', table_name='generated_presentations')
    op.drop_index('idx_presentations_course', table_name='generated_presentations')
    op.drop_index('idx_presentations_skill', table_name='generated_presentations')
    op.drop_index('idx_presentations_workflow', table_name='generated_presentations')

    # No triggers to drop for SQLite (triggers not created in upgrade)

    # Drop table
    op.drop_table('generated_presentations')
