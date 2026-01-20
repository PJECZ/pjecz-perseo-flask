"""
Settings
"""

import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Settings"""

    # Variables de entorno
    CLOUD_STORAGE_DEPOSITO: str = os.getenv("CLOUD_STORAGE_DEPOSITO", "")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    HOST: str = os.getenv("HOST", "http://127.0.0.1:5000")
    PREFIX: str = os.getenv("PREFIX", "")
    REDIS_HOST: str = os.getenv("REDIS_HOST", "127.0.0.1")
    REDIS_PORT: str = os.getenv("REDIS_PORT", "6379")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    SQLALCHEMY_DATABASE_URI: str = os.getenv("SQLALCHEMY_DATABASE_URI", "")
    TASK_QUEUE_NAME: str = os.getenv("TASK_QUEUE_NAME", "pjecz_perseo")
    TZ: str = os.getenv("TZ", "America/Mexico_City")

    # Incrementar el tamaño de lo que se sube en los formularios
    MAX_CONTENT_LENGTH: int | None = None
    MAX_FORM_MEMORY_SIZE: int = 1024 * (2**10) ** 2  # 1 GB

    class Config:
        """Load configuration"""

        @classmethod
        def customise_sources(cls, init_settings, env_settings, file_secret_settings):
            """Change the order of precedence of settings sources"""
            return env_settings, file_secret_settings, init_settings


@lru_cache()
def get_settings() -> Settings:
    """Get Settings"""
    return Settings()
