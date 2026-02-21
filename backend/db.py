"""
Database layer for Banking Data Assistant
Handles SQLAlchemy engine creation, connection management, and initialization
"""

import logging
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

from sqlalchemy import (
    create_engine,
    event,
    text,
    MetaData,
    Table,
    Column,
    Integer,
    String,
    DECIMAL,
    DateTime,
    ForeignKey,
    Engine
)
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from backend.config import settings, get_database_path

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================
# ENGINE CONFIGURATION
# ============================================================

def create_db_engine() -> Engine:
    """
    Create SQLAlchemy engine with appropriate configuration
    Enforces read-only mode for security
    """
    connect_args = {}
    
    # SQLite-specific configuration
    if settings.DATABASE_URL.startswith("sqlite"):
        connect_args = {
            "check_same_thread": False,  # Allow multi-threading
        }
        
        # Use StaticPool for SQLite in-memory or small applications
        engine = create_engine(
            settings.DATABASE_URL,
            connect_args=connect_args,
            poolclass=StaticPool,
            echo=settings.DEBUG
        )
        
        # Enable foreign key constraints for SQLite
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    else:
        # PostgreSQL or other database configuration
        engine = create_engine(
            settings.DATABASE_URL,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_timeout=settings.DB_POOL_TIMEOUT,
            echo=settings.DEBUG
        )
    
    logger.info(f"Database engine created: {settings.DATABASE_URL}")
    return engine


# Global engine instance
engine = create_db_engine()

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ============================================================
# METADATA & TABLE DEFINITIONS
# ============================================================

metadata = MetaData()

# Define tables (for reflection and validation)
customers_table = Table(
    'customers',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String, nullable=False),
    Column('email', String, nullable=False, unique=True),
    Column('created_at', DateTime, server_default=text('CURRENT_TIMESTAMP'))
)

accounts_table = Table(
    'accounts',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('customer_id', Integer, ForeignKey('customers.id'), nullable=False),
    Column('account_number', String, nullable=False, unique=True),
    Column('balance', DECIMAL(15, 2), nullable=False, server_default=text('0.00')),
    Column('created_at', DateTime, server_default=text('CURRENT_TIMESTAMP'))
)

transactions_table = Table(
    'transactions',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('account_id', Integer, ForeignKey('accounts.id'), nullable=False),
    Column('type', String, nullable=False),
    Column('amount', DECIMAL(15, 2), nullable=False),
    Column('created_at', DateTime, server_default=text('CURRENT_TIMESTAMP'))
)


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_database() -> None:
    """
    Initialize database with schema from SQL file
    Only creates tables if they don't exist
    """
    try:
        schema_file = Path(__file__).parent.parent / "models" / "schema.sql"
        
        if not schema_file.exists():
            logger.error(f"Schema file not found: {schema_file}")
            raise FileNotFoundError(f"Schema file not found: {schema_file}")
        
        # Read schema SQL
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
        
        # Execute schema SQL
        with engine.begin() as conn:
            # Split by semicolon and execute each statement
            statements = [s.strip() for s in schema_sql.split(';') if s.strip()]
            for statement in statements:
                if statement:
                    conn.execute(text(statement))
        
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def get_table_names() -> list[str]:
    """
    Get list of all table names in the database
    Used for validation
    """
    try:
        with engine.connect() as conn:
            # Reflect current database state
            meta = MetaData()
            meta.reflect(bind=conn)
            return list(meta.tables.keys())
    except Exception as e:
        logger.error(f"Failed to get table names: {e}")
        return []


def verify_tables_exist() -> bool:
    """
    Verify that all required tables exist in database
    Returns True if all tables exist, False otherwise
    """
    try:
        existing_tables = get_table_names()
        required_tables = settings.ALLOWED_TABLES
        
        missing_tables = set(required_tables) - set(existing_tables)
        
        if missing_tables:
            logger.warning(f"Missing tables: {missing_tables}")
            return False
        
        logger.info(f"All required tables exist: {required_tables}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to verify tables: {e}")
        return False


# ============================================================
# SESSION MANAGEMENT
# ============================================================

@contextmanager
def get_db_session():
    """
    Context manager for database sessions
    Ensures proper session cleanup
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_db():
    """
    Dependency for FastAPI to get database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================
# HEALTH CHECK
# ============================================================

def check_database_health() -> dict:
    """
    Check database connection health
    Returns status dictionary
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        return {
            "status": "healthy",
            "database": settings.DATABASE_URL.split("://")[0],
            "tables": get_table_names()
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }
