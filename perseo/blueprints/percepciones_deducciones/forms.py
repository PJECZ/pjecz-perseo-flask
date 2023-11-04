"""
Percepciones Deducciones, formularios
"""
from flask_wtf import FlaskForm
from wtforms import FloatField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired

from perseo.blueprints.conceptos.models import Concepto


class PercepcionDeduccionEditForm(FlaskForm):
    """Formulario Percepcion Deduccion"""

    quincena = StringField("Quincena")  # Solo lectura
    persona_rfc = StringField("RFC")  # Solo lectura
    persona_nombre_completo = StringField("Nombre completo")  # Solo lectura
    centro_trabajo_clave = StringField("Centro de Trabajo")  # Solo lectura
    plaza_clave = SelectField("Plaza")  # Solo lectura
    concepto = SelectField("Concepto", coerce=int, validators=[DataRequired()])
    importe = FloatField("Importe", validators=[DataRequired()])
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones"""
        super().__init__(*args, **kwargs)
        self.concepto.choices = [
            (c.id, f"{c.clave} - {c.descripcion}") for c in Concepto.query.filter_by(estatus="A").order_by(Concepto.clave).all()
        ]
