"""Wave 0.2: Daily Review Workflow Alembic Migration

Add tables for daily question review queue and manual training examples
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from datetime import datetime

revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade():
    """Add Wave 0.2 tables: review queue and manual training"""
    
    # 1. ai_review_queue - Low-confidence questions that need human review
    op.create_table(
        'ai_review_queue',
        sa.Column('queue_id', sa.String(36), primary_key=True),
        sa.Column('conversation_id', sa.String(36), sa.ForeignKey('ai_conversations.id'), nullable=True, index=True),
        sa.Column('customer_id', sa.String(36), sa.ForeignKey('crm_customers.id'), nullable=True, index=True),
        sa.Column('customer_message', sa.Text, nullable=False),
        sa.Column('detected_intent', sa.String(50), nullable=True),
        sa.Column('intent_confidence', sa.Float, nullable=True),  # 0-1
        sa.Column('detected_language', sa.String(20), nullable=True),
        sa.Column('ai_response', sa.Text, nullable=True),
        sa.Column('review_status', sa.String(20), default='pending'),  # pending, approved, reclassified, escalated
        sa.Column('human_intent_correction', sa.String(50), nullable=True),  # If reclassified
        sa.Column('human_notes', sa.Text, nullable=True),
        sa.Column('should_add_to_kb', sa.Boolean, default=False),
        sa.Column('kb_category', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime, default=datetime.utcnow, index=True),
        sa.Column('reviewed_at', sa.DateTime, nullable=True),
        sa.Column('reviewed_by', sa.String(100), nullable=True),
    )
    op.create_index('idx_review_queue_status_created', 'ai_review_queue', ['review_status', 'created_at'])
    
    # 2. manual_training_examples - Your approved message/intent pairs for learning
    op.create_table(
        'manual_training_examples',
        sa.Column('example_id', sa.String(36), primary_key=True),
        sa.Column('review_queue_id', sa.String(36), sa.ForeignKey('ai_review_queue.id'), nullable=True),
        sa.Column('message_text', sa.Text, nullable=False),
        sa.Column('detected_language', sa.String(20), nullable=True),
        sa.Column('correct_intent', sa.String(50), nullable=False),
        sa.Column('intent_confidence', sa.Float, nullable=True),
        sa.Column('keywords_identified', postgresql.JSON, nullable=True),  # Keywords that led to intent
        sa.Column('approved_by', sa.String(100), nullable=False),
        sa.Column('learning_phase', sa.Integer, default=1),  # Track which learning batch this was from
        sa.Column('created_at', sa.DateTime, default=datetime.utcnow, index=True),
    )
    op.create_index('idx_training_examples_intent', 'manual_training_examples', ['correct_intent'])
    
    # 3. kb_performance - Track which KB entries are actually helpful
    op.create_table(
        'kb_performance',
        sa.Column('perf_id', sa.String(36), primary_key=True),
        sa.Column('kb_id', sa.String(36), sa.ForeignKey('knowledge_base.id'), nullable=False, unique=True, index=True),
        sa.Column('times_suggested', sa.Integer, default=0),  # How many times this KB was suggested in responses
        sa.Column('times_clicked_helpful', sa.Integer, default=0),  # How many times customer said "helpful"
        sa.Column('times_marked_unhelpful', sa.Integer, default=0),  # Customer said "not helpful"
        sa.Column('average_rating', sa.Float, default=0.0),  # 1-5 stars
        sa.Column('last_updated', sa.DateTime, default=datetime.utcnow),
        sa.Column('created_at', sa.DateTime, default=datetime.utcnow),
    )
    
    # 4. response_quality_feedback - User feedback on AI responses
    op.create_table(
        'response_quality_feedback',
        sa.Column('feedback_id', sa.String(36), primary_key=True),
        sa.Column('ai_log_id', sa.String(36), sa.ForeignKey('ai_logs.id'), nullable=True),
        sa.Column('customer_id', sa.String(36), sa.ForeignKey('crm_customers.id'), nullable=True),
        sa.Column('response_text', sa.Text, nullable=True),
        sa.Column('rating', sa.Integer, nullable=True),  # 1-5 stars
        sa.Column('feedback_text', sa.Text, nullable=True),  # Why did you rate it this way?
        sa.Column('is_helpful', sa.Boolean, nullable=True),  # Thumbs up/down
        sa.Column('suggested_improvement', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, default=datetime.utcnow, index=True),
    )
    op.create_index('idx_response_quality_rating', 'response_quality_feedback', ['rating', 'created_at'])


def downgrade():
    """Drop Wave 0.2 tables"""
    op.drop_table('response_quality_feedback')
    op.drop_table('kb_performance')
    op.drop_table('manual_training_examples')
    op.drop_table('ai_review_queue')
