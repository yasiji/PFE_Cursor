"""Database configuration and session management."""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import Generator

from shared.config import get_config
from shared.logging_setup import get_logger

logger = get_logger(__name__)

# Get database URL from config
config = get_config()
database_url = config.database.url

# Create engine
engine = create_engine(
    database_url,
    connect_args={"check_same_thread": False} if "sqlite" in database_url else {},
    echo=config.database.echo
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db() -> Generator:
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database (create tables)."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized")

