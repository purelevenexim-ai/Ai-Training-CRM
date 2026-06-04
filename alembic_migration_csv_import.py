"""Create CSV import tables
Revision ID: 009
Create Date: 2026-05-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade():
    """Create import job, import result, bulk operation tables"""
    
    # Create import_jobs table
    op.create_table(
        'crm_import_jobs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('file_size', sa.Integer, nullable=False),
        sa.Column('row_count', sa.Integer, nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('validation_errors', postgresql.JSON, nullable=True),
        sa.Column('processed_count', sa.Integer, server_default='0'),
        sa.Column('success_count', sa.Integer, server_default='0'),
        sa.Column('duplicate_count', sa.Integer, server_default='0'),
        sa.Column('error_count', sa.Integer, server_default='0'),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_import_status', 'crm_import_jobs', ['status'])
    op.create_index('idx_import_created', 'crm_import_jobs', ['created_at'])
    
    # Create import_results table
    op.create_table(
        'crm_import_results',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('job_id', sa.String(36), nullable=False),
        sa.Column('row_index', sa.Integer, nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('customer_id', sa.String(36), nullable=True),
        sa.Column('error_message', sa.String(500), nullable=True),
        sa.Column('data', postgresql.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['crm_import_jobs.id']),
        sa.ForeignKeyConstraint(['customer_id'], ['crm_customers.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_result_job', 'crm_import_results', ['job_id'])
    op.create_index('idx_result_status', 'crm_import_results', ['status'])
    
    # Create bulk_operations table
    op.create_table(
        'crm_bulk_operations',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('operation_type', sa.String(50), nullable=False),
        sa.Column('customer_count', sa.Integer, nullable=False),
        sa.Column('operation_data', postgresql.JSON, nullable=False),
        sa.Column('status', sa.String(50), server_default='pending'),
        sa.Column('success_count', sa.Integer, server_default='0'),
        sa.Column('error_count', sa.Integer, server_default='0'),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_bulk_status', 'crm_bulk_operations', ['status'])
    op.create_index('idx_bulk_created', 'crm_bulk_operations', ['created_at'])
    
    # Create bulk_operation_results table
    op.create_table(
        'crm_bulk_operation_results',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('operation_id', sa.String(36), nullable=False),
        sa.Column('customer_id', sa.String(36), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('error_message', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.ForeignKeyConstraint(['operation_id'], ['crm_bulk_operations.id']),
        sa.ForeignKeyConstraint(['customer_id'], ['crm_customers.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_bulk_result_operation', 'crm_bulk_operation_results', ['operation_id'])
    op.create_index('idx_bulk_result_customer', 'crm_bulk_operation_results', ['customer_id'])


def downgrade():
    """Drop CSV import tables"""
    op.drop_index('idx_bulk_result_customer', 'crm_bulk_operation_results')
    op.drop_index('idx_bulk_result_operation', 'crm_bulk_operation_results')
    op.drop_table('crm_bulk_operation_results')
    
    op.drop_index('idx_bulk_created', 'crm_bulk_operations')
    op.drop_index('idx_bulk_status', 'crm_bulk_operations')
    op.drop_table('crm_bulk_operations')
    
    op.drop_index('idx_result_status', 'crm_import_results')
    op.drop_index('idx_result_job', 'crm_import_results')
    op.drop_table('crm_import_results')
    
    op.drop_index('idx_import_created', 'crm_import_jobs')
    op.drop_index('idx_import_status', 'crm_import_jobs')
    op.drop_table('crm_import_jobs')
