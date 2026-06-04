"""Add AI CRM V1 core tables: customer scoring, events, conversations, products, KB, logs.

Revision ID: 006
Revises: 005
Create Date: 2026-06-01 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from datetime import datetime

revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
    """Create 6 core AI CRM tables."""
    
    # 1. customer_ai_profile - Customer scoring and status
    op.create_table(
        'customer_ai_profile',
        sa.Column('profile_id', sa.String(36), primary_key=True),
        sa.Column('customer_id', sa.String(36), sa.ForeignKey('crm_customers.id'), nullable=False, index=True),
        sa.Column('overall_score', sa.Integer, default=0),  # 0-100
        sa.Column('engagement_score', sa.Integer, default=0),  # 0-100
        sa.Column('purchase_intent_score', sa.Integer, default=0),  # 0-100
        sa.Column('customer_value_score', sa.Integer, default=0),  # 0-100
        sa.Column('lead_status', sa.String(20), default='Cold'),  # Cold, Warm, Hot, Ready
        sa.Column('last_activity', sa.DateTime, nullable=True),
        sa.Column('next_action', sa.String(100), nullable=True),  # "Call Now", "Send Offer", "Follow Up"
        sa.Column('last_score_update', sa.DateTime, default=datetime.utcnow),
        sa.Column('created_at', sa.DateTime, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.UniqueConstraint('customer_id', name='uq_customer_ai_profile_customer_id'),
    )
    op.create_index('idx_customer_ai_profile_score', 'customer_ai_profile', ['overall_score'])
    op.create_index('idx_customer_ai_profile_status', 'customer_ai_profile', ['lead_status'])
    
    # 2. customer_events - Event log for AI interactions
    op.create_table(
        'customer_events',
        sa.Column('event_id', sa.String(36), primary_key=True),
        sa.Column('customer_id', sa.String(36), sa.ForeignKey('crm_customers.id'), nullable=False, index=True),
        sa.Column('conversation_id', sa.String(36), nullable=True, index=True),
        sa.Column('event_type', sa.String(50), nullable=False),  # PRICE_INQUIRY, COD_INQUIRY, ORDER_CREATED, etc.
        sa.Column('context_json', postgresql.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime, default=datetime.utcnow, index=True),
    )
    op.create_index('idx_customer_events_customer_created', 'customer_events', ['customer_id', 'created_at'])
    
    # 3. ai_conversations - Chat sessions
    op.create_table(
        'ai_conversations',
        sa.Column('conversation_id', sa.String(36), primary_key=True),
        sa.Column('customer_id', sa.String(36), sa.ForeignKey('crm_customers.id'), nullable=False, index=True),
        sa.Column('message_count', sa.Integer, default=1),
        sa.Column('intents_in_path', postgresql.JSON, nullable=True),  # Array of detected intents
        sa.Column('outcome', sa.String(50), nullable=True),  # converted, lost, pending, escalated
        sa.Column('created_at', sa.DateTime, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
    )
    op.create_index('idx_ai_conversations_customer', 'ai_conversations', ['customer_id'])
    
    # 4. product_catalog - Products
    op.create_table(
        'product_catalog',
        sa.Column('product_id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('price_inr', sa.Float, nullable=False),  # Current price in INR
        sa.Column('stock', sa.Integer, default=0),  # Current stock level
        sa.Column('category', sa.String(100), nullable=True),  # Pepper, Cardamom, Clove, etc.
        sa.Column('status', sa.String(20), default='active'),  # active, inactive, discontinued
        sa.Column('created_at', sa.DateTime, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
    )
    op.create_index('idx_product_catalog_category', 'product_catalog', ['category'])
    
    # 5. knowledge_base - FAQ and help articles
    op.create_table(
        'knowledge_base',
        sa.Column('kb_id', sa.String(36), primary_key=True),
        sa.Column('question', sa.String(500), nullable=False),
        sa.Column('answer', sa.Text, nullable=False),
        sa.Column('category', sa.String(50), nullable=True),  # FAQ, Shipping, Payment, Policy, etc.
        sa.Column('status', sa.String(20), default='active'),  # active, inactive, archived
        sa.Column('created_at', sa.DateTime, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
    )
    op.create_index('idx_knowledge_base_category', 'knowledge_base', ['category'])
    op.create_index('idx_knowledge_base_status', 'knowledge_base', ['status'])
    
    # 6. ai_logs - Audit trail
    op.create_table(
        'ai_logs',
        sa.Column('log_id', sa.String(36), primary_key=True),
        sa.Column('customer_id', sa.String(36), sa.ForeignKey('crm_customers.id'), nullable=True, index=True),
        sa.Column('conversation_id', sa.String(36), nullable=True),
        sa.Column('intent_detected', sa.String(50), nullable=True),
        sa.Column('language_detected', sa.String(20), nullable=True),  # english, malayalam, manglish, mixed
        sa.Column('response_text', sa.Text, nullable=True),
        sa.Column('tokens_used', sa.Integer, nullable=True),
        sa.Column('latency_ms', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime, default=datetime.utcnow, index=True),
    )
    op.create_index('idx_ai_logs_customer', 'ai_logs', ['customer_id', 'created_at'])


def downgrade():
    """Drop all AI CRM tables."""
    op.drop_table('ai_logs')
    op.drop_table('knowledge_base')
    op.drop_table('product_catalog')
    op.drop_table('ai_conversations')
    op.drop_table('customer_events')
    op.drop_table('customer_ai_profile')
