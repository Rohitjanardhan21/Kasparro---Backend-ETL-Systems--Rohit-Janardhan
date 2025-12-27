"""Configuration management for the Kasparro ETL system."""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = Field(
        default="postgresql://postgres:password@localhost:5432/kasparro_etl",
        env="DATABASE_URL"
    )
    
    # API Keys (Optional - APIs work without keys but with rate limits)
    coinpaprika_api_key: str = Field(default="", env="COINPAPRIKA_API_KEY")
    coingecko_api_key: str = Field(default="", env="COINGECKO_API_KEY")
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    
    # ETL Configuration
    etl_batch_size: int = Field(default=1000, env="ETL_BATCH_SIZE")
    etl_rate_limit_requests: int = Field(default=100, env="ETL_RATE_LIMIT_REQUESTS")
    etl_rate_limit_period: int = Field(default=60, env="ETL_RATE_LIMIT_PERIOD")
    etl_retry_attempts: int = Field(default=3, env="ETL_RETRY_ATTEMPTS")
    etl_retry_delay: int = Field(default=5, env="ETL_RETRY_DELAY")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    
    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings