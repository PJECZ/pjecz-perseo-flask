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

from dotenv import load_dotenv
from google.cloud import secretmanager
from pydantic_settings import BaseSettings

load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID", "")  # Por defecto esta vacio, esto significa estamos en modo local
PREFIX = os.getenv("PREFIX", "firebase")  # Es comun a todos los sistemas web


def get_secret(secret_id: str) -> str:
    """Get secret from google cloud secret manager"""

    # If not in google cloud, return environment variable
    if PROJECT_ID == "":
        return os.getenv(secret_id.upper(), "")

    # Create the secret manager client
    client = secretmanager.SecretManagerServiceClient()

    # Build the resource name of the secret version
    if PREFIX != "":
        secret = f"{PREFIX}_{secret_id}"
    else:
        secret = secret_id
    name = client.secret_version_path(PROJECT_ID, secret, "latest")

    # Access the secret version and return the decoded payload
    try:
        response = client.access_secret_version(name=name)
        return response.payload.data.decode("UTF-8")
    except Exception as error:
        return ""  # If fail return empty string


class FirebaseSettings(BaseSettings):
    """Settings"""

    APIKEY: str = get_secret("apikey")
    APPID: str = get_secret("appid")
    AUTHDOMAIN: str = get_secret("authdomain")
    DATABASEURL: str = get_secret("databaseurl")
    MEASUREMENTID: str = get_secret("measurementid")
    MESSAGINGSENDERID: str = get_secret("messagingsenderid")
    PROJECTID: str = get_secret("projectid")
    STORAGEBUCKET: str = get_secret("storagebucket")

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
