"""Create customer enrichment tables
Revision ID: 011
Create Date: 2026-05-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade():
    """Create enrichment tables"""
    
    # Create customer_enrichment table
    op.create_table(
        'crm_customer_enrichment',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('customer_id', sa.String(36), nullable=False),
        sa.Column('enrichment_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('enriched_fields', postgresql.JSON, nullable=True),
        sa.Column('metadata', postgresql.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['crm_customers.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_enrichment_customer', 'crm_customer_enrichment', ['customer_id'])
    op.create_index('idx_enrichment_type', 'crm_customer_enrichment', ['enrichment_type'])
    op.create_index('idx_enrichment_status', 'crm_customer_enrichment', ['status'])
    
    # Create company_data table
    op.create_table(
        'crm_company_data',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('customer_id', sa.String(36), nullable=False, unique=True),
        sa.Column('company_name', sa.String(255), nullable=False),
        sa.Column('industry', sa.String(100), nullable=True),
        sa.Column('employees', sa.Integer, nullable=True),
        sa.Column('revenue', sa.String(50), nullable=True),
        sa.Column('founded_year', sa.Integer, nullable=True),
        sa.Column('website', sa.String(255), nullable=True),
        sa.Column('location', sa.String(100), nullable=True),
        sa.Column('data_source', sa.String(50), nullable=False),
        sa.Column('enriched_at', sa.DateTime, nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['crm_customers.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_company_customer', 'crm_company_data', ['customer_id'])
    op.create_index('idx_company_industry', 'crm_company_data', ['industry'])
    
    # Create intent_signals table
    op.create_table(
        'crm_intent_signals',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('customer_id', sa.String(36), nullable=False),
        sa.Column('signal_type', sa.String(50), nullable=False),
        sa.Column('score', sa.Float, nullable=False),
        sa.Column('source', sa.String(100), nullable=False),
        sa.Column('metadata', postgresql.JSON, nullable=True),
        sa.Column('detected_at', sa.DateTime, nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['crm_customers.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_signal_customer', 'crm_intent_signals', ['customer_id'])
    op.create_index('idx_signal_type', 'crm_intent_signals', ['signal_type'])
    op.create_index('idx_signal_score', 'crm_intent_signals', ['score'])


def downgrade():
    """Drop enrichment tables"""
    op.drop_index('idx_signal_score', 'crm_intent_signals')
    op.drop_index('idx_signal_type', 'crm_intent_signals')
    op.drop_index('idx_signal_customer', 'crm_intent_signals')
    op.drop_table('crm_intent_signals')
    
    op.drop_index('idx_company_industry', 'crm_company_data')
    op.drop_index('idx_company_customer', 'crm_company_data')
    op.drop_table('crm_company_data')
    
    op.drop_index('idx_enrichment_status', 'crm_customer_enrichment')
    op.drop_index('idx_enrichment_type', 'crm_customer_enrichment')
    op.drop_index('idx_enrichment_customer', 'crm_customer_enrichment')
    op.drop_table('crm_customer_enrichment')
