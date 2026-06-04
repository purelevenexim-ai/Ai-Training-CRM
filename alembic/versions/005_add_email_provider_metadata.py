"""Add provider and metadata columns to crm_messages for hybrid SendGrid+Plunk routing.

Revision ID: 005
Revises: 004
Create Date: 2026-05-18 15:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    """Add provider and msg_metadata columns to crm_messages table."""
    # Add provider column
    op.add_column(
        'crm_messages',
        sa.Column('provider', sa.String(50), nullable=True, comment='sendgrid | plunk | wabis')
    )
    
    # Add msg_metadata column (JSON) — note: 'metadata' is reserved in SQLAlchemy
    op.add_column(
        'crm_messages',
        sa.Column('msg_metadata', postgresql.JSON, nullable=True, comment='Quality flag and other metadata')
    )


def downgrade():
    """Remove provider and msg_metadata columns from crm_messages table."""
    op.drop_column('crm_messages', 'msg_metadata')
    op.drop_column('crm_messages', 'provider')
