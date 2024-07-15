"""
Plazas, formularios
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length, Regexp

from lib.safe_string import PLAZA_REGEXP


class PlazaForm(FlaskForm):
    """Formulario Plaza"""

    clave = StringField("Clave (hasta 24 caracteres)", validators=[DataRequired(), Regexp(PLAZA_REGEXP)])
    descripcion = StringField("Descripción", validators=[DataRequired(), Length(max=256)])
    guardar = SubmitField("Guardar")
