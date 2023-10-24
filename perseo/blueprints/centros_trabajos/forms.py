"""
Centros de Trabajos, formularios
"""
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length


class CentroTrabajoForm(FlaskForm):
    """Formulario CentroTrabajo"""

    clave = StringField("Clave (hasta 10 carecteres)", validators=[DataRequired(), Length(max=10)])
    descripcion = StringField("Descripción", validators=[DataRequired(), Length(max=256)])
    guardar = SubmitField("Guardar")
