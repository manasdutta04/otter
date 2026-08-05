"""Add repository health reports."""
from alembic import op
revision = "0008_health"
down_revision = "0007_task_patches"
branch_labels = None
depends_on = None
def upgrade() -> None:
    op.execute("""CREATE TABLE IF NOT EXISTS repository_health (repository_id VARCHAR(32) PRIMARY KEY REFERENCES repositories(id) ON DELETE CASCADE, architecture_score INTEGER NOT NULL DEFAULT 0, security_score INTEGER NOT NULL DEFAULT 0, maintainability_score INTEGER NOT NULL DEFAULT 0, performance_score INTEGER NOT NULL DEFAULT 0, debt_score INTEGER NOT NULL DEFAULT 0, documentation_score INTEGER NOT NULL DEFAULT 0, dependency_score INTEGER NOT NULL DEFAULT 0, complexity_score INTEGER NOT NULL DEFAULT 0, findings TEXT NOT NULL DEFAULT '[]', analyzed_at TIMESTAMPTZ DEFAULT now())""")
def downgrade() -> None:
    op.drop_table("repository_health")
