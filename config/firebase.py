"""
Firebase configuration

Configure los siguientes secretos en google cloud secret manager:

- firebase_apikey
- firebase_appid
- firebase_authdomain
- firebase_databaseurl
- firebase_measurementid
- firebase_messagingsenderid
- firebase_projectid
- firebase_storagebucket
"""
import os
from functools import lru_cache

from google.cloud import secretmanager
from pydantic_settings import BaseSettings

PROJECT_ID = os.getenv("PROJECT_ID", "")  # Por defecto esta vacio, esto significa estamos en modo local
PREFIX = os.getenv("PREFIX", "firebase_")


def get_secret(secret_id: str) -> str:
    """Get secret from google cloud secret manager"""

    # If not in google cloud, return environment variable
    if PROJECT_ID == "":
        return os.getenv(secret_id.upper(), "")

    # Create the secret manager client
    client = secretmanager.SecretManagerServiceClient()

    # Build the resource name of the secret version
    secret = f"{PREFIX}_{secret_id}"
    name = client.secret_version_path(PROJECT_ID, secret, "latest")

    # Access the secret version
    response = client.access_secret_version(name=name)

    # Return the decoded payload
    return response.payload.data.decode("UTF-8")


class FirebaseSettings(BaseSettings):
    """Settings"""

    FIREBASE_APIKEY: str = get_secret("firebase_apikey")
    FIREBASE_APPID: str = get_secret("firebase_appid")
    FIREBASE_AUTHDOMAIN: str = get_secret("firebase_authdomain")
    FIREBASE_DATABASEURL: str = get_secret("firebase_databaseurl")
    FIREBASE_MEASUREMENTID: str = get_secret("firebase_measurementid")
    FIREBASE_MESSAGINGSENDERID: str = get_secret("firebase_messagingsenderid")
    FIREBASE_PROJECTID: str = get_secret("firebase_projectid")
    FIREBASE_STORAGEBUCKET: str = get_secret("firebase_storagebucket")

    class Config:
        """Load configuration"""

        @classmethod
        def customise_sources(cls, init_settings, env_settings, file_secret_settings):
            """Customise sources, first environment variables, then .env file, then google cloud secret manager"""
            return env_settings, file_secret_settings, init_settings


@lru_cache()
def get_firebase_settings() -> FirebaseSettings:
    """Get Settings"""
    return FirebaseSettings()
