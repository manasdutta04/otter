"""Add structured coding task patches."""
from alembic import op
revision = "0007_task_patches"
down_revision = "0006_code_tasks"
branch_labels = None
depends_on = None
def upgrade() -> None:
    op.execute("ALTER TABLE code_change_tasks ADD COLUMN IF NOT EXISTS patch_json TEXT NOT NULL DEFAULT '[]'")
    op.execute("ALTER TABLE code_change_tasks ADD COLUMN IF NOT EXISTS changed_files TEXT NOT NULL DEFAULT '[]'")
    op.execute("ALTER TABLE code_change_tasks ADD COLUMN IF NOT EXISTS applied_at TIMESTAMPTZ")
def downgrade() -> None:
    op.execute("ALTER TABLE code_change_tasks DROP COLUMN IF EXISTS applied_at")
    op.execute("ALTER TABLE code_change_tasks DROP COLUMN IF EXISTS changed_files")
    op.execute("ALTER TABLE code_change_tasks DROP COLUMN IF EXISTS patch_json")
