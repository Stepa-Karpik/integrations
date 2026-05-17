"""link watched sources to downstream document sources"""
from alembic import op
import sqlalchemy as sa

revision = "0002_downstream_source_id"
down_revision = "0001_initial_integrations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("watched_sources", sa.Column("downstream_source_id", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("watched_sources", "downstream_source_id")
