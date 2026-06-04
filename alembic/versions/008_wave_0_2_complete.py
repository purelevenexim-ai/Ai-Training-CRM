"""Wave 0.2 Complete - Advanced Scoring, KB Organization, Feature Toggles

Alembic migration to add:
- Columns to customer_ai_profile (response_quality_score, churn_risk_score)
- feature_toggles table
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade():
    """Add Wave 0.2 complete features"""
    
    # 1. Add columns to customer_ai_profile table
    op.add_column(
        'customer_ai_profile',
        sa.Column('response_quality_score', sa.Float, default=3.5),
    )
    op.add_column(
        'customer_ai_profile',
        sa.Column('churn_risk_score', sa.Integer, default=0),
    )
    
    # 2. Create feature_toggles table
    op.create_table(
        'feature_toggles',
        sa.Column('toggle_id', sa.String(36), primary_key=True),
        sa.Column('feature_key', sa.String(50), nullable=False, unique=True, index=True),
        sa.Column('feature_name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('enabled', sa.Boolean, default=True, index=True),
        sa.Column('category', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime, default=datetime.utcnow),
    )
    
    # 3. Insert default feature toggles
    op.execute("""
        INSERT INTO feature_toggles (toggle_id, feature_key, feature_name, description, enabled, category, created_at)
        VALUES 
        ('toggle-001', 'wave_0_2_review_queue', 'Wave 0.2 - Daily Review Queue', 'Flag low-confidence messages for human review', true, 'Wave 0.2', NOW()),
        ('toggle-002', 'wave_0_2_learning_engine', 'Wave 0.2 - Learning Engine', 'Improve rule engine accuracy from corrections', true, 'Wave 0.2', NOW()),
        ('toggle-003', 'wave_0_2_advanced_scoring', 'Wave 0.2 - Advanced Scoring', 'Track response quality and churn risk scores', true, 'Wave 0.2', NOW()),
        ('toggle-004', 'wave_0_2_kb_organization', 'Wave 0.2 - KB Auto-Organization', 'Track KB performance and suggest archiving', true, 'Wave 0.2', NOW()),
        ('toggle-005', 'wave_1_product_affinity', 'Wave 1 - Product Affinity', 'Recommend complementary products', false, 'Wave 1', NOW())
    """)


def downgrade():
    """Downgrade Wave 0.2 complete features"""
    op.drop_table('feature_toggles')
    op.drop_column('customer_ai_profile', 'churn_risk_score')
    op.drop_column('customer_ai_profile', 'response_quality_score')
