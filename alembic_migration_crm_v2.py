"""
Alembic migration v2: Identity, attribution fields, and audience support
- Adds unified_identity table (cross-source customer identity graph)
- Adds gclid, fbclid, session_id, identity_id to crm_customers
- Adds gclid, fbclid, payment_method, delivered_at, rto, offline_conversion_sent to crm_orders
- Adds n8n_notified to crm_events
Run: alembic upgrade head  (or execute upgrade() directly if running standalone)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    # ─── unified_identity ───────────────────────────────────────────────────
    op.create_table(
        'unified_identity',
        sa.Column('identity_id', postgresql.UUID(as_uuid=False), nullable=False,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('email_hash',   sa.String(64),  nullable=True),
        sa.Column('phone_hash',   sa.String(64),  nullable=True),
        sa.Column('session_id',   sa.String(255), nullable=True),
        sa.Column('gclid',        sa.String(255), nullable=True),
        sa.Column('fbclid',       sa.String(255), nullable=True),
        sa.Column('shopify_cid',  sa.String(255), nullable=True),

        sa.Column('first_seen',   sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('last_seen',    sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('visit_count',  sa.Integer(), server_default='1'),

        sa.Column('device',       postgresql.JSONB(), nullable=True),
        sa.Column('pincode',      sa.String(10),  nullable=True),
        sa.Column('rto_risk',     sa.Float(),     nullable=True),

        sa.Column('source_first', sa.String(100), nullable=True),
        sa.Column('source_last',  sa.String(100), nullable=True),

        sa.Column('is_buyer',       sa.Boolean(), server_default='false'),
        sa.Column('total_orders',   sa.Integer(), server_default='0'),
        sa.Column('total_revenue',  sa.Numeric(12, 2), server_default='0'),
        sa.Column('preferred_pay',  sa.String(50), nullable=True),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),

        sa.PrimaryKeyConstraint('identity_id'),
        sa.UniqueConstraint('email_hash',  name='uq_identity_email'),
        sa.UniqueConstraint('phone_hash',  name='uq_identity_phone'),
        sa.UniqueConstraint('session_id',  name='uq_identity_session'),
        sa.UniqueConstraint('shopify_cid', name='uq_identity_shopify'),
    )
    op.create_index('idx_identity_email',   'unified_identity', ['email_hash'])
    op.create_index('idx_identity_phone',   'unified_identity', ['phone_hash'])
    op.create_index('idx_identity_session', 'unified_identity', ['session_id'])
    op.create_index('idx_identity_gclid',   'unified_identity', ['gclid'])
    op.create_index('idx_identity_fbclid',  'unified_identity', ['fbclid'])

    # ─── crm_customers — new attribution columns ────────────────────────────
    op.add_column('crm_customers', sa.Column('gclid',       sa.String(255), nullable=True))
    op.add_column('crm_customers', sa.Column('fbclid',      sa.String(255), nullable=True))
    op.add_column('crm_customers', sa.Column('session_id',  sa.String(255), nullable=True))
    op.add_column('crm_customers', sa.Column('identity_id', sa.String(36),  nullable=True))
    op.create_index('idx_customer_session',  'crm_customers', ['session_id'])
    op.create_index('idx_customer_identity', 'crm_customers', ['identity_id'])

    # ─── crm_orders — COD + attribution columns ─────────────────────────────
    op.add_column('crm_orders', sa.Column('gclid',       sa.String(255), nullable=True))
    op.add_column('crm_orders', sa.Column('fbclid',      sa.String(255), nullable=True))
    op.add_column('crm_orders', sa.Column('payment_method', sa.String(50),  nullable=True))
    op.add_column('crm_orders', sa.Column('delivered_at',   sa.DateTime(),  nullable=True))
    op.add_column('crm_orders', sa.Column('rto',   sa.Boolean(), server_default='false'))
    op.add_column('crm_orders', sa.Column('offline_conversion_sent',
                                          sa.Boolean(), server_default='false'))
    op.create_index('idx_order_gclid', 'crm_orders', ['gclid'])

    # ─── crm_events — N8N dedup flag ────────────────────────────────────────
    op.add_column('crm_events', sa.Column('session_id',    sa.String(255), nullable=True))
    op.add_column('crm_events', sa.Column('n8n_notified',  sa.Boolean(), server_default='false'))
    op.create_index('idx_event_session',      'crm_events', ['session_id'])
    op.create_index('idx_event_n8n_notified', 'crm_events', ['event_type', 'n8n_notified'])


def downgrade():
    op.drop_index('idx_event_n8n_notified', 'crm_events')
    op.drop_index('idx_event_session',      'crm_events')
    op.drop_column('crm_events', 'n8n_notified')
    op.drop_column('crm_events', 'session_id')

    op.drop_index('idx_order_gclid', 'crm_orders')
    op.drop_column('crm_orders', 'offline_conversion_sent')
    op.drop_column('crm_orders', 'rto')
    op.drop_column('crm_orders', 'delivered_at')
    op.drop_column('crm_orders', 'payment_method')
    op.drop_column('crm_orders', 'fbclid')
    op.drop_column('crm_orders', 'gclid')

    op.drop_index('idx_customer_identity', 'crm_customers')
    op.drop_index('idx_customer_session',  'crm_customers')
    op.drop_column('crm_customers', 'identity_id')
    op.drop_column('crm_customers', 'session_id')
    op.drop_column('crm_customers', 'fbclid')
    op.drop_column('crm_customers', 'gclid')

    op.drop_index('idx_identity_fbclid',  'unified_identity')
    op.drop_index('idx_identity_gclid',   'unified_identity')
    op.drop_index('idx_identity_session', 'unified_identity')
    op.drop_index('idx_identity_phone',   'unified_identity')
    op.drop_index('idx_identity_email',   'unified_identity')
    op.drop_table('unified_identity')
