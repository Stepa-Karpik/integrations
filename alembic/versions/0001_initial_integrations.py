"""initial integrations schema"""
from alembic import op
import sqlalchemy as sa
revision = '0001_initial_integrations'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table('connections',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('owner_subject_id', sa.String(length=128), nullable=False),
        sa.Column('provider', sa.String(length=64), nullable=False),
        sa.Column('access_token', sa.String(length=2048), nullable=False),
        sa.Column('refresh_token', sa.String(length=2048), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_connections_owner_subject_id', 'connections', ['owner_subject_id'])
    op.create_table('watched_sources',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('owner_subject_id', sa.String(length=128), nullable=False),
        sa.Column('provider', sa.String(length=64), nullable=False),
        sa.Column('root_path', sa.String(length=1024), nullable=False),
        sa.Column('connection_id', sa.String(length=64), sa.ForeignKey('connections.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_watched_sources_owner_subject_id', 'watched_sources', ['owner_subject_id'])
    op.create_table('sync_jobs',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('source_id', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_sync_jobs_source_id', 'sync_jobs', ['source_id'])

def downgrade() -> None:
    op.drop_index('ix_sync_jobs_source_id', table_name='sync_jobs')
    op.drop_table('sync_jobs')
    op.drop_index('ix_watched_sources_owner_subject_id', table_name='watched_sources')
    op.drop_table('watched_sources')
    op.drop_index('ix_connections_owner_subject_id', table_name='connections')
    op.drop_table('connections')
