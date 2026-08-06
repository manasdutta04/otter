"""Create OTTER Phase 1 schema."""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS users (
      id VARCHAR(32) PRIMARY KEY,
      github_id VARCHAR(64) NOT NULL UNIQUE,
      login VARCHAR(255) NOT NULL,
      avatar_url TEXT,
      created_at TIMESTAMPTZ DEFAULT now()
    )
    """)
    op.execute("""
    CREATE TABLE IF NOT EXISTS auth_sessions (
      id VARCHAR(64) PRIMARY KEY,
      user_id VARCHAR(32) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      github_token TEXT NOT NULL,
      expires_at TIMESTAMPTZ NOT NULL
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_auth_sessions_user_id ON auth_sessions(user_id)")
    op.execute("""
    CREATE TABLE IF NOT EXISTS repositories (
      id VARCHAR(32) PRIMARY KEY,
      user_id VARCHAR(32) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      url TEXT NOT NULL,
      name VARCHAR(255) NOT NULL,
      status VARCHAR(32) NOT NULL DEFAULT 'queued',
      branch VARCHAR(255),
      file_count INTEGER NOT NULL DEFAULT 0,
      error TEXT,
      created_at TIMESTAMPTZ DEFAULT now()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_repositories_user_id ON repositories(user_id)")
    op.execute("""
    CREATE TABLE IF NOT EXISTS repository_import_jobs (
      id VARCHAR(32) PRIMARY KEY,
      repository_id VARCHAR(32) NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
      user_id VARCHAR(32) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      status VARCHAR(32) NOT NULL DEFAULT 'queued',
      attempt_count INTEGER NOT NULL DEFAULT 0,
      error TEXT,
      started_at TIMESTAMPTZ,
      finished_at TIMESTAMPTZ,
      created_at TIMESTAMPTZ DEFAULT now()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_repository_import_jobs_repository_id ON repository_import_jobs(repository_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_repository_import_jobs_user_id ON repository_import_jobs(user_id)")

def downgrade() -> None:
    op.drop_table("repository_import_jobs")
    op.drop_table("repositories")
    op.drop_table("auth_sessions")
    op.drop_table("users")
