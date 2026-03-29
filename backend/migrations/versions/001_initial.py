"""Initial schema

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Enable TimescaleDB
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")

    op.create_table(
        'projects',
        sa.Column('id',          sa.String, primary_key=True),
        sa.Column('name',        sa.String, nullable=False),
        sa.Column('slug',        sa.String, unique=True, nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('repo_url',    sa.String),
        sa.Column('api_key',     sa.String, unique=True),
        sa.Column('created_at',  sa.DateTime),
        sa.Column('updated_at',  sa.DateTime),
    )

    op.create_table(
        'users',
        sa.Column('id',              sa.String, primary_key=True),
        sa.Column('email',           sa.String, unique=True, nullable=False),
        sa.Column('name',            sa.String, nullable=False),
        sa.Column('hashed_password', sa.String, nullable=False),
        sa.Column('role',            sa.String, default='member'),
        sa.Column('created_at',      sa.DateTime),
    )

    op.create_table(
        'runs',
        sa.Column('id',             sa.String, primary_key=True),
        sa.Column('project_id',     sa.String, sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('tool',           sa.String, nullable=False),
        sa.Column('tool_version',   sa.String),
        sa.Column('branch',         sa.String),
        sa.Column('commit_sha',     sa.String),
        sa.Column('commit_message', sa.String),
        sa.Column('pr_number',      sa.String),
        sa.Column('environment',    sa.String),
        sa.Column('ci_provider',    sa.String),
        sa.Column('ci_run_url',     sa.String),
        sa.Column('triggered_by',   sa.String),
        sa.Column('started_at',     sa.DateTime, nullable=False),
        sa.Column('finished_at',    sa.DateTime),
        sa.Column('duration_ms',    sa.Integer, default=0),
        sa.Column('total',          sa.Integer, default=0),
        sa.Column('passed',         sa.Integer, default=0),
        sa.Column('failed',         sa.Integer, default=0),
        sa.Column('skipped',        sa.Integer, default=0),
        sa.Column('flaky',          sa.Integer, default=0),
        sa.Column('pass_rate',      sa.Float,   default=0.0),
        sa.Column('run_metadata',   sa.JSON,    default=dict),
    )
    op.create_index('ix_runs_project_started', 'runs', ['project_id', 'started_at'])

    op.create_table(
        'test_results',
        sa.Column('id',              sa.String, primary_key=True),
        sa.Column('run_id',          sa.String, sa.ForeignKey('runs.id'), nullable=False),
        sa.Column('project_id',      sa.String, nullable=False),
        sa.Column('name',            sa.String, nullable=False),
        sa.Column('suite',           sa.String, nullable=False),
        sa.Column('file_path',       sa.String),
        sa.Column('status',          sa.String, nullable=False),
        sa.Column('duration_ms',     sa.Integer, default=0),
        sa.Column('started_at',      sa.DateTime),
        sa.Column('error_message',   sa.Text),
        sa.Column('stack_trace',     sa.Text),
        sa.Column('ai_category',     sa.String),
        sa.Column('ai_root_cause',   sa.Text),
        sa.Column('ai_fix',          sa.Text),
        sa.Column('ai_confidence',   sa.Float),
        sa.Column('flaky_score',     sa.Float),
        sa.Column('retry_count',     sa.Integer, default=0),
        sa.Column('browser',         sa.String),
        sa.Column('platform',        sa.String),
        sa.Column('device',          sa.String),
        sa.Column('screenshot_url',  sa.String),
        sa.Column('video_url',       sa.String),
        sa.Column('trace_url',       sa.String),
        sa.Column('tags',            sa.JSON, default=list),
        sa.Column('steps',           sa.JSON, default=list),
        sa.Column('result_metadata', sa.JSON, default=dict),
    )
    op.create_index('ix_results_run_id',       'test_results', ['run_id'])
    op.create_index('ix_results_project_name', 'test_results', ['project_id', 'name'])
    op.create_index('ix_results_status',       'test_results', ['status'])
    op.create_index('ix_results_flaky_score',  'test_results', ['flaky_score'])

    # Convert test_results to TimescaleDB hypertable for fast time-series queries
    op.execute("""
        SELECT create_hypertable(
            'test_results', 
            'started_at',
            if_not_exists => TRUE,
            migrate_data => TRUE
        );
    """)

    op.create_table(
        'comments',
        sa.Column('id',             sa.String, primary_key=True),
        sa.Column('test_result_id', sa.String, sa.ForeignKey('test_results.id'), nullable=False),
        sa.Column('author',         sa.String, nullable=False),
        sa.Column('body',           sa.Text, nullable=False),
        sa.Column('created_at',     sa.DateTime),
    )

    op.create_table(
        'custom_kpis',
        sa.Column('id',          sa.String, primary_key=True),
        sa.Column('project_id',  sa.String, sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('name',        sa.String, nullable=False),
        sa.Column('formula',     sa.Text, nullable=False),
        sa.Column('threshold',   sa.Float),
        sa.Column('created_at',  sa.DateTime),
    )


def downgrade():
    op.drop_table('custom_kpis')
    op.drop_table('comments')
    op.drop_table('test_results')
    op.drop_table('runs')
    op.drop_table('users')
    op.drop_table('projects')
