"""
HC-XCDSS Database Session & Engine Configuration
Supports dual environments:
- Local Development: SQLite (outputs/hc_xcdss.db)
- Production / Render: PostgreSQL (via DATABASE_URL)
"""

import os
from pathlib import Path
from sqlalchemy import create_engine, event, Engine
from sqlalchemy.orm import sessionmaker, Session

# --------------------------------------------------
# Project Paths & Default SQLite Database File
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIRECTORY = PROJECT_ROOT / "outputs"
OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

DEFAULT_SQLITE_FILE = OUTPUT_DIRECTORY / "hc_xcdss.db"
DEFAULT_SQLITE_URL = f"sqlite:///{DEFAULT_SQLITE_FILE.as_posix()}"
DATABASE_FILE = DEFAULT_SQLITE_FILE


def normalize_database_url(url: str) -> str:
    """
    Normalizes database URL schemes, converting Render's 'postgres://' to 'postgresql://'.
    """
    if not url:
        return url
    trimmed = url.strip()
    if trimmed.startswith("postgres://"):
        return trimmed.replace("postgres://", "postgresql://", 1)
    return trimmed


def get_database_url() -> str:
    """
    Resolves the active database URL from environment or falls back to local SQLite.
    """
    raw_url = os.getenv("DATABASE_URL")
    if raw_url and raw_url.strip():
        return normalize_database_url(raw_url)
    return DEFAULT_SQLITE_URL


def create_app_engine(database_url: str) -> Engine:
    """
    Creates and configures an engine according to the dialect.
    """
    is_sqlite = database_url.startswith("sqlite")

    if is_sqlite:
        app_engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            echo=False,
        )

        @event.listens_for(app_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return app_engine

    # PostgreSQL / other production RDBMS
    return create_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=5,
        max_overflow=10,
        echo=False,
    )


# Active Database URL & Engine Instance
DATABASE_URL = get_database_url()
engine = create_app_engine(DATABASE_URL)

# --------------------------------------------------
# Session Local Factory
# --------------------------------------------------

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# --------------------------------------------------
# Dependency / Context Manager Helper
# --------------------------------------------------

def get_db() -> Session:
    """
    Yields a database session and ensures proper closure.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

