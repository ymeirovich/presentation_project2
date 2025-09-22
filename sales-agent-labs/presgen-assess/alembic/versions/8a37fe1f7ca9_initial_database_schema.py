"""Initial database schema

Revision ID: 8a37fe1f7ca9
Revises:
Create Date: 2025-09-23 00:13:15.015990

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '8a37fe1f7ca9'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create certification_profiles table
    op.create_table('certification_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('version', sa.String(length=100), nullable=False),
        sa.Column('provider', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('exam_code', sa.String(length=50), nullable=True),
        sa.Column('passing_score', sa.Integer(), nullable=True),
        sa.Column('exam_duration_minutes', sa.Integer(), nullable=True),
        sa.Column('question_count', sa.Integer(), nullable=True),
        sa.Column('exam_domains', sa.JSON(), nullable=False),
        sa.Column('prerequisites', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('recommended_experience', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', 'version', name='uix_certification_name_version')
    )

    # Create knowledge_base_documents table
    op.create_table('knowledge_base_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('certification_profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('content_classification', sa.String(length=50), nullable=False),
        sa.Column('file_hash', sa.String(length=64), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False),
        sa.Column('chunk_count', sa.Integer(), nullable=False),
        sa.Column('processing_status', sa.String(length=50), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['certification_profile_id'], ['certification_profiles.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('file_hash', name='uix_knowledge_document_hash')
    )

    # Create vector_ingestion_audit table
    op.create_table('vector_ingestion_audit',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chunks_ingested', sa.Integer(), nullable=False),
        sa.Column('chunks_failed', sa.Integer(), nullable=False),
        sa.Column('ingestion_duration_seconds', sa.Float(), nullable=False),
        sa.Column('vector_collection', sa.String(length=100), nullable=False),
        sa.Column('error_details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['document_id'], ['knowledge_base_documents.id'], ondelete='CASCADE')
    )

    # Create workflow_executions table
    op.create_table('workflow_executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('certification_profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workflow_type', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('parameters', sa.JSON(), nullable=True),
        sa.Column('resume_token', sa.String(length=255), nullable=True),
        sa.Column('google_sheet_url', sa.Text(), nullable=True),
        sa.Column('presentation_url', sa.Text(), nullable=True),
        sa.Column('progress', sa.Integer(), nullable=False, default=0),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['certification_profile_id'], ['certification_profiles.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('resume_token', name='uix_workflow_resume_token')
    )

    # Create presentation_generations table
    op.create_table('presentation_generations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workflow_execution_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('slide_count', sa.Integer(), nullable=False),
        sa.Column('content_outline', sa.JSON(), nullable=False),
        sa.Column('generation_status', sa.String(length=50), nullable=False),
        sa.Column('google_slides_url', sa.Text(), nullable=True),
        sa.Column('rag_sources_used', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('quality_metrics', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['workflow_execution_id'], ['workflow_executions.id'], ondelete='CASCADE')
    )

    # Create assessment_results table
    op.create_table('assessment_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('certification_profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', sa.String(length=255), nullable=False),
        sa.Column('questions', sa.JSON(), nullable=False),
        sa.Column('answers', sa.JSON(), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('passing_threshold', sa.Float(), nullable=False),
        sa.Column('time_taken_seconds', sa.Integer(), nullable=False),
        sa.Column('domain_scores', sa.JSON(), nullable=False),
        sa.Column('confidence_ratings', sa.JSON(), nullable=True),
        sa.Column('rag_sources_referenced', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['certification_profile_id'], ['certification_profiles.id'], ondelete='CASCADE')
    )

    # Create learning_content table
    op.create_table('learning_content',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assessment_result_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content_type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('content_outline', sa.JSON(), nullable=False),
        sa.Column('slide_count', sa.Integer(), nullable=False),
        sa.Column('estimated_duration_minutes', sa.Integer(), nullable=False),
        sa.Column('target_gaps', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('rag_context_sources', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('generation_status', sa.String(length=50), nullable=False),
        sa.Column('google_slides_url', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['assessment_result_id'], ['assessment_results.id'], ondelete='CASCADE')
    )

    # Create identified_gaps table
    op.create_table('identified_gaps',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assessment_result_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('domain', sa.String(length=200), nullable=False),
        sa.Column('subdomain', sa.String(length=200), nullable=True),
        sa.Column('gap_type', sa.String(length=50), nullable=False),
        sa.Column('severity_score', sa.Float(), nullable=False),
        sa.Column('confidence_level', sa.Float(), nullable=False),
        sa.Column('evidence_sources', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('remediation_priority', sa.Integer(), nullable=False),
        sa.Column('estimated_study_hours', sa.Integer(), nullable=False),
        sa.Column('rag_recommendations', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['assessment_result_id'], ['assessment_results.id'], ondelete='CASCADE')
    )

    # Create indexes for better query performance
    op.create_index('ix_certification_profiles_name', 'certification_profiles', ['name'])
    op.create_index('ix_certification_profiles_provider', 'certification_profiles', ['provider'])
    op.create_index('ix_knowledge_base_documents_content_classification', 'knowledge_base_documents', ['content_classification'])
    op.create_index('ix_workflow_executions_user_id', 'workflow_executions', ['user_id'])
    op.create_index('ix_workflow_executions_status', 'workflow_executions', ['status'])
    op.create_index('ix_assessment_results_user_id', 'assessment_results', ['user_id'])
    op.create_index('ix_identified_gaps_domain', 'identified_gaps', ['domain'])
    op.create_index('ix_identified_gaps_severity', 'identified_gaps', ['severity_score'])


def downgrade() -> None:
    # Drop tables in reverse order due to foreign key constraints
    op.drop_table('identified_gaps')
    op.drop_table('learning_content')
    op.drop_table('assessment_results')
    op.drop_table('presentation_generations')
    op.drop_table('workflow_executions')
    op.drop_table('vector_ingestion_audit')
    op.drop_table('knowledge_base_documents')
    op.drop_table('certification_profiles')