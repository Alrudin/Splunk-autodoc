"""Application configuration management."""

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = Field(
        default="sqlite:///./flow.db",
        validation_alias=AliasChoices("DB_URL", "DATABASE_URL", "database_url"),
        description="Database connection URL (supports DB_URL, DATABASE_URL, or database_url)",
    )
    echo_sql: bool = False

    # Storage
    storage_root: str = "/data"

    # Logging
    log_level: str = "info"

    # CORS
    allow_origins: list[str] | str = Field(
        default=["http://localhost:5173"],
        validation_alias=AliasChoices("ALLOW_ORIGINS", "allow_origins"),
    )
    workers: int = 4

    @field_validator("allow_origins", mode="before")
    @classmethod
    def parse_allow_origins(cls, v):
        """Parse ALLOW_ORIGINS from comma-separated string or list."""
        if isinstance(v, str):
            # Split comma-separated string and strip whitespace
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        # Return as-is if already a list
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )


# Singleton instance
settings = Settings()
