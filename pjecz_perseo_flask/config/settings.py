"""
Settings
"""

import os
from functools import lru_cache

from google.cloud import secretmanager
from pydantic_settings import BaseSettings


def get_secret(secret_id: str, default: str = "") -> str:
    """Obtener el valor del secreto desde Google Cloud Secret Manager o desde las variables de entorno"""
    project_id = os.getenv("PROJECT_ID", "")
    service_prefix = os.getenv("SERVICE_PREFIX", "pjecz_perseo")

    # Si PROJECT_ID está vacío estamos en modo de desarrollo
    if project_id == "":
        value = os.getenv(secret_id.upper(), "")
        # Si el valor es texto vacio, entregar el valor por defecto
        if value == "":
            return default
        return value

    # Tratar de obtener el secreto
    try:
        # Create the secret manager client
        client = secretmanager.SecretManagerServiceClient()
        # Build the resource name of the secret version
        secret = f"{service_prefix}_{secret_id}".lower()
        name = client.secret_version_path(project_id, secret, "latest")
        # Access the secret version
        response = client.access_secret_version(name=name)
        # Return the decoded payload
        return response.payload.data.decode("UTF-8")
    except:
        pass

    # Si no funciona lo anterior, entregar el valor por defecto
    return default


class Settings(BaseSettings):
    """Settings"""

    # Variables de entorno
    CLOUD_STORAGE_DEPOSITO: str = get_secret("CLOUD_STORAGE_DEPOSITO", "")
    ENVIRONMENT: str = get_secret("ENVIRONMENT", "development")
    HOST: str = get_secret("HOST", "http://127.0.0.1:5000")
    PREFIX: str = get_secret("PREFIX", "")
    REDIS_HOST: str = get_secret("REDIS_HOST", "127.0.0.1")
    REDIS_PORT: str = get_secret("REDIS_PORT", "6379")
    SALT: str = get_secret("SALT", "")
    SECRET_KEY: str = get_secret("SECRET_KEY", "")
    SQLALCHEMY_DATABASE_URI: str = get_secret("SQLALCHEMY_DATABASE_URI", "")
    TASK_QUEUE_NAME: str = get_secret("TASK_QUEUE_NAME", "pjecz_perseo")
    TZ: str = get_secret("TZ", "America/Mexico_City")

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
