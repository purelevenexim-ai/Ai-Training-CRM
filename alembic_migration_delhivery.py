"""
Alembic migration - Add Delhivery shipping tables
Adds:
- crm_delhivery_orders (track orders through fulfillment)
- crm_delhivery_tracking (track shipment events)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006_add_delhivery_shipping'
down_revision = '005_add_cart_recovery'
branch_labels = None
depends_on = None


def upgrade():
    """Create Delhivery tables"""
    
    # DelhiveryOrder table
    op.create_table(
        'crm_delhivery_orders',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('customer_id', sa.String(36), nullable=True),
        sa.Column('order_number', sa.String(100), nullable=False, unique=True),
        sa.Column('order_id', sa.String(100), nullable=True),
        sa.Column('recipient_name', sa.String(255), nullable=False),
        sa.Column('recipient_email', sa.String(255), nullable=True),
        sa.Column('recipient_phone', sa.String(20), nullable=False),
        sa.Column('address_line1', sa.String(255), nullable=False),
        sa.Column('address_line2', sa.String(255), nullable=True),
        sa.Column('city', sa.String(100), nullable=False),
        sa.Column('state', sa.String(100), nullable=False),
        sa.Column('postal_code', sa.String(20), nullable=False),
        sa.Column('country', sa.String(2), nullable=True, server_default='IN'),
        sa.Column('items_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('items', postgresql.JSON(), nullable=True),
        sa.Column('subtotal', sa.Float(), nullable=True),
        sa.Column('shipping_charge', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('tax', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('total_amount', sa.Float(), nullable=False),
        sa.Column('delhivery_waybill', sa.String(50), nullable=True),
        sa.Column('delhivery_status', sa.String(50), nullable=True, server_default='pending'),
        sa.Column('delhivery_sku', sa.String(50), nullable=True),
        sa.Column('delhivery_response', postgresql.JSON(), nullable=True),
        sa.Column('tracking_url', sa.String(500), nullable=True),
        sa.Column('last_track_at', sa.DateTime(), nullable=True),
        sa.Column('estimated_delivery', sa.Date(), nullable=True),
        sa.Column('actual_delivery', sa.DateTime(), nullable=True),
        sa.Column('picked_at', sa.DateTime(), nullable=True),
        sa.Column('in_transit_at', sa.DateTime(), nullable=True),
        sa.Column('out_for_delivery_at', sa.DateTime(), nullable=True),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.Column('failed_at', sa.DateTime(), nullable=True),
        sa.Column('failed_reason', sa.String(500), nullable=True),
        sa.Column('webhook_notified_at', sa.DateTime(), nullable=True),
        sa.Column('customer_notified_at', sa.DateTime(), nullable=True),
        sa.Column('notification_status', sa.String(50), nullable=True),
        sa.Column('is_cancellable', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('cancellation_reason', sa.String(500), nullable=True),
        sa.Column('metadata', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['customer_id'], ['crm_customers.id'], )
    )
    
    # Indexes for Delhivery orders
    op.create_index('idx_delhivery_customer', 'crm_delhivery_orders', ['customer_id'])
    op.create_index('idx_delhivery_status', 'crm_delhivery_orders', ['delhivery_status'])
    op.create_index('idx_delhivery_waybill', 'crm_delhivery_orders', ['delhivery_waybill'])
    op.create_index('idx_delhivery_created', 'crm_delhivery_orders', ['created_at'])
    
    # DelhiveryTracking table
    op.create_table(
        'crm_delhivery_tracking',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('delhivery_order_id', sa.String(36), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('event_timestamp', sa.DateTime(), nullable=False),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('status_message', sa.String(500), nullable=True),
        sa.Column('status_code', sa.String(50), nullable=True),
        sa.Column('handler_name', sa.String(255), nullable=True),
        sa.Column('handler_contact', sa.String(20), nullable=True),
        sa.Column('metadata', postgresql.JSON(), nullable=True),
        sa.Column('received_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['delhivery_order_id'], ['crm_delhivery_orders.id'], )
    )
    
    # Indexes for tracking
    op.create_index('idx_tracking_order', 'crm_delhivery_tracking', ['delhivery_order_id'])
    op.create_index('idx_tracking_event_type', 'crm_delhivery_tracking', ['event_type'])
    op.create_index('idx_tracking_timestamp', 'crm_delhivery_tracking', ['event_timestamp'])


def downgrade():
    """Drop Delhivery tables"""
    
    # Drop tracking table first (has foreign key)
    op.drop_index('idx_tracking_timestamp', table_name='crm_delhivery_tracking')
    op.drop_index('idx_tracking_event_type', table_name='crm_delhivery_tracking')
    op.drop_index('idx_tracking_order', table_name='crm_delhivery_tracking')
    op.drop_table('crm_delhivery_tracking')
    
    # Drop orders table
    op.drop_index('idx_delhivery_created', table_name='crm_delhivery_orders')
    op.drop_index('idx_delhivery_waybill', table_name='crm_delhivery_orders')
    op.drop_index('idx_delhivery_status', table_name='crm_delhivery_orders')
    op.drop_index('idx_delhivery_customer', table_name='crm_delhivery_orders')
    op.drop_table('crm_delhivery_orders')
