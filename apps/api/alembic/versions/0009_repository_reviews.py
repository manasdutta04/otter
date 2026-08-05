"""Add persisted repository review reports."""
from alembic import op
revision = "0009_reviews"
down_revision = "0008_health"
branch_labels = None
depends_on = None
def upgrade() -> None:
    op.execute("CREATE TABLE IF NOT EXISTS repository_reviews (id VARCHAR(32) PRIMARY KEY, repository_id VARCHAR(32) NOT NULL REFERENCES repositories(id) ON DELETE CASCADE, user_id VARCHAR(32) NOT NULL REFERENCES users(id) ON DELETE CASCADE, findings TEXT NOT NULL DEFAULT '[]', created_at TIMESTAMPTZ DEFAULT now())")
    op.execute("CREATE INDEX IF NOT EXISTS ix_repository_reviews_repository_id ON repository_reviews(repository_id)")
def downgrade() -> None:
    op.drop_table("repository_reviews")
