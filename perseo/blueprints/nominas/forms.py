"""
Nominas, formularios
"""
from flask_wtf import FlaskForm
from wtforms import FloatField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired

from perseo.blueprints.nominas.models import Nomina


class NominaEditForm(FlaskForm):
    """Formulario Nomina"""

    quincena = StringField("Quincena (6 dígitos)")  # Solo lectura
    persona_rfc = StringField("RFC")  # Solo lectura
    persona_nombre_completo = StringField("Nombre completo")  # Solo lectura
    centro_trabajo_clave = StringField("Centro de Trabajo")  # Solo lectura
    plaza_clave = SelectField("Plaza")  # Solo lectura
    percepcion = FloatField("Percepción", validators=[DataRequired()])
    deduccion = FloatField("Deducción", validators=[DataRequired()])
    importe = FloatField("Importe", validators=[DataRequired()])
    tipo = SelectField("Tipo", choices=Nomina.TIPOS, validators=[DataRequired()])
    guardar = SubmitField("Guardar")
