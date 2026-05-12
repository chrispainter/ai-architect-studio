import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "AI Architect Studio"
    debug: bool = False

    # Database
    database_url: str = "sqlite:///./ai_architect_studio.db"

    # Auth
    jwt_secret_key: str = "change-me-in-production-use-a-real-secret"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # Google / LLM
    google_api_key: str = ""
    github_personal_access_token: str = ""
    # Default to the stable production model. gemini-3.1-pro-preview hits
    # capacity spikes (frequent 503 UNAVAILABLE) and isn't reliable for
    # multi-agent crews. Override via GEMINI_MODEL env var when needed.
    gemini_model: str = "gemini-2.5-pro"

    # Stitch MCP (Phase 2)
    stitch_api_key: str = ""
    stitch_mcp_url: str = "https://stitch.googleapis.com/mcp"

    # n8n (Phase 4)
    n8n_base_url: str = ""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
