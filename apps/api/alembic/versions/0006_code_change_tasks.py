"""Add approval-gated coding tasks."""
from alembic import op
revision = "0006_code_tasks"
down_revision = "0005_memory_docs"
branch_labels = None
depends_on = None
def upgrade() -> None:
    op.execute("""CREATE TABLE IF NOT EXISTS code_change_tasks (id VARCHAR(32) PRIMARY KEY, repository_id VARCHAR(32) NOT NULL REFERENCES repositories(id) ON DELETE CASCADE, user_id VARCHAR(32) NOT NULL REFERENCES users(id) ON DELETE CASCADE, plan_id VARCHAR(32) REFERENCES repository_plans(id) ON DELETE SET NULL, request TEXT NOT NULL, status VARCHAR(32) NOT NULL DEFAULT 'draft', proposed_summary TEXT NOT NULL DEFAULT '', approval_note TEXT, created_at TIMESTAMPTZ DEFAULT now(), approved_at TIMESTAMPTZ)""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_code_change_tasks_repository_id ON code_change_tasks(repository_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_code_change_tasks_user_id ON code_change_tasks(user_id)")
def downgrade() -> None:
    op.drop_table("code_change_tasks")
