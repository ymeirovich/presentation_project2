"""Add ChromaDB integration fields to certification profiles

Revision ID: 005_chromadb_integration
Revises: 8a37fe1f7ca9
Create Date: 2025-09-24 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = '005_chromadb_integration'
down_revision = '8a37fe1f7ca9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add ChromaDB integration and prompt fields to certification_profiles table."""

    # Add new columns to certification_profiles
    op.add_column('certification_profiles',
                  sa.Column('bundle_version', sa.String(50), nullable=False, server_default='v1.0'))

    op.add_column('certification_profiles',
                  sa.Column('collection_name', sa.String(255), nullable=True))

    # Custom prompts for different workflow processes
    op.add_column('certification_profiles',
                  sa.Column('assessment_prompt', sa.Text, nullable=True))

    op.add_column('certification_profiles',
                  sa.Column('presentation_prompt', sa.Text, nullable=True))

    op.add_column('certification_profiles',
                  sa.Column('gap_analysis_prompt', sa.Text, nullable=True))

    # File upload tracking
    op.add_column('certification_profiles',
                  sa.Column('uploaded_files_metadata', sa.JSON, nullable=False, server_default='[]'))

    op.add_column('certification_profiles',
                  sa.Column('resource_binding_enabled', sa.Boolean, nullable=False, server_default='true'))

    # Update existing records with default prompts
    connection = op.get_bind()

    # Default gap analysis prompt (truncated for migration)
    default_gap_analysis_prompt = """
You are an expert educational assessment analyst specializing in multidimensional skill gap analysis for professional certifications.

Analyze assessment results across five key dimensions:
1. Bloom's Taxonomy Depth Analysis (Remember/Understand/Apply/Analyze/Evaluate/Create)
2. Learning Style & Retention Indicators (Visual/Auditory/Kinesthetic/Multimodal)
3. Metacognitive Awareness Assessment (Self-assessment accuracy, uncertainty recognition, strategy adaptation)
4. Transfer Learning Evaluation (Near transfer, far transfer, analogical reasoning)
5. Certification-Specific Insights (Exam strategy readiness, industry context understanding, professional competency alignment)

Provide comprehensive analysis with specific, actionable recommendations tailored to the certification requirements.

Context: {certification_name}
Assessment Data: {assessment_results}
"""

    # Update existing records with default prompt
    connection.execute(sa.text("""
        UPDATE certification_profiles
        SET gap_analysis_prompt = :prompt
        WHERE gap_analysis_prompt IS NULL
    """), prompt=default_gap_analysis_prompt)


def downgrade() -> None:
    """Remove ChromaDB integration fields from certification_profiles table."""

    # Remove added columns in reverse order
    op.drop_column('certification_profiles', 'resource_binding_enabled')
    op.drop_column('certification_profiles', 'uploaded_files_metadata')
    op.drop_column('certification_profiles', 'gap_analysis_prompt')
    op.drop_column('certification_profiles', 'presentation_prompt')
    op.drop_column('certification_profiles', 'assessment_prompt')
    op.drop_column('certification_profiles', 'collection_name')
    op.drop_column('certification_profiles', 'bundle_version')