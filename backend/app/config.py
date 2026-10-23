import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "HackMate Backend"
    environment: str = os.getenv("ENVIRONMENT", "development")
    backend_host: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    backend_port: int = int(os.getenv("BACKEND_PORT", "8000"))
    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    runner_workspace_root: str = os.getenv("RUNNER_WORKSPACE_ROOT", "./generated")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
