"""
Conceptos, formularios
"""
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length


class ConceptoForm(FlaskForm):
    """Formulario Concepto"""

    clave = StringField("Clave", validators=[DataRequired(), Length(max=16)])
    descripcion = StringField("Descripción", validators=[DataRequired(), Length(max=256)])
    guardar = SubmitField("Guardar")
