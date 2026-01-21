"""
Flask Extensions
"""

from flask_login import LoginManager
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from passlib.context import CryptContext

database = SQLAlchemy()
csrf = CSRFProtect()
login_manager = LoginManager()
moment = Moment()
pwd_context = CryptContext(schemes=["pbkdf2_sha256", "des_crypt"], deprecated="auto")


def authentication(user_model):
    """Flask-Login authentication"""

    @login_manager.user_loader
    def load_user(uid):
        return user_model.query.get(uid)
