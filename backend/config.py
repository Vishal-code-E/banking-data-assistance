"""
Configuration module for Banking Data Assistant
Handles environment variables and application settings
"""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    Follows 12-factor app principles
    """
    
    # Application
    APP_NAME: str = "Banking Data Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "sqlite:///banking_10k.db"
    )
    
    # Database connection pool settings
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    
    # Query execution settings
    QUERY_TIMEOUT: int = int(os.getenv("QUERY_TIMEOUT", "30"))
    MAX_RESULT_ROWS: int = int(os.getenv("MAX_RESULT_ROWS", "1000"))
    
    # Security
    ALLOWED_TABLES: list[str] = [
        "customers",
        "accounts", 
        "transactions"
    ]
    
    # CORS (if frontend is on different origin)
    CORS_ORIGINS: str = os.getenv(
        "CORS_ORIGINS",
        "https://banking-data-frontend-assistance-1.onrender.com,"
        "http://localhost:3000,http://localhost:8080,http://localhost:8001,"
        "http://localhost:5500,http://127.0.0.1:5500,http://localhost:5173,"
        "http://127.0.0.1:8001"
    )
    
    # Port — Render injects PORT env var
    PORT: int = int(os.getenv("PORT", "8000"))
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra fields from .env


# Global settings instance
settings = Settings()


def get_database_path() -> Optional[Path]:
    """
    Get the filesystem path to the SQLite database
    Returns None for non-SQLite databases
    """
    if settings.DATABASE_URL.startswith("sqlite:///"):
        db_file = settings.DATABASE_URL.replace("sqlite:///", "")
        return Path(db_file)
    return None
