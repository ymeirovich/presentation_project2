"""add_gap_analysis_tables_sprint0

Revision ID: 006_gap_analysis
Revises: 005_chromadb_integration
Create Date: 2025-09-30

Sprint 0 Deliverable: Database schema for Gap Analysis persistence.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006_gap_analysis'
down_revision = '005_chromadb_integration'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create Gap Analysis tables."""

    # Create gap_analysis_results table
    op.create_table(
        'gap_analysis_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workflow_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Overall performance metrics
        sa.Column('overall_score', sa.Float(), nullable=False),
        sa.Column('total_questions', sa.Integer(), nullable=False),
        sa.Column('correct_answers', sa.Integer(), nullable=False),
        sa.Column('incorrect_answers', sa.Integer(), nullable=False),

        # Skill gaps and performance by domain
        sa.Column('skill_gaps', sa.JSON(), nullable=False),
        sa.Column('performance_by_domain', sa.JSON(), nullable=False),
        sa.Column('severity_scores', sa.JSON(), nullable=False),

        # Text summary (plain language explanation)
        sa.Column('text_summary', sa.Text(), nullable=False),

        # Charts data for dashboard
        sa.Column('charts_data', sa.JSON()),

        # Metadata
        sa.Column('certification_profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()')),

        # Foreign keys
        sa.ForeignKeyConstraint(['workflow_id'], ['workflow_executions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('ix_gap_analysis_workflow_id', 'gap_analysis_results', ['workflow_id'])
    op.create_index('ix_gap_analysis_cert_profile', 'gap_analysis_results', ['certification_profile_id'])

    # Create content_outlines table
    op.create_table(
        'content_outlines',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('gap_analysis_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workflow_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Skill gap information
        sa.Column('skill_id', sa.String(255), nullable=False),
        sa.Column('skill_name', sa.String(500), nullable=False),
        sa.Column('exam_domain', sa.String(255), nullable=False),
        sa.Column('exam_guide_section', sa.String(500), nullable=False),

        # RAG-retrieved content
        sa.Column('content_items', sa.JSON(), nullable=False),
        sa.Column('rag_retrieval_score', sa.Float(), nullable=False),

        # Metadata
        sa.Column('retrieved_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()')),

        # Foreign keys
        sa.ForeignKeyConstraint(['gap_analysis_id'], ['gap_analysis_results.id'], ),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflow_executions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('ix_content_outlines_gap_analysis_id', 'content_outlines', ['gap_analysis_id'])
    op.create_index('ix_content_outlines_workflow_id', 'content_outlines', ['workflow_id'])
    op.create_index('ix_content_outlines_skill_id', 'content_outlines', ['skill_id'])

    # Create recommended_courses table
    op.create_table(
        'recommended_courses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('gap_analysis_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workflow_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Skill gap information
        sa.Column('skill_id', sa.String(255), nullable=False),
        sa.Column('skill_name', sa.String(500), nullable=False),
        sa.Column('exam_domain', sa.String(255), nullable=False),
        sa.Column('exam_subsection', sa.String(500)),

        # Course information
        sa.Column('course_title', sa.String(500), nullable=False),
        sa.Column('course_description', sa.Text(), nullable=False),
        sa.Column('estimated_duration_minutes', sa.Integer(), nullable=False),
        sa.Column('difficulty_level', sa.String(50), nullable=False),

        # Course outline
        sa.Column('learning_objectives', sa.JSON(), nullable=False),
        sa.Column('content_outline', sa.JSON(), nullable=False),

        # PresGen-Avatar generation status
        sa.Column('generation_status', sa.String(50), server_default='pending'),
        sa.Column('generation_started_at', sa.DateTime(timezone=True)),
        sa.Column('generation_completed_at', sa.DateTime(timezone=True)),
        sa.Column('generation_error', sa.Text()),

        # Generated course resources
        sa.Column('video_url', sa.Text()),
        sa.Column('presentation_url', sa.Text()),
        sa.Column('download_url', sa.Text()),

        # Metadata
        sa.Column('priority', sa.Integer(), server_default='0'),
        sa.Column('recommended_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()')),

        # Foreign keys
        sa.ForeignKeyConstraint(['gap_analysis_id'], ['gap_analysis_results.id'], ),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflow_executions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('ix_recommended_courses_gap_analysis_id', 'recommended_courses', ['gap_analysis_id'])
    op.create_index('ix_recommended_courses_workflow_id', 'recommended_courses', ['workflow_id'])
    op.create_index('ix_recommended_courses_skill_id', 'recommended_courses', ['skill_id'])
    op.create_index('ix_recommended_courses_status', 'recommended_courses', ['generation_status'])


def downgrade() -> None:
    """Drop Gap Analysis tables."""

    # Drop indexes first
    op.drop_index('ix_recommended_courses_status', 'recommended_courses')
    op.drop_index('ix_recommended_courses_skill_id', 'recommended_courses')
    op.drop_index('ix_recommended_courses_workflow_id', 'recommended_courses')
    op.drop_index('ix_recommended_courses_gap_analysis_id', 'recommended_courses')

    op.drop_index('ix_content_outlines_skill_id', 'content_outlines')
    op.drop_index('ix_content_outlines_workflow_id', 'content_outlines')
    op.drop_index('ix_content_outlines_gap_analysis_id', 'content_outlines')

    op.drop_index('ix_gap_analysis_cert_profile', 'gap_analysis_results')
    op.drop_index('ix_gap_analysis_workflow_id', 'gap_analysis_results')

    # Drop tables
    op.drop_table('recommended_courses')
    op.drop_table('content_outlines')
    op.drop_table('gap_analysis_results')