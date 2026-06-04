"""
Alembic migration: Add Lead Management & Authentication
Adds APIKey table and Lead-related fields to Customer table
"""

from alembic import op
import sqlalchemy as sa


def upgrade():
    """
    Upgrade: Add lead management and API key tables
    """
    
    # 1. Add lead fields to crm_customers table
    op.add_column('crm_customers', sa.Column('is_lead', sa.Boolean(), default=False, nullable=False))
    op.add_column('crm_customers', sa.Column('lead_source', sa.String(50), nullable=True))
    op.add_column('crm_customers', sa.Column('lead_status', sa.String(50), nullable=True))
    op.add_column('crm_customers', sa.Column('lead_score', sa.Float(), nullable=True))
    op.add_column('crm_customers', sa.Column('lead_created_at', sa.DateTime(), nullable=True))
    op.add_column('crm_customers', sa.Column('contacted_at', sa.DateTime(), nullable=True))
    op.add_column('crm_customers', sa.Column('qualified_at', sa.DateTime(), nullable=True))
    op.add_column('crm_customers', sa.Column('propensity_score', sa.Float(), default=0.5, nullable=False))
    op.add_column('crm_customers', sa.Column('propensity_updated_at', sa.DateTime(), nullable=True))
    op.add_column('crm_customers', sa.Column('company', sa.String(255), nullable=True))
    op.add_column('crm_customers', sa.Column('job_title', sa.String(255), nullable=True))
    op.add_column('crm_customers', sa.Column('industry', sa.String(255), nullable=True))
    
    # 2. Create indexes for lead fields
    op.create_index('idx_is_lead', 'crm_customers', ['is_lead'])
    op.create_index('idx_lead_status', 'crm_customers', ['lead_status'])
    op.create_index('idx_lead_source', 'crm_customers', ['lead_source'])
    op.create_index('idx_lead_score', 'crm_customers', ['lead_score'])
    
    # 3. Create APIKey table
    op.create_table(
        'crm_api_keys',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('key_hash', sa.String(255), nullable=False, unique=True),
        sa.Column('key_preview', sa.String(8), nullable=True),
        sa.Column('scope', sa.String(255), default='read:write'),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('ip_whitelist', sa.JSON(), nullable=True),
        sa.Column('created_by', sa.String(255), nullable=True),
    )
    
    op.create_index('idx_apikey_active', 'crm_api_keys', ['is_active'])
    op.create_index('idx_apikey_expires', 'crm_api_keys', ['expires_at'])


def downgrade():
    """
    Downgrade: Remove lead management and API key tables
    """
    
    # Drop APIKey table
    op.drop_table('crm_api_keys')
    
    # Drop indexes
    op.drop_index('idx_apikey_expires', 'crm_api_keys')
    op.drop_index('idx_apikey_active', 'crm_api_keys')
    op.drop_index('idx_lead_score', 'crm_customers')
    op.drop_index('idx_lead_source', 'crm_customers')
    op.drop_index('idx_lead_status', 'crm_customers')
    op.drop_index('idx_is_lead', 'crm_customers')
    
    # Remove lead fields
    op.drop_column('crm_customers', 'industry')
    op.drop_column('crm_customers', 'job_title')
    op.drop_column('crm_customers', 'company')
    op.drop_column('crm_customers', 'propensity_updated_at')
    op.drop_column('crm_customers', 'propensity_score')
    op.drop_column('crm_customers', 'qualified_at')
    op.drop_column('crm_customers', 'contacted_at')
    op.drop_column('crm_customers', 'lead_created_at')
    op.drop_column('crm_customers', 'lead_score')
    op.drop_column('crm_customers', 'lead_status')
    op.drop_column('crm_customers', 'lead_source')
    op.drop_column('crm_customers', 'is_lead')
