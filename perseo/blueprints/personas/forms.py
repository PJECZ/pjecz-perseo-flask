"""
Personas, formularios
"""
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, Regexp

from lib.safe_string import CURP_REGEXP, RFC_REGEXP


class PersonaForm(FlaskForm):
    """Formulario Persona"""

    rfc = StringField("RFC", validators=[DataRequired(), Regexp(RFC_REGEXP)])
    nombres = StringField("Nombres", validators=[DataRequired(), Length(max=256)])
    apellido_primero = StringField("Apellido primero", validators=[DataRequired(), Length(max=256)])
    apellido_segundo = StringField("Apellido segundo", validators=[Optional(), Length(max=256)])
    curp = StringField("CURP", validators=[DataRequired(), Regexp(CURP_REGEXP)])
    guardar = SubmitField("Guardar")
