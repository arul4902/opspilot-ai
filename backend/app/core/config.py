import os
from typing import List, Union, Optional
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "OpsPilot AI"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Security & JWT
    SECRET_KEY: str = "opspilot-super-secure-dev-secret-key-change-in-production-12345678"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours

    # Database
    DATABASE_URL: str = "sqlite:///./opspilot.db"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_database_url(cls, v: Optional[str]) -> str:
        url = v or "sqlite:///./opspilot.db"
        if (os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")) and url.startswith("sqlite:///."):
            return "sqlite:////tmp/opspilot.db"
        return url

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:4200",
        "http://127.0.0.1:4200",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://opspilot-ai.vercel.app",
        "*"
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # LLM Settings
    LLM_PROVIDER: str = "mock"  # "mock", "gemini", "openai"
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL_NAME: str = "gemini-1.5-flash"

    # RAG Settings
    CHROMA_PERSIST_DIRECTORY: str = "./chroma_storage"

    @field_validator("CHROMA_PERSIST_DIRECTORY", mode="before")
    @classmethod
    def assemble_chroma_dir(cls, v: Optional[str]) -> str:
        d = v or "./chroma_storage"
        if (os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")) and d.startswith("."):
            return "/tmp/chroma_storage"
        return d

    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # Operations & Agent Guardrails
    MAX_AGENT_STEPS: int = 8
    AGENT_TIMEOUT_SECONDS: int = 30
    REQUIRE_APPROVAL_REFUND_THRESHOLD: float = 0.0  # Consequential: all refunds require approval

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

