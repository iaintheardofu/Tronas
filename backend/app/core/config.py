from pydantic_settings import BaseSettings
from pydantic import ConfigDict, field_validator
from typing import Optional
from functools import lru_cache
import secrets


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Tronas PIA Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    API_V1_PREFIX: str = "/api/v1"

    # Database - MUST be set via environment variable in production
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/pia_db"
    DATABASE_ECHO: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security - SECRET_KEY MUST be set via environment variable
    # Generate with: python -c "import secrets; print(secrets.token_urlsafe(64))"
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    @field_validator("SECRET_KEY", mode="before")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """
        Validate SECRET_KEY is set and meets minimum security requirements.
        """
        if not v:
            # Generate a random key if not provided
            return secrets.token_urlsafe(64)
        if len(v) < 32:
            raise ValueError(
                "SECRET_KEY must be at least 32 characters long for security"
            )
        return v

    # CORS - Allow Railway and localhost origins
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://tronas.ai",
        "https://www.tronas.ai",
        "https://*.up.railway.app",
        "https://*.railway.app",
    ]

    # Microsoft Azure AD / Entra ID
    AZURE_TENANT_ID: Optional[str] = None
    AZURE_CLIENT_ID: Optional[str] = None
    AZURE_CLIENT_SECRET: Optional[str] = None
    AZURE_AUTHORITY: str = "https://login.microsoftonline.com"

    # Microsoft Graph API scopes
    MS_GRAPH_SCOPES: list[str] = [
        "https://graph.microsoft.com/.default"
    ]

    # Azure Storage for document processing
    AZURE_STORAGE_CONNECTION_STRING: Optional[str] = None
    AZURE_STORAGE_CONTAINER: str = "pia-documents"

    # OpenAI / Azure OpenAI for document classification
    OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_ENDPOINT: Optional[str] = None
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_DEPLOYMENT: str = "gpt-4"

    # Classification model settings
    CLASSIFICATION_MODEL: str = "gpt-4"
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # File uploads
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE_MB: int = 100
    ALLOWED_FILE_TYPES: list[str] = [
        "application/pdf",
        "image/jpeg",
        "image/png",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/plain",
        "message/rfc822",  # .eml files
        "application/vnd.ms-outlook",  # .msg files
    ]

    # Email notifications
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: str = "pia-automation@city.local"

    # Texas PIA-specific settings (Texas Government Code Chapter 552)
    PIA_RESPONSE_DEADLINE_DAYS: int = 10  # 10 business days per Texas law
    PIA_AG_RULING_DEADLINE_DAYS: int = 45  # 45 days for AG ruling
    PIA_EXTENSION_MAX_DAYS: int = 10  # Additional 10 days with notice

    # Document processing thresholds
    LARGE_REQUEST_THRESHOLD_PAGES: int = 5000
    BATCH_SIZE: int = 100

    # Classification categories (Texas PIA exemptions)
    CLASSIFICATION_CATEGORIES: list[str] = [
        "responsive",
        "non_responsive",
        "attorney_client_privilege",
        "legislative_privilege",
        "law_enforcement",
        "medical_information",
        "personnel_records",
        "trade_secrets",
        "deliberative_process",
        "pending_litigation",
        "personal_information",
        "needs_review"
    ]

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
