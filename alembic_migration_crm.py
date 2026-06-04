"""
Alembic migration: Create CRM tables
This creates the customer, order, event, segment, attribution, and conversion_feeds tables
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    # Create customers table
    op.create_table(
        'crm_customers',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('shopify_customer_id', sa.String(50), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('first_name', sa.String(100), nullable=True),
        sa.Column('last_name', sa.String(100), nullable=True),
        sa.Column('shopify_created_at', sa.DateTime(), nullable=True),
        sa.Column('shopify_updated_at', sa.DateTime(), nullable=True),
        sa.Column('tags', postgresql.JSON(), nullable=True),
        sa.Column('total_spent', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('orders_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_order_date', sa.DateTime(), nullable=True),
        sa.Column('email_subscribed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('sms_subscribed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('metadata', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('shopify_customer_id'),
        sa.UniqueConstraint('email'),
    )
    op.create_index('idx_email_phone', 'crm_customers', ['email', 'phone'])
    op.create_index('idx_shopify_id', 'crm_customers', ['shopify_customer_id'])
    
    # Create orders table
    op.create_table(
        'crm_orders',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('shopify_order_id', sa.String(50), nullable=True),
        sa.Column('customer_id', sa.String(36), nullable=False),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('order_date', sa.DateTime(), nullable=True),
        sa.Column('total_amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='INR'),
        sa.Column('status', sa.String(50), nullable=True),
        sa.Column('items', postgresql.JSON(), nullable=False),
        sa.Column('shipping_address', postgresql.JSON(), nullable=True),
        sa.Column('utm_source', sa.String(100), nullable=True),
        sa.Column('utm_medium', sa.String(100), nullable=True),
        sa.Column('utm_campaign', sa.String(100), nullable=True),
        sa.Column('campaign_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['customer_id'], ['crm_customers.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('shopify_order_id'),
    )
    op.create_index('idx_customer_id_date', 'crm_orders', ['customer_id', 'order_date'])
    
    # Create events table
    op.create_table(
        'crm_events',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('customer_id', sa.String(36), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('event_data', postgresql.JSON(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['customer_id'], ['crm_customers.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_customer_timestamp', 'crm_events', ['customer_id', 'timestamp'])
    op.create_index('idx_source_type', 'crm_events', ['source', 'event_type'])
    op.create_index('idx_email', 'crm_events', ['email'])
    op.create_index('idx_timestamp', 'crm_events', ['timestamp'])
    
    # Create segments table
    op.create_table(
        'crm_segments',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.String(1000), nullable=True),
        sa.Column('rule_set', postgresql.JSON(), nullable=False),
        sa.Column('customer_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('auto_update', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    
    # Create attribution table
    op.create_table(
        'crm_attributions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('order_id', sa.String(36), nullable=False),
        sa.Column('customer_id', sa.String(36), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('campaign_id', sa.String(100), nullable=True),
        sa.Column('campaign_name', sa.String(255), nullable=True),
        sa.Column('ad_id', sa.String(100), nullable=True),
        sa.Column('gclid', sa.String(255), nullable=True),
        sa.Column('fbp', sa.String(255), nullable=True),
        sa.Column('attributed_amount', sa.Float(), nullable=False),
        sa.Column('attributed_percentage', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['customer_id'], ['crm_customers.id']),
        sa.ForeignKeyConstraint(['order_id'], ['crm_orders.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_order_campaign', 'crm_attributions', ['order_id', 'campaign_id'])
    
    # Create conversion_feeds table
    op.create_table(
        'crm_conversion_feeds',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('external_id', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('shopify_customer_id', sa.String(50), nullable=True),
        sa.Column('conversion_type', sa.String(100), nullable=False),
        sa.Column('conversion_value', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='INR'),
        sa.Column('campaign_id', sa.String(100), nullable=True),
        sa.Column('campaign_name', sa.String(255), nullable=True),
        sa.Column('gclid', sa.String(255), nullable=True),
        sa.Column('fbp', sa.String(255), nullable=True),
        sa.Column('is_matched', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('matched_customer_id', sa.String(36), nullable=True),
        sa.Column('metadata', postgresql.JSON(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['matched_customer_id'], ['crm_customers.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_conversion_source', 'crm_conversion_feeds', ['source'])
    op.create_index('idx_conversion_external_id', 'crm_conversion_feeds', ['external_id'])
    op.create_index('idx_conversion_email', 'crm_conversion_feeds', ['email'])
    op.create_index('idx_conversion_source_time', 'crm_conversion_feeds', ['source', 'created_at'])


def downgrade():
    # Drop tables in reverse order
    op.drop_table('crm_conversion_feeds')
    op.drop_table('crm_attributions')
    op.drop_table('crm_segments')
    op.drop_table('crm_events')
    op.drop_table('crm_orders')
    op.drop_table('crm_customers')
