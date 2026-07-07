"""
Centralized configuration management using Pydantic settings.

This file reads configuration from environment variables and .env file.
It validates all values at startup so we catch misconfiguration early.

Why pydantic-settings?
- Type validation (PORT must be int, DEBUG must be bool)
- Automatic .env file loading
- IDE autocomplete for settings
- Secret masking in logs
"""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Each attribute maps to an environment variable (case-insensitive).
    Example: APP_NAME maps to APP_NAME or app_name in .env
    """
    
    # Application
    APP_NAME: str = "AI Support Copilot"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = Field(..., min_length=32)
    
    # Database
    DATABASE_URL: str = Field(
        default="postgresql://postgres:password@localhost:5432/support_copilot"
    )
    
    # JWT Authentication
    JWT_SECRET_KEY: str = Field(..., min_length=32)
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # AI - Gemini
    GEMINI_API_KEY: str = ""
    # AI - Groq
    GROQ_API_KEY: str = ""
    # AI - Embeddings
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    CHROMA_PERSIST_DIR: str = "./chroma_data"
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Tells pydantic-settings to read from .env file
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


# Create a single instance to be imported everywhere
# This is a Singleton pattern - only one Settings object exists
settings = Settings()