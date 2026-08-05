"""Add engineering memory and generated documents."""
from alembic import op

revision = "0005_memory_docs"
down_revision = "0004_graphs"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS memory_entries (
      id VARCHAR(32) PRIMARY KEY,
      repository_id VARCHAR(32) NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
      user_id VARCHAR(32) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      kind VARCHAR(32) NOT NULL DEFAULT 'note',
      title VARCHAR(255) NOT NULL,
      content TEXT NOT NULL,
      created_at TIMESTAMPTZ DEFAULT now()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_memory_entries_repository_id ON memory_entries(repository_id)")
    op.execute("""
    CREATE TABLE IF NOT EXISTS generated_documents (
      id VARCHAR(32) PRIMARY KEY,
      repository_id VARCHAR(32) NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
      user_id VARCHAR(32) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      kind VARCHAR(32) NOT NULL DEFAULT 'overview',
      title VARCHAR(255) NOT NULL,
      content TEXT NOT NULL,
      created_at TIMESTAMPTZ DEFAULT now()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_generated_documents_repository_id ON generated_documents(repository_id)")

def downgrade() -> None:
    op.drop_table("generated_documents")
    op.drop_table("memory_entries")
