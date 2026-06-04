"""
Alembic migration - Add Google Forms submission tracking
Adds:
- crm_google_form_submissions (track form submissions)
- crm_google_form_templates (save form field mappings)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '007_add_google_forms'
down_revision = '006_add_delhivery_shipping'
branch_labels = None
depends_on = None


def upgrade():
    """Create Google Forms tables"""
    
    # GoogleFormSubmission table
    op.create_table(
        'crm_google_form_submissions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('form_id', sa.String(100), nullable=False),
        sa.Column('customer_id', sa.String(36), nullable=True),
        sa.Column('submission_data', postgresql.JSON(), nullable=False),
        sa.Column('extracted_fields', postgresql.JSON(), nullable=True),
        sa.Column('submission_hash', sa.String(64), nullable=True, unique=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='received'),
        sa.Column('match_type', sa.String(50), nullable=True),
        sa.Column('error_message', sa.String(500), nullable=True),
        sa.Column('metadata', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['customer_id'], ['crm_customers.id'], )
    )
    
    # Indexes for submissions
    op.create_index('idx_form_id', 'crm_google_form_submissions', ['form_id'])
    op.create_index('idx_form_customer', 'crm_google_form_submissions', ['form_id', 'customer_id'])
    op.create_index('idx_form_status', 'crm_google_form_submissions', ['form_id', 'status'])
    op.create_index('idx_form_created', 'crm_google_form_submissions', ['form_id', 'created_at'])
    op.create_index('idx_customer_id_forms', 'crm_google_form_submissions', ['customer_id'])
    
    # GoogleFormTemplate table
    op.create_table(
        'crm_google_form_templates',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('form_id', sa.String(100), nullable=False, unique=True),
        sa.Column('form_name', sa.String(255), nullable=False),
        sa.Column('form_url', sa.String(500), nullable=True),
        sa.Column('field_mapping', postgresql.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Indexes for templates
    op.create_index('idx_template_form_id', 'crm_google_form_templates', ['form_id'])
    op.create_index('idx_template_active', 'crm_google_form_templates', ['is_active'])


def downgrade():
    """Drop Google Forms tables"""
    
    # Drop template table first
    op.drop_index('idx_template_active', table_name='crm_google_form_templates')
    op.drop_index('idx_template_form_id', table_name='crm_google_form_templates')
    op.drop_table('crm_google_form_templates')
    
    # Drop submissions table
    op.drop_index('idx_form_created', table_name='crm_google_form_submissions')
    op.drop_index('idx_form_status', table_name='crm_google_form_submissions')
    op.drop_index('idx_form_customer', table_name='crm_google_form_submissions')
    op.drop_index('idx_form_id', table_name='crm_google_form_submissions')
    op.drop_index('idx_customer_id_forms', table_name='crm_google_form_submissions')
    op.drop_table('crm_google_form_submissions')
