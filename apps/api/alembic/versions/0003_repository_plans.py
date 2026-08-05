"""Add persisted planning engine output."""
from alembic import op

revision = "0003_plans"
down_revision = "0002_intelligence"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS repository_plans (
      id VARCHAR(32) PRIMARY KEY,
      repository_id VARCHAR(32) NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
      user_id VARCHAR(32) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      request TEXT NOT NULL,
      title VARCHAR(255) NOT NULL,
      complexity VARCHAR(32) NOT NULL,
      summary TEXT NOT NULL,
      steps TEXT NOT NULL DEFAULT '[]',
      affected_files TEXT NOT NULL DEFAULT '[]',
      dependencies TEXT NOT NULL DEFAULT '[]',
      risks TEXT NOT NULL DEFAULT '[]',
      created_at TIMESTAMPTZ DEFAULT now()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_repository_plans_repository_id ON repository_plans(repository_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_repository_plans_user_id ON repository_plans(user_id)")

def downgrade() -> None:
    op.drop_table("repository_plans")
