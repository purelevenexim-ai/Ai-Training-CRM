"""
Alembic migration - Add Meta Ads tracking tables
Adds:
- crm_meta_audiences (custom audiences for targeting)
- crm_meta_conversions (offline conversions for attribution)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '008_add_meta_ads'
down_revision = '007_add_google_forms'
branch_labels = None
depends_on = None


def upgrade():
    """Create Meta Ads tables"""
    
    # MetaAudience table
    op.create_table(
        'crm_meta_audiences',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('meta_audience_id', sa.String(100), nullable=False, unique=True),
        sa.Column('audience_name', sa.String(255), nullable=False),
        sa.Column('audience_description', sa.String(500), nullable=True),
        sa.Column('audience_type', sa.String(50), nullable=True),
        sa.Column('customer_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('metadata', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Indexes for audiences
    op.create_index('idx_audience_id', 'crm_meta_audiences', ['meta_audience_id'])
    op.create_index('idx_audience_active', 'crm_meta_audiences', ['is_active'])
    op.create_index('idx_audience_type', 'crm_meta_audiences', ['audience_type'])
    
    # MetaConversion table
    op.create_table(
        'crm_meta_conversions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('customer_id', sa.String(36), nullable=True),
        sa.Column('event_name', sa.String(100), nullable=False),
        sa.Column('value', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(3), nullable=True, server_default='INR'),
        sa.Column('status', sa.String(50), nullable=True),
        sa.Column('synced_to_meta', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('meta_response', postgresql.JSON(), nullable=True),
        sa.Column('meta_event_id', sa.String(100), nullable=True),
        sa.Column('metadata', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['customer_id'], ['crm_customers.id'], )
    )
    
    # Indexes for conversions
    op.create_index('idx_conversion_customer', 'crm_meta_conversions', ['customer_id'])
    op.create_index('idx_conversion_event', 'crm_meta_conversions', ['event_name'])
    op.create_index('idx_conversion_synced', 'crm_meta_conversions', ['synced_to_meta'])
    op.create_index('idx_conversion_created', 'crm_meta_conversions', ['created_at'])


def downgrade():
    """Drop Meta Ads tables"""
    
    # Drop conversion table first (has foreign key)
    op.drop_index('idx_conversion_created', table_name='crm_meta_conversions')
    op.drop_index('idx_conversion_synced', table_name='crm_meta_conversions')
    op.drop_index('idx_conversion_event', table_name='crm_meta_conversions')
    op.drop_index('idx_conversion_customer', table_name='crm_meta_conversions')
    op.drop_table('crm_meta_conversions')
    
    # Drop audience table
    op.drop_index('idx_audience_type', table_name='crm_meta_audiences')
    op.drop_index('idx_audience_active', table_name='crm_meta_audiences')
    op.drop_index('idx_audience_id', table_name='crm_meta_audiences')
    op.drop_table('crm_meta_audiences')
