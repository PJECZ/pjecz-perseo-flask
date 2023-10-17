"""
Usuarios, formularios
"""
from flask_wtf import FlaskForm
from wtforms import HiddenField, PasswordField, StringField, SubmitField
from wtforms.validators import Email, Length, Optional, Regexp

from lib.safe_string import CONTRASENA_REGEXP

CONTRASENA_MENSAJE = "De 8 a 48 caracteres con al menos una mayúscula, una minúscula y un número. No acentos, ni eñe."


class AccesoForm(FlaskForm):
    """Formulario de acceso al sistema"""

    siguiente = HiddenField()
    identidad = StringField("Correo electrónico o usuario", validators=[Optional(), Length(8, 256)])
    contrasena = PasswordField(
        "Contraseña",
        validators=[Optional(), Length(8, 48), Regexp(CONTRASENA_REGEXP, 0, CONTRASENA_MENSAJE)],
    )
    email = StringField("Correo electrónico", validators=[Optional(), Email()])
    token = StringField("Token", validators=[Optional()])
    guardar = SubmitField("Guardar")
