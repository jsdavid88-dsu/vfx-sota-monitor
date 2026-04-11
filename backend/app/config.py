"""Application configuration via pydantic-settings."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Look for .env in project root (preferred) then backend/
ENV_FILES = (PROJECT_ROOT / ".env", BACKEND_DIR / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILES, extra="ignore")

    # Database (SQLite native by default — no Docker needed)
    database_url: str = f"sqlite+aiosqlite:///{DATA_DIR / 'vfx_sota.db'}"

    # External APIs
    github_token: str = ""
    hf_token: str = ""
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "vfx-sota-monitor"

    # App
    api_prefix: str = "/api"
    cors_origins: list[str] = [
        "http://localhost:3001",
        "http://localhost:5173",
        "http://127.0.0.1:3001",
    ]

    # Admin (worker authentication — set a shared secret in .env)
    admin_token: str = "change-me-in-production"

    # Firecrawl self-hosted endpoint (empty or disabled = Reddit-only feed)
    firecrawl_base_url: str = "http://localhost:3002"
    firecrawl_enabled: bool = True


settings = Settings()
