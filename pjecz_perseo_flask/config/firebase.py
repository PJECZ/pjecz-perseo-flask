"""
Firebase
"""

import os
from functools import lru_cache

from google.cloud import secretmanager
from pydantic_settings import BaseSettings


def get_secret(secret_id: str, default: str = "") -> str:
    """Obtener el valor del secreto desde Google Cloud Secret Manager o desde las variables de entorno"""
    project_id = os.getenv("PROJECT_ID", "")

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
        secret = secret_id.lower()
        name = client.secret_version_path(project_id, secret, "latest")
        # Access the secret version
        response = client.access_secret_version(name=name)
        # Return the decoded payload
        return response.payload.data.decode("UTF-8")
    except:
        pass

    # Si no funciona lo anterior, entregar el valor por defecto
    return default


class FirebaseSettings(BaseSettings):
    """FirebaseSettings"""

    # Variables de entorno
    APIKEY: str = get_secret("FIREBASE_APIKEY", "")
    APPID: str = get_secret("FIREBASE_APPID", "")
    AUTHDOMAIN: str = get_secret("FIREBASE_AUTHDOMAIN", "")
    DATABASEURL: str = get_secret("FIREBASE_DATABASEURL", "")
    MEASUREMENTID: str = get_secret("FIREBASE_MEASUREMENTID", "")
    MESSAGINGSENDERID: str = get_secret("FIREBASE_MESSAGINGSENDERID", "")
    PROJECTID: str = get_secret("FIREBASE_PROJECTID", "")
    STORAGEBUCKET: str = get_secret("FIREBASE_STORAGEBUCKET", "")

    class Config:
        """Load configuration"""

        @classmethod
        def customise_sources(cls, init_settings, env_settings, file_secret_settings):
            """Change the order of precedence of settings sources"""
            return env_settings, file_secret_settings, init_settings


@lru_cache()
def get_firebase_settings() -> FirebaseSettings:
    """Get Firebase Settings"""
    return FirebaseSettings()
