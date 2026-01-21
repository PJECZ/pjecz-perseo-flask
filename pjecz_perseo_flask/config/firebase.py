"""
Firebase
"""

import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class FirebaseSettings(BaseSettings):
    """FirebaseSettings"""

    # Variables de entorno
    APIKEY: str = os.getenv("FIREBASE_APIKEY", "")
    APPID: str = os.getenv("FIREBASE_APPID", "")
    AUTHDOMAIN: str = os.getenv("FIREBASE_AUTHDOMAIN", "")
    DATABASEURL: str = os.getenv("FIREBASE_DATABASEURL", "")
    MEASUREMENTID: str = os.getenv("FIREBASE_MEASUREMENTID", "")
    MESSAGINGSENDERID: str = os.getenv("FIREBASE_MESSAGINGSENDERID", "")
    PROJECTID: str = os.getenv("FIREBASE_PROJECTID", "")
    STORAGEBUCKET: str = os.getenv("FIREBASE_STORAGEBUCKET", "")

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
