"""
Conceptos, formularios
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length, Regexp

from lib.safe_string import CONCEPTO_REGEXP


class ConceptoForm(FlaskForm):
    """Formulario Concepto"""

    clave = StringField(
        "Clave (P o D seguido de 2 a 4 números y/o letras)", validators=[DataRequired(), Regexp(CONCEPTO_REGEXP)]
    )
    descripcion = StringField("Descripción", validators=[DataRequired(), Length(max=256)])
    guardar = SubmitField("Guardar")
