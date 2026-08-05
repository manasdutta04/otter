"""Add repository intelligence storage."""
from alembic import op

revision = "0002_intelligence"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS repository_intelligence (
      repository_id VARCHAR(32) PRIMARY KEY REFERENCES repositories(id) ON DELETE CASCADE,
      summary TEXT NOT NULL DEFAULT '',
      tech_stack TEXT NOT NULL DEFAULT '[]',
      folders TEXT NOT NULL DEFAULT '[]',
      entry_points TEXT NOT NULL DEFAULT '[]',
      architecture_signals TEXT NOT NULL DEFAULT '[]',
      analyzed_at TIMESTAMPTZ DEFAULT now()
    )
    """)

def downgrade() -> None:
    op.drop_table("repository_intelligence")
