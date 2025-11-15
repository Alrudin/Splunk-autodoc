"""Application configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )

    # Database configuration
    db_url: str = "sqlite:///./flow.db"

    # CORS configuration (comma-separated string, parsed when needed)
    allow_origins: str = "http://localhost:5173,http://localhost:8080"

    # Storage configuration
    storage_root: str = "data"

    # Server configuration
    workers: int = 4
    log_level: str = "info"

    @property
    def origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.allow_origins.split(",") if origin.strip()]


# Global settings instance
settings = Settings()
