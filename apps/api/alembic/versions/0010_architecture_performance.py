"""Add architecture and performance reports."""
from alembic import op
revision = "0010_arch_perf"
down_revision = "0009_reviews"
branch_labels = None
depends_on = None
def upgrade() -> None:
    op.execute("CREATE TABLE IF NOT EXISTS repository_architecture_analysis (repository_id VARCHAR(32) PRIMARY KEY REFERENCES repositories(id) ON DELETE CASCADE, score INTEGER NOT NULL DEFAULT 0, findings TEXT NOT NULL DEFAULT '[]', created_at TIMESTAMPTZ DEFAULT now())")
    op.execute("CREATE TABLE IF NOT EXISTS repository_performance (repository_id VARCHAR(32) PRIMARY KEY REFERENCES repositories(id) ON DELETE CASCADE, score INTEGER NOT NULL DEFAULT 0, hotspots TEXT NOT NULL DEFAULT '[]', created_at TIMESTAMPTZ DEFAULT now())")
def downgrade() -> None:
    op.drop_table("repository_performance")
    op.drop_table("repository_architecture_analysis")
