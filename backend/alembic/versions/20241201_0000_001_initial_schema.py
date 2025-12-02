"""Initial database schema for Tronas PIA Platform

Revision ID: 001
Revises:
Create Date: 2024-12-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE requeststatus AS ENUM ('new', 'acknowledged', 'in_progress', 'pending_department_review', 'pending_ag_ruling', 'extension_requested', 'released', 'closed_no_records', 'withdrawn')")
    op.execute("CREATE TYPE requesttype AS ENUM ('standard', 'expedited', 'recurring', 'media', 'legal')")
    op.execute("CREATE TYPE documentclassification AS ENUM ('responsive', 'non_responsive', 'partially_responsive', 'exempt', 'unclassified')")
    op.execute("CREATE TYPE documentstatus AS ENUM ('pending', 'processing', 'classified', 'reviewed', 'redacted', 'approved', 'released', 'withheld')")
    op.execute("CREATE TYPE tasktype AS ENUM ('email_retrieval', 'document_retrieval', 'text_extraction', 'ocr_processing', 'classification', 'deduplication', 'human_review', 'redaction', 'response_generation', 'cost_calculation', 'release_preparation')")
    op.execute("CREATE TYPE taskstatus AS ENUM ('pending', 'in_progress', 'completed', 'failed', 'skipped')")
    op.execute("CREATE TYPE userrole AS ENUM ('admin', 'pia_coordinator', 'department_reviewer', 'legal_reviewer', 'viewer')")

    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('azure_ad_id', sa.String(255), nullable=True),
        sa.Column('role', postgresql.ENUM('admin', 'pia_coordinator', 'department_reviewer', 'legal_reviewer', 'viewer', name='userrole', create_type=False), nullable=False, server_default='viewer'),
        sa.Column('department', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('azure_ad_id')
    )
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_azure_ad_id', 'users', ['azure_ad_id'])

    # PIA Requests table
    op.create_table(
        'pia_requests',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('request_number', sa.String(50), nullable=False),
        sa.Column('requester_name', sa.String(255), nullable=False),
        sa.Column('requester_email', sa.String(255), nullable=False),
        sa.Column('requester_phone', sa.String(50), nullable=True),
        sa.Column('requester_organization', sa.String(255), nullable=True),
        sa.Column('requester_address', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('date_received', sa.Date(), nullable=False),
        sa.Column('response_deadline', sa.Date(), nullable=False),
        sa.Column('extension_deadline', sa.Date(), nullable=True),
        sa.Column('date_completed', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', postgresql.ENUM('new', 'acknowledged', 'in_progress', 'pending_department_review', 'pending_ag_ruling', 'extension_requested', 'released', 'closed_no_records', 'withdrawn', name='requeststatus', create_type=False), nullable=False, server_default='new'),
        sa.Column('request_type', postgresql.ENUM('standard', 'expedited', 'recurring', 'media', 'legal', name='requesttype', create_type=False), nullable=False, server_default='standard'),
        sa.Column('priority', sa.String(20), nullable=False, server_default='medium'),
        sa.Column('assigned_to', sa.Integer(), nullable=True),
        sa.Column('departments_involved', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('search_terms', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('date_range_start', sa.Date(), nullable=True),
        sa.Column('date_range_end', sa.Date(), nullable=True),
        sa.Column('total_documents', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_pages', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('responsive_documents', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('redacted_documents', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('withheld_documents', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('estimated_cost', sa.Numeric(10, 2), nullable=True),
        sa.Column('actual_cost', sa.Numeric(10, 2), nullable=True),
        sa.Column('cost_waived', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('cost_waiver_reason', sa.Text(), nullable=True),
        sa.Column('ag_submission_date', sa.Date(), nullable=True),
        sa.Column('ag_ruling_date', sa.Date(), nullable=True),
        sa.Column('ag_ruling_reference', sa.String(100), nullable=True),
        sa.Column('exemptions_cited', postgresql.JSONB(), nullable=True),
        sa.Column('delivery_method', sa.String(50), nullable=True, server_default='email'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('classification_complete', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deduplication_complete', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('ocr_complete', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_overdue', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['assigned_to'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('request_number')
    )
    op.create_index('ix_pia_requests_request_number', 'pia_requests', ['request_number'])
    op.create_index('ix_pia_requests_status', 'pia_requests', ['status'])
    op.create_index('ix_pia_requests_date_received', 'pia_requests', ['date_received'])
    op.create_index('ix_pia_requests_response_deadline', 'pia_requests', ['response_deadline'])
    op.create_index('ix_pia_requests_requester_email', 'pia_requests', ['requester_email'])

    # Documents table
    op.create_table(
        'documents',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('request_id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(500), nullable=False),
        sa.Column('original_path', sa.Text(), nullable=True),
        sa.Column('storage_path', sa.Text(), nullable=True),
        sa.Column('file_type', sa.String(50), nullable=True),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('file_size', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('file_hash', sa.String(64), nullable=True),
        sa.Column('page_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('source_type', sa.String(50), nullable=True),
        sa.Column('source_location', sa.Text(), nullable=True),
        sa.Column('classification', postgresql.ENUM('responsive', 'non_responsive', 'partially_responsive', 'exempt', 'unclassified', name='documentclassification', create_type=False), nullable=False, server_default='unclassified'),
        sa.Column('classification_confidence', sa.Float(), nullable=True),
        sa.Column('classification_reasoning', sa.Text(), nullable=True),
        sa.Column('exemptions', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('status', postgresql.ENUM('pending', 'processing', 'classified', 'reviewed', 'redacted', 'approved', 'released', 'withheld', name='documentstatus', create_type=False), nullable=False, server_default='pending'),
        sa.Column('extracted_text', sa.Text(), nullable=True),
        sa.Column('ocr_text', sa.Text(), nullable=True),
        sa.Column('ocr_confidence', sa.Float(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('is_duplicate', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('duplicate_of_id', sa.Integer(), nullable=True),
        sa.Column('needs_redaction', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('redaction_notes', sa.Text(), nullable=True),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['request_id'], ['pia_requests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['duplicate_of_id'], ['documents.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_documents_request_id', 'documents', ['request_id'])
    op.create_index('ix_documents_classification', 'documents', ['classification'])
    op.create_index('ix_documents_status', 'documents', ['status'])
    op.create_index('ix_documents_file_hash', 'documents', ['file_hash'])

    # Email Threads table
    op.create_table(
        'email_threads',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('request_id', sa.Integer(), nullable=False),
        sa.Column('thread_id', sa.String(255), nullable=False),
        sa.Column('subject', sa.String(500), nullable=True),
        sa.Column('participants', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('email_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('first_email_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_email_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_responsive', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['request_id'], ['pia_requests.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_email_threads_request_id', 'email_threads', ['request_id'])
    op.create_index('ix_email_threads_thread_id', 'email_threads', ['thread_id'])

    # Emails table
    op.create_table(
        'emails',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('request_id', sa.Integer(), nullable=False),
        sa.Column('thread_id', sa.Integer(), nullable=True),
        sa.Column('message_id', sa.String(255), nullable=False),
        sa.Column('internet_message_id', sa.String(500), nullable=True),
        sa.Column('conversation_id', sa.String(255), nullable=True),
        sa.Column('subject', sa.String(500), nullable=True),
        sa.Column('sender', sa.String(255), nullable=True),
        sa.Column('recipients', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('cc', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('bcc', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('sent_datetime', sa.DateTime(timezone=True), nullable=True),
        sa.Column('received_datetime', sa.DateTime(timezone=True), nullable=True),
        sa.Column('body_preview', sa.Text(), nullable=True),
        sa.Column('body_content', sa.Text(), nullable=True),
        sa.Column('has_attachments', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('attachment_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('importance', sa.String(20), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_draft', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('categories', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('web_link', sa.Text(), nullable=True),
        sa.Column('is_duplicate', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('duplicate_of_id', sa.Integer(), nullable=True),
        sa.Column('classification', postgresql.ENUM('responsive', 'non_responsive', 'partially_responsive', 'exempt', 'unclassified', name='documentclassification', create_type=False), nullable=False, server_default='unclassified'),
        sa.Column('classification_confidence', sa.Float(), nullable=True),
        sa.Column('raw_data', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['request_id'], ['pia_requests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['thread_id'], ['email_threads.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['duplicate_of_id'], ['emails.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_emails_request_id', 'emails', ['request_id'])
    op.create_index('ix_emails_message_id', 'emails', ['message_id'])
    op.create_index('ix_emails_thread_id', 'emails', ['thread_id'])
    op.create_index('ix_emails_sent_datetime', 'emails', ['sent_datetime'])

    # Workflow Tasks table
    op.create_table(
        'workflow_tasks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('request_id', sa.Integer(), nullable=False),
        sa.Column('task_type', postgresql.ENUM('email_retrieval', 'document_retrieval', 'text_extraction', 'ocr_processing', 'classification', 'deduplication', 'human_review', 'redaction', 'response_generation', 'cost_calculation', 'release_preparation', name='tasktype', create_type=False), nullable=False),
        sa.Column('task_name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', postgresql.ENUM('pending', 'in_progress', 'completed', 'failed', 'skipped', name='taskstatus', create_type=False), nullable=False, server_default='pending'),
        sa.Column('order_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_automated', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('requires_human_approval', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('assigned_to', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('input_data', postgresql.JSONB(), nullable=True),
        sa.Column('output_data', postgresql.JSONB(), nullable=True),
        sa.Column('dependencies', postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['request_id'], ['pia_requests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_to'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_workflow_tasks_request_id', 'workflow_tasks', ['request_id'])
    op.create_index('ix_workflow_tasks_status', 'workflow_tasks', ['status'])
    op.create_index('ix_workflow_tasks_task_type', 'workflow_tasks', ['task_type'])

    # Audit Logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('request_id', sa.Integer(), nullable=True),
        sa.Column('document_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('old_values', postgresql.JSONB(), nullable=True),
        sa.Column('new_values', postgresql.JSONB(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['request_id'], ['pia_requests.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_request_id', 'audit_logs', ['request_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('audit_logs')
    op.drop_table('workflow_tasks')
    op.drop_table('emails')
    op.drop_table('email_threads')
    op.drop_table('documents')
    op.drop_table('pia_requests')
    op.drop_table('users')

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS userrole")
    op.execute("DROP TYPE IF EXISTS taskstatus")
    op.execute("DROP TYPE IF EXISTS tasktype")
    op.execute("DROP TYPE IF EXISTS documentstatus")
    op.execute("DROP TYPE IF EXISTS documentclassification")
    op.execute("DROP TYPE IF EXISTS requesttype")
    op.execute("DROP TYPE IF EXISTS requeststatus")
