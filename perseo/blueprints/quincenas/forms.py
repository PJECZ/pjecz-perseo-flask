"""
Quincenas, formularios
"""
from flask_wtf import FlaskForm
from wtforms import RadioField, StringField, SubmitField
from wtforms.validators import DataRequired, Regexp

from lib.safe_string import QUINCENA_REGEXP
from perseo.blueprints.quincenas.models import Quincena


class QuincenaForm(FlaskForm):
    """Formulario Quincena"""

    quincena = StringField("Quincena (6 dígitos)", validators=[DataRequired(), Regexp(QUINCENA_REGEXP)])
    estado = RadioField("Estado", validators=[DataRequired()], choices=Quincena.ESTADOS.items(), coerce=str)
    guardar = SubmitField("Guardar")
