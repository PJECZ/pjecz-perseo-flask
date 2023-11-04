"""
Personas, formularios
"""
from flask_wtf import FlaskForm
from wtforms import RadioField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, Regexp

from lib.safe_string import CURP_REGEXP, RFC_REGEXP

MODELOS = [
    (1, "1) CONFIANZA"),
    (2, "2) SINDICALIZADO"),
    (3, "3) PENSIONADO"),
]


class PersonaForm(FlaskForm):
    """Formulario Persona"""

    rfc = StringField("RFC", validators=[DataRequired(), Regexp(RFC_REGEXP)])
    nombres = StringField("Nombres", validators=[DataRequired(), Length(max=256)])
    apellido_primero = StringField("Apellido primero", validators=[DataRequired(), Length(max=256)])
    apellido_segundo = StringField("Apellido segundo", validators=[Optional(), Length(max=256)])
    curp = StringField("CURP", validators=[Optional(), Regexp(CURP_REGEXP)])
    modelo = RadioField("Modelo", validators=[DataRequired()], choices=MODELOS, coerce=int)
    guardar = SubmitField("Guardar")
