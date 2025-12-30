"""Database connection and session management."""

from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
from typing import Generator
import logging

from .config import get_settings
from services.circuit_breaker import db_circuit_breaker

logger = logging.getLogger(__name__)

settings = get_settings()

# Create database engine with optimized connection pooling for 100% success rate
engine = create_engine(
    settings.database_url,
    pool_size=8,  # Reduced pool size for better resource management
    max_overflow=12,  # Conservative overflow to prevent exhaustion
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=1200,  # Recycle connections every 20 minutes
    pool_timeout=20,  # Reduced timeout to fail fast
    connect_args={
        "connect_timeout": 10,  # Connection timeout
        "application_name": "kasparro_etl_api"
    },
    echo=settings.log_level == "DEBUG"
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Metadata for table operations
metadata = MetaData()


def get_db() -> Generator[Session, None, None]:
    """Get database session for dependency injection."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Get database session for context management with enhanced error handling."""
    db = SessionLocal()
    try:
        # Test connection before yielding
        db.execute(text("SELECT 1"))
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        try:
            db.close()
        except Exception as e:
            logger.warning(f"Error closing database session: {e}")


def init_db() -> None:
    """Initialize database tables."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


@db_circuit_breaker
def check_db_connection() -> bool:
    """Check if database connection is healthy with circuit breaker protection."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False