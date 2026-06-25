from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "ai-video-service"
    kafka_bootstrap_servers: str = "localhost:9092"
    redis_url: str = "redis://localhost:6379/0"
    postgres_url: str = "postgresql://aivideo:aivideo@localhost:5432/aivideo"
    cassandra_hosts: str = "localhost"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    qdrant_url: str = "http://localhost:6333"
    jwt_secret: str = "dev-secret-change-in-prod"


@lru_cache
def get_settings() -> Settings:
    return Settings()
