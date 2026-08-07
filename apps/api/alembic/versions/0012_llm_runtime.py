"""LLM runtime settings singleton."""
from alembic import op

revision = "0012_llm_runtime"
down_revision = "0011_analysis_json"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS llm_runtime_settings (
            id VARCHAR(32) PRIMARY KEY,
            provider VARCHAR(32) NOT NULL DEFAULT 'ollama',
            base_url TEXT NOT NULL DEFAULT 'http://127.0.0.1:11434/v1',
            model VARCHAR(255) NOT NULL DEFAULT 'qwen2.5-coder:7b',
            api_key TEXT NOT NULL DEFAULT '',
            free_failover BOOLEAN NOT NULL DEFAULT TRUE,
            configured BOOLEAN NOT NULL DEFAULT FALSE,
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS llm_runtime_settings")
