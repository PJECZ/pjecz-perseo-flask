"""
Usuarios, formularios
"""

from flask_wtf import FlaskForm
from wtforms import HiddenField, PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional, Regexp

from ...lib.safe_string import CONTRASENA_REGEXP

CONTRASENA_MENSAJE = "De 8 a 48 caracteres con al menos una mayúscula, una minúscula y un número. No acentos, ni eñe."


class AccesoForm(FlaskForm):
    """Formulario de acceso al sistema"""

    siguiente = HiddenField(default="")
    correo_electronico = StringField("Correo electrónico", validators=[DataRequired(), Length(8, 256)])
    contrasena = PasswordField(
        "Contraseña",
        validators=[DataRequired(), Length(8, 48), Regexp(CONTRASENA_REGEXP, 0, CONTRASENA_MENSAJE)],
    )
    ingresar = SubmitField("Ingresar")


class FirebaseForm(FlaskForm):
    """Formulario de acceso por Firebase"""

    siguiente = HiddenField(default="")
    identidad = StringField("Identidad", validators=[DataRequired()])
    token = StringField("Token", validators=[DataRequired()])
    ingresar = SubmitField("Ingresar")


class UsuarioForm(FlaskForm):
    """Formulario Usuario"""

    distrito = SelectField("Distrito", choices=None, validate_choice=False)  # Las opciones se agregan con JS
    autoridad = SelectField("Autoridad", choices=None, validate_choice=False)  # Las opciones se agregan con JS
    email = StringField("e-mail", validators=[DataRequired(), Email()])
    nombres = StringField("Nombres", validators=[DataRequired(), Length(max=256)])
    apellido_primero = StringField("Apellido primero", validators=[DataRequired(), Length(max=256)])
    apellido_segundo = StringField("Apellido segundo", validators=[Optional(), Length(max=256)])
    puesto = StringField("Puesto", validators=[Optional(), Length(max=256)])
    guardar = SubmitField("Guardar")
