"""Add embedding_dimension column to knowledge_base_documents

Revision ID: add_embedding_dimension
Revises:
Create Date: 2025-11-15

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '009_embedding_dimension'
down_revision = '008_drive_url'
branch_labels = None
depends_on = None


def upgrade():
    """Add embedding_dimension column to track vector dimensions"""
    # Add embedding_dimension column
    op.add_column(
        'knowledge_base_documents',
        sa.Column('embedding_dimension', sa.Integer(), nullable=True)
    )

    # Set default value for existing records (1536 for OpenAI text-embedding-3-small)
    # This assumes existing documents were processed with OpenAI embeddings
    op.execute("""
        UPDATE knowledge_base_documents
        SET embedding_dimension = 1536
        WHERE embedding_dimension IS NULL
          AND embedding_model = 'text-embedding-3-small'
    """)

    # Set 128 for any records that might have used fallback embeddings
    op.execute("""
        UPDATE knowledge_base_documents
        SET embedding_dimension = 128
        WHERE embedding_dimension IS NULL
          AND (embedding_model IS NULL OR embedding_model = 'simple_hash')
    """)


def downgrade():
    """Remove embedding_dimension column"""
    op.drop_column('knowledge_base_documents', 'embedding_dimension')
