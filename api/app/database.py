"""Database connection management."""

from collections.abc import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.models.base import Base


# Detect database type from URL
def is_sqlite(url: str) -> bool:
    """Check if the database URL is for SQLite."""
    return url.startswith("sqlite")


# Configure engine based on database type
if is_sqlite(settings.database_url):
    # SQLite configuration
    engine = create_engine(
        settings.database_url,
        echo=settings.echo_sql,
        connect_args={"check_same_thread": False},
    )

    # Enable foreign keys for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        """Enable foreign keys for SQLite connections."""
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

else:
    # PostgreSQL configuration
    engine = create_engine(
        settings.database_url,
        echo=settings.echo_sql,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions.

    Yields a database session and ensures cleanup.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize database by creating all tables.

    Useful for testing and SQLite development mode.
    """
    # Import all models to ensure they're registered

    Base.metadata.create_all(bind=engine)


def check_db_connection() -> bool:
    """
    Check database connectivity.

    Returns True if database is accessible, False otherwise.
    Used by healthcheck endpoint.
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
