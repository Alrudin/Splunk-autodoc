"""Application configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database configuration
    db_url: str = "sqlite:///./flow.db"

    # CORS configuration
    allow_origins: list[str] = ["http://localhost:5173", "http://localhost:8080"]

    # Storage configuration
    storage_root: str = "/data"

    # Server configuration
    workers: int = 4
    log_level: str = "info"

    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
