"""
Alembic migration - Add cart recovery tables
Adds:
- crm_cart_abandonments (track abandoned carts)
- crm_cart_recovery_templates (recovery email templates)
- crm_cart_recovery_campaigns (recovery campaign tracking)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005_add_cart_recovery'
down_revision = '004_add_offline_conversions'
branch_labels = None
depends_on = None


def upgrade():
    """Create cart recovery tables"""
    
    # CartAbandonment table
    op.create_table(
        'crm_cart_abandonments',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('customer_id', sa.String(36), nullable=True),
        sa.Column('cart_token', sa.String(100), nullable=True),
        sa.Column('cart_value', sa.Float(), nullable=True),
        sa.Column('items_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('currency', sa.String(3), nullable=True, server_default='INR'),
        sa.Column('cart_items', postgresql.JSON(), nullable=True),
        sa.Column('abandoned_at', sa.DateTime(), nullable=True),
        sa.Column('abandoned_url', sa.String(500), nullable=True),
        sa.Column('reason', sa.String(100), nullable=True),
        sa.Column('recovery_status', sa.String(50), nullable=True, server_default='pending'),
        sa.Column('recovery_attempts', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('first_recovery_campaign_id', sa.String(36), nullable=True),
        sa.Column('last_recovery_campaign_id', sa.String(36), nullable=True),
        sa.Column('last_recovery_at', sa.DateTime(), nullable=True),
        sa.Column('recovered_value', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('recovered_at', sa.DateTime(), nullable=True),
        sa.Column('time_to_recovery_hours', sa.Integer(), nullable=True),
        sa.Column('recovery_emails_sent', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('recovery_emails_clicked', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('recovery_email_click_rate', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('source', sa.String(50), nullable=True, server_default='shopify'),
        sa.Column('metadata', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['customer_id'], ['crm_customers.id'], ),
        sa.UniqueConstraint('cart_token')
    )
    
    # Indexes for cart abandonments
    op.create_index('idx_cart_abandoned_customer', 'crm_cart_abandonments', ['customer_id'])
    op.create_index('idx_cart_abandoned_status', 'crm_cart_abandonments', ['recovery_status'])
    op.create_index('idx_cart_abandoned_time', 'crm_cart_abandonments', ['abandoned_at'])
    
    # CartRecoveryTemplate table
    op.create_table(
        'crm_cart_recovery_templates',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('subject', sa.String(200), nullable=False),
        sa.Column('template_html', sa.String(10000), nullable=False),
        sa.Column('template_text', sa.String(10000), nullable=True),
        sa.Column('trigger_hours_after_abandon', sa.Integer(), nullable=True),
        sa.Column('cta_text', sa.String(100), nullable=True, server_default='Complete Your Purchase'),
        sa.Column('cta_url_param', sa.String(255), nullable=True),
        sa.Column('include_product_image', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('include_discount_code', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('discount_code', sa.String(50), nullable=True),
        sa.Column('discount_percentage', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('send_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('click_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('recovery_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('avg_recovery_value', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Indexes for templates
    op.create_index('idx_template_active', 'crm_cart_recovery_templates', ['is_active'])
    op.create_index('idx_template_trigger', 'crm_cart_recovery_templates', ['trigger_hours_after_abandon'])
    
    # CartRecoveryCampaign table
    op.create_table(
        'crm_cart_recovery_campaigns',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('cart_abandonment_id', sa.String(36), nullable=False),
        sa.Column('template_id', sa.String(36), nullable=False),
        sa.Column('customer_email', sa.String(255), nullable=False),
        sa.Column('email_sent_at', sa.DateTime(), nullable=True),
        sa.Column('email_delivered_at', sa.DateTime(), nullable=True),
        sa.Column('email_opened_at', sa.DateTime(), nullable=True),
        sa.Column('email_clicked_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(50), nullable=True, server_default='pending'),
        sa.Column('recovered', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('recovered_value', sa.Float(), nullable=True),
        sa.Column('recovered_at', sa.DateTime(), nullable=True),
        sa.Column('n8n_execution_id', sa.String(100), nullable=True),
        sa.Column('n8n_status', sa.String(50), nullable=True),
        sa.Column('utm_source', sa.String(100), nullable=True, server_default='cart_recovery'),
        sa.Column('utm_campaign', sa.String(100), nullable=True),
        sa.Column('metadata', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['cart_abandonment_id'], ['crm_cart_abandonments.id'], ),
        sa.ForeignKeyConstraint(['template_id'], ['crm_cart_recovery_templates.id'], )
    )
    
    # Indexes for campaigns
    op.create_index('idx_recovery_campaign_cart', 'crm_cart_recovery_campaigns', ['cart_abandonment_id'])
    op.create_index('idx_recovery_campaign_status', 'crm_cart_recovery_campaigns', ['status'])
    op.create_index('idx_recovery_campaign_email_sent', 'crm_cart_recovery_campaigns', ['email_sent_at'])
    op.create_index('idx_recovery_campaign_recovered', 'crm_cart_recovery_campaigns', ['recovered'])


def downgrade():
    """Drop cart recovery tables"""
    
    # Drop campaign table first (has foreign keys)
    op.drop_index('idx_recovery_campaign_recovered', table_name='crm_cart_recovery_campaigns')
    op.drop_index('idx_recovery_campaign_email_sent', table_name='crm_cart_recovery_campaigns')
    op.drop_index('idx_recovery_campaign_status', table_name='crm_cart_recovery_campaigns')
    op.drop_index('idx_recovery_campaign_cart', table_name='crm_cart_recovery_campaigns')
    op.drop_table('crm_cart_recovery_campaigns')
    
    # Drop template table
    op.drop_index('idx_template_trigger', table_name='crm_cart_recovery_templates')
    op.drop_index('idx_template_active', table_name='crm_cart_recovery_templates')
    op.drop_table('crm_cart_recovery_templates')
    
    # Drop abandonment table
    op.drop_index('idx_cart_abandoned_time', table_name='crm_cart_abandonments')
    op.drop_index('idx_cart_abandoned_status', table_name='crm_cart_abandonments')
    op.drop_index('idx_cart_abandoned_customer', table_name='crm_cart_abandonments')
    op.drop_table('crm_cart_abandonments')
