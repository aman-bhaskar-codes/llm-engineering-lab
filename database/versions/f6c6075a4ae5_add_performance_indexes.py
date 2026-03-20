"""add_performance_indexes

Revision ID: f6c6075a4ae5
Revises: 619120609684
Create Date: 2026-03-20 12:03:08.356830+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f6c6075a4ae5'
down_revision = '619120609684'
branch_labels = None
depends_on = None


def upgrade():
    # Performance indexes for frequent queries
    op.create_index('ix_extractions_created_at', 'extractions', [sa.text('created_at DESC')], unique=False)
    op.create_index('ix_usage_tracking_usage_date', 'usage_tracking', ['usage_date'], unique=False)


def downgrade():
    op.drop_index('ix_usage_tracking_usage_date', table_name='usage_tracking')
    op.drop_index('ix_extractions_created_at', table_name='extractions')
