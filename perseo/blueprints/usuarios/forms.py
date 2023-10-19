"""
Usuarios, formularios
"""
from flask_wtf import FlaskForm
from wtforms import HiddenField, PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional, Regexp

from lib.safe_string import CONTRASENA_REGEXP
from perseo.blueprints.autoridades.models import Autoridad

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


class UsuarioForm(FlaskForm):
    """Formulario Usuario"""

    autoridad = SelectField("Autoridad", coerce=int, validators=[DataRequired()])
    email = StringField("e-mail", validators=[DataRequired(), Email()])
    nombres = StringField("Nombres", validators=[DataRequired(), Length(max=256)])
    apellido_primero = StringField("Apellido primero", validators=[DataRequired(), Length(max=256)])
    apellido_segundo = StringField("Apellido segundo", validators=[Optional(), Length(max=256)])
    curp = StringField("CURP", validators=[Optional(), Length(max=256)])
    puesto = StringField("Puesto", validators=[Optional(), Length(max=256)])
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones para autoridad"""
        super().__init__(*args, **kwargs)
        self.autoridad.choices = [
            (d.id, d.clave + " - " + d.descripcion_corta)
            for d in Autoridad.query.filter_by(estatus="A").order_by(Autoridad.clave).all()
        ]
