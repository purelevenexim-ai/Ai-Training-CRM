"""
Alembic migration: Add Wave 0.2 Wabis AI integration tables

Creates tables for:
- Incoming messages from Wabis
- Outgoing AI replies
- Escalation queue
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    """Create Wave 0.2 Wabis AI integration tables"""
    
    # Incoming messages from Wabis
    op.create_table(
        'ai_incoming_messages',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('conversation_id', sa.String(255), index=True),
        sa.Column('customer_phone', sa.String(20), index=True),
        sa.Column('message_type', sa.String(50), default='text'),
        sa.Column('body', sa.Text()),
        sa.Column('created_at', sa.String(30), index=True),
    )
    
    # Outgoing AI replies
    op.create_table(
        'ai_outgoing_replies',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('conversation_id', sa.String(255), index=True),
        sa.Column('customer_phone', sa.String(20), index=True),
        sa.Column('reply_text', sa.Text()),
        sa.Column('intent', sa.String(100)),  # complaint, bulk_inquiry, purchase_intent, etc
        sa.Column('escalated', sa.Boolean, default=False),
        sa.Column('send_status', sa.String(50), default='pending'),  # pending, sent, failed
        sa.Column('created_at', sa.String(30), index=True),
    )
    
    # Escalation queue for complaints, bulk inquiries, etc
    op.create_table(
        'escalation_queue',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('customer_phone', sa.String(20), index=True),
        sa.Column('reason', sa.Text()),
        sa.Column('resolved', sa.Boolean, default=False),
        sa.Column('created_at', sa.String(30), index=True),
        sa.Column('resolved_at', sa.String(30)),
    )


def downgrade():
    """Drop Wave 0.2 Wabis AI integration tables"""
    op.drop_table('escalation_queue')
    op.drop_table('ai_outgoing_replies')
    op.drop_table('ai_incoming_messages')
