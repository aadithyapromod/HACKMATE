import os
from pathlib import Path
from typing import Literal, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core App Settings
    ENVIRONMENT: Literal["development", "production", "test"] = "development"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    PROJECT_NAME: str = "HackMate Core API"
    API_V2_PREFIX: str = "/api/v2"
    CORS_ORIGINS: str = "*"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./hackmate.db"

    # Workspace directory for generated code
    WORKSPACE_BASE_DIR: str = str(Path(__file__).resolve().parent.parent.parent / "workspace" / "projects")

    # Execution Runner Settings
    RUNNER_TYPE: Literal["docker", "local"] = "docker"
    ENABLE_LOCAL_DEV_RUNNER: bool = False
    DOCKER_IMAGE_NAME: str = "hackmate-sandbox:latest"
    BUILD_TIMEOUT_SECONDS: int = 120
    MAX_REPAIR_ATTEMPTS: int = 1

    # AI Integration
    GEMINI_API_KEY: str = Field(default="", description="Google Gemini API key")
    GEMINI_MODEL: str = "gemini-flash-latest"

    # Optional Integrations
    FIRECRAWL_API_KEY: str = ""
    N8N_WEBHOOK_URL: str = ""
    N8N_WEBHOOK_SECRET: str = ""
    ADAPTION_API_KEY: str = ""

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def normalized_database_url(self) -> str:
        """Converts Render postgresql:// or postgres:// to postgresql+asyncpg://"""
        url = self.DATABASE_URL.strip()
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and "+asyncpg" not in url:
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    @property
    def resolved_workspace_path(self) -> Path:
        path = Path(self.WORKSPACE_BASE_DIR).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def parsed_cors_origins(self) -> List[str]:
        if self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
