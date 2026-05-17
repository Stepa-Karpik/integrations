from alembic import op
import sqlalchemy as sa
revision = '0003_provider_credentials'
down_revision = '0002_downstream_source_id'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'provider_credentials',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('owner_subject_id', sa.String(length=128), nullable=False),
        sa.Column('provider', sa.String(length=64), nullable=False),
        sa.Column('client_id_encrypted', sa.String(length=4096), nullable=False),
        sa.Column('client_secret_encrypted', sa.String(length=4096), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_provider_credentials_owner_subject_id', 'provider_credentials', ['owner_subject_id'])

def downgrade():
    op.drop_index('ix_provider_credentials_owner_subject_id', table_name='provider_credentials')
    op.drop_table('provider_credentials')
