"""Create SMS and Email tables
Revision ID: 010
Create Date: 2026-05-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade():
    """Create SMS and email tables"""
    
    # Create sms_campaigns table
    op.create_table(
        'crm_sms_campaigns',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('campaign_name', sa.String(255), nullable=False),
        sa.Column('message_text', sa.Text, nullable=False),
        sa.Column('audience_filter', postgresql.JSON, nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('total_recipients', sa.Integer, server_default='0'),
        sa.Column('sent_count', sa.Integer, server_default='0'),
        sa.Column('failed_count', sa.Integer, server_default='0'),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_sms_campaign_status', 'crm_sms_campaigns', ['status'])
    op.create_index('idx_sms_campaign_created', 'crm_sms_campaigns', ['created_at'])
    
    # Create sms_messages table
    op.create_table(
        'crm_sms_messages',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('campaign_id', sa.String(36), nullable=True),
        sa.Column('customer_id', sa.String(36), nullable=False),
        sa.Column('phone_number', sa.String(20), nullable=False),
        sa.Column('message_text', sa.Text, nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('twilio_sid', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.ForeignKeyConstraint(['campaign_id'], ['crm_sms_campaigns.id']),
        sa.ForeignKeyConstraint(['customer_id'], ['crm_customers.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_sms_customer', 'crm_sms_messages', ['customer_id'])
    op.create_index('idx_sms_campaign', 'crm_sms_messages', ['campaign_id'])
    op.create_index('idx_sms_status', 'crm_sms_messages', ['status'])
    
    # Create email_templates table
    op.create_table(
        'crm_email_templates',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('template_name', sa.String(255), nullable=False),
        sa.Column('subject', sa.String(255), nullable=False),
        sa.Column('html_content', sa.Text, nullable=False),
        sa.Column('variables', postgresql.JSON, nullable=True),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_template_active', 'crm_email_templates', ['is_active'])
    
    # Create email_campaigns table
    op.create_table(
        'crm_email_campaigns',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('campaign_name', sa.String(255), nullable=False),
        sa.Column('template_id', sa.String(36), nullable=False),
        sa.Column('audience_filter', postgresql.JSON, nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('total_recipients', sa.Integer, server_default='0'),
        sa.Column('sent_count', sa.Integer, server_default='0'),
        sa.Column('failed_count', sa.Integer, server_default='0'),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.ForeignKeyConstraint(['template_id'], ['crm_email_templates.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_email_campaign_status', 'crm_email_campaigns', ['status'])
    op.create_index('idx_email_campaign_created', 'crm_email_campaigns', ['created_at'])
    
    # Create email_messages table
    op.create_table(
        'crm_email_messages',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('campaign_id', sa.String(36), nullable=True),
        sa.Column('customer_id', sa.String(36), nullable=False),
        sa.Column('email_address', sa.String(255), nullable=False),
        sa.Column('subject', sa.String(255), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('plunk_message_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.ForeignKeyConstraint(['campaign_id'], ['crm_email_campaigns.id']),
        sa.ForeignKeyConstraint(['customer_id'], ['crm_customers.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_email_customer', 'crm_email_messages', ['customer_id'])
    op.create_index('idx_email_campaign', 'crm_email_messages', ['campaign_id'])
    op.create_index('idx_email_status', 'crm_email_messages', ['status'])


def downgrade():
    """Drop SMS and email tables"""
    op.drop_index('idx_email_status', 'crm_email_messages')
    op.drop_index('idx_email_campaign', 'crm_email_messages')
    op.drop_index('idx_email_customer', 'crm_email_messages')
    op.drop_table('crm_email_messages')
    
    op.drop_index('idx_email_campaign_created', 'crm_email_campaigns')
    op.drop_index('idx_email_campaign_status', 'crm_email_campaigns')
    op.drop_table('crm_email_campaigns')
    
    op.drop_index('idx_template_active', 'crm_email_templates')
    op.drop_table('crm_email_templates')
    
    op.drop_index('idx_sms_status', 'crm_sms_messages')
    op.drop_index('idx_sms_campaign', 'crm_sms_messages')
    op.drop_index('idx_sms_customer', 'crm_sms_messages')
    op.drop_table('crm_sms_messages')
    
    op.drop_index('idx_sms_campaign_created', 'crm_sms_campaigns')
    op.drop_index('idx_sms_campaign_status', 'crm_sms_campaigns')
    op.drop_table('crm_sms_campaigns')
