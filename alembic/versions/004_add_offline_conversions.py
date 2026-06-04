"""Add offline conversions table

Revision ID: 004_add_offline_conversions
Revises: 003_add_lead_management
Create Date: 2026-05-22

"""
from alembic import op
import sqlalchemy as sa


revision = '004_add_offline_conversions'
down_revision = '003_add_lead_management'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create offline_conversions table
    op.create_table(
        'crm_offline_conversions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('customer_id', sa.String(36), nullable=True),
        sa.Column('conversion_type', sa.String(50), server_default='Purchase', nullable=False),
        sa.Column('conversion_value', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(3), server_default='INR', nullable=False),
        
        # Conversion source
        sa.Column('source', sa.String(50), nullable=True),
        sa.Column('conversion_timestamp', sa.DateTime(), nullable=True),
        
        # Conversion data
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('first_name', sa.String(100), nullable=True),
        sa.Column('last_name', sa.String(100), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state', sa.String(100), nullable=True),
        sa.Column('postal_code', sa.String(20), nullable=True),
        sa.Column('country', sa.String(2), nullable=True),
        
        # Matching results
        sa.Column('status', sa.String(20), server_default='pending', nullable=False),
        sa.Column('match_algorithm', sa.String(50), nullable=True),
        sa.Column('match_confidence', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('match_fields', sa.JSON(), nullable=True),
        
        # CAPI submission
        sa.Column('capi_status', sa.String(50), nullable=True),
        sa.Column('capi_event_id', sa.String(100), nullable=True),
        sa.Column('capi_response', sa.JSON(), nullable=True),
        
        # Retry logic
        sa.Column('retry_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('max_retries', sa.Integer(), server_default='5', nullable=False),
        sa.Column('next_retry_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.String(500), nullable=True),
        
        # Metadata
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('matched_at', sa.DateTime(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('capi_event_id')
    )
    
    # Create indexes
    op.create_index('idx_offline_conversion_customer', 'crm_offline_conversions', ['customer_id'])
    op.create_index('idx_offline_conversion_status', 'crm_offline_conversions', ['status'])
    op.create_index('idx_offline_conversion_capi_status', 'crm_offline_conversions', ['capi_status'])
    op.create_index('idx_offline_conversion_source', 'crm_offline_conversions', ['source'])
    op.create_index('idx_offline_conversion_retry', 'crm_offline_conversions', ['next_retry_at'])
    op.create_index('idx_offline_conversion_created', 'crm_offline_conversions', ['created_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_offline_conversion_created', table_name='crm_offline_conversions')
    op.drop_index('idx_offline_conversion_retry', table_name='crm_offline_conversions')
    op.drop_index('idx_offline_conversion_source', table_name='crm_offline_conversions')
    op.drop_index('idx_offline_conversion_capi_status', table_name='crm_offline_conversions')
    op.drop_index('idx_offline_conversion_status', table_name='crm_offline_conversions')
    op.drop_index('idx_offline_conversion_customer', table_name='crm_offline_conversions')
    
    # Drop table
    op.drop_table('crm_offline_conversions')
