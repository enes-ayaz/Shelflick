from functools import lru_cache
from typing import Literal, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """MediaPulse Application Settings using Pydantic v2 BaseSettings."""

    # Project Information
    PROJECT_NAME: str = "MediaPulse"
    PROJECT_VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["development", "staging", "production", "test"] = "development"
    DEBUG: bool = False

    # Database Configuration (PostgreSQL with asyncpg)
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://user:pass@localhost:5432/mediapulse",
        description="Async PostgreSQL connection string using asyncpg driver",
    )

    # External Media APIs Configuration
    TMDB_API_KEY: Optional[str] = Field(default=None, description="TMDB API v3 Key")
    TMDB_ACCESS_TOKEN: Optional[str] = Field(default=None, description="TMDB API v4 Read Access Token (Bearer)")
    TMDB_BASE_URL: str = Field(default="https://api.themoviedb.org/3", description="TMDB API v3 Base URL")
    TMDB_IMAGE_BASE_URL: str = Field(default="https://image.tmdb.org/t/p/w500", description="TMDB Poster CDN Base URL")
    IMAGE_PROXY_BASE_URL: str = Field(
        default="http://localhost:8000/api/v1/proxy/image",
        description="Local image proxy endpoint to bypass DNS sinkholing",
    )
    ANILIST_GRAPHQL_URL: str = Field(default="https://graphql.anilist.co", description="AniList GraphQL Endpoint")

    HTTP_TIMEOUT_SECONDS: float = Field(default=10.0, description="Default HTTP client timeout in seconds")
    HTTP_MAX_RETRIES: int = Field(default=3, description="Default retry count for external API requests")

    # LLM & AI Pipeline Configuration
    GEMINI_API_KEY: Optional[str] = Field(default=None, description="Google Gemini API Key")
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API Key (or Gemini OpenAI-compatible)")
    OPENAI_BASE_URL: Optional[str] = Field(default=None, description="Custom OpenAI Base URL (e.g. for Ollama or Gemini)")
    LLM_PROVIDER: Literal["gemini", "openai"] = Field(default="gemini", description="Default LLM provider")
    LLM_MODEL: str = Field(default="gemini-2.5-flash", description="Default LLM model name")
    LLM_TEMPERATURE: float = Field(default=0.2, description="Sampling temperature for deterministic parsing")

    # Security & Authentication Configuration
    JWT_SECRET_KEY: str = Field(
        default="shelflick-jwt-super-secret-key-change-in-production-2026",
        description="Secret key used for signing JWT access tokens",
    )
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT signing algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60 * 24 * 7, # 7 days
        description="Access token expiration duration in minutes",
    )
    GOOGLE_CLIENT_ID: Optional[str] = Field(
        default=None,
        description="Google OAuth2 Client ID for validating Google credentials",
    )

    # CORS & Web Origins Configuration
    FRONTEND_URL: Optional[str] = Field(
        default=None,
        description="Public URL of the deployed frontend (e.g. https://shelflick.vercel.app)",
    )
    ALLOWED_ORIGINS: list[str] = Field(
        default=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ],
        description="List of allowed CORS origins",
    )

    @property
    def cors_origins(self) -> list[str]:
        """Collects all allowed CORS origins from localhost defaults, ALLOWED_ORIGINS, and FRONTEND_URL."""
        origins = set(self.ALLOWED_ORIGINS)
        if self.FRONTEND_URL:
            for url in self.FRONTEND_URL.split(","):
                cleaned = url.strip().rstrip("/")
                if cleaned:
                    origins.add(cleaned)
        return list(origins)

    # Database Connection Pool Settings
    DB_POOL_SIZE: int = Field(default=10, description="Database connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=20, description="Maximum overflow connections")
    DB_POOL_TIMEOUT: int = Field(default=30, description="Timeout waiting for connection")
    DB_ECHO: bool = Field(default=False, description="Echo SQL queries in logs")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton factory."""
    return Settings()


settings = get_settings()
