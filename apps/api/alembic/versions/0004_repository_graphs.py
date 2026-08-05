"""Add persisted repository architecture graphs."""
from alembic import op

revision = "0004_graphs"
down_revision = "0003_plans"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS repository_graphs (
      repository_id VARCHAR(32) PRIMARY KEY REFERENCES repositories(id) ON DELETE CASCADE,
      nodes TEXT NOT NULL DEFAULT '[]',
      edges TEXT NOT NULL DEFAULT '[]',
      generated_at TIMESTAMPTZ DEFAULT now()
    )
    """)

def downgrade() -> None:
    op.drop_table("repository_graphs")
