from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "veridexs API"
    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = "http://localhost:8000/auth/github/callback"
    next_public_url: str = "http://localhost:3000"
    repository_data_dir: str = "./data/repositories"
    database_url: str = "postgresql+asyncpg://veridexs:veridexs@postgres:5432/veridexs"
    redis_url: str = "redis://redis:6379/0"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = "https://api.openai.com/v1"
    github_api_url: str = "https://api.github.com"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache
def get_settings() -> Settings:
    return Settings()
