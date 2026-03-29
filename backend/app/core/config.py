from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "NexusReport"
    version: str = "0.1.0"
    environment: str = "development"
    secret_key: str = "changeme"
    api_prefix: str = "/api/v1"

    # Database
    database_url: str = "postgresql+asyncpg://nexus:nexussecret@localhost/nexusreport"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Storage (MinIO / S3)
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "nexus"
    minio_secret_key: str = "nexussecret"
    minio_bucket: str = "nexusreport-artifacts"
    minio_secure: bool = False

    # AI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # Notifications
    slack_webhook_url: str = ""
    teams_webhook_url: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
