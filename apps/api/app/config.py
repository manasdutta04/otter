from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Otter API"
    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = "http://localhost:8000/auth/github/callback"
    # Public Cloudflare Worker that holds the Otter GitHub App secret.
    otter_auth_broker_url: str = ""
    # Must match REDEEM_HMAC_SECRET on the Worker when set.
    otter_auth_redeem_secret: str = ""
    next_public_url: str = "http://localhost:3000"
    repository_data_dir: str = "./data/repositories"
    database_url: str = "postgresql+asyncpg://otter:otter@127.0.0.1:5432/otter"
    redis_url: str = "redis://127.0.0.1:6379/0"
    llm_api_key: str = ""
    # Default: local Ollama coding model (no cloud key / no TPM caps).
    llm_model: str = "qwen2.5-coder:7b"
    llm_base_url: str = "http://127.0.0.1:11434/v1"
    # When true (default), try other local Ollama tags if the primary fails.
    llm_free_failover: bool = True
    github_api_url: str = "https://api.github.com"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def auth_broker_enabled(self) -> bool:
        return bool(self.otter_auth_broker_url.strip())

    @property
    def local_oauth_enabled(self) -> bool:
        return bool(self.github_client_id and self.github_client_secret)

@lru_cache
def get_settings() -> Settings:
    return Settings()
