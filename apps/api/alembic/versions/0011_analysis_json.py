"""Add analysis_json to repository_intelligence."""
from alembic import op

revision = "0011_analysis_json"
down_revision = "0010_arch_perf"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE repository_intelligence ADD COLUMN IF NOT EXISTS analysis_json TEXT NOT NULL DEFAULT '{}'"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE repository_intelligence DROP COLUMN IF EXISTS analysis_json")
