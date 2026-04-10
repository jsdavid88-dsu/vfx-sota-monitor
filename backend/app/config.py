"""Application configuration via pydantic-settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://vfx:vfx@db:5432/vfx_sota"

    # Ollama
    ollama_base_url: str = "http://host.docker.internal:11434/v1"
    ollama_model: str = "gemma4:26b"
    ollama_api_key: str = "ollama"  # Ollama ignores this

    # External APIs
    github_token: str = ""
    hf_token: str = ""
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "vfx-sota-monitor"

    # App
    api_prefix: str = "/api"
    cors_origins: list[str] = ["http://localhost:3001", "http://localhost:5173"]


settings = Settings()
