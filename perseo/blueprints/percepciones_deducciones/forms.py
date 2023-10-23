"""
Percepciones-Deducciones, formularios
"""
from flask_wtf import FlaskForm
from wtforms import FloatField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, Regexp

from lib.safe_string import QUINCENA_REGEXP
from perseo.blueprints.centros_trabajos.models import CentroTrabajo
from perseo.blueprints.conceptos.models import Concepto
from perseo.blueprints.plazas.models import Plaza


class PercepcionDeduccionNewWithPersonaForm(FlaskForm):
    """Formulario Percepcion Deduccion con la persona como parametro"""

    persona_rfc = StringField("RFC")  # Solo lectura
    persona_nombre_completo = StringField("Nombre completo")  # Solo lectura
    centro_trabajo = SelectField("Centro de Trabajo", coerce=int, validators=[DataRequired()])
    concepto = SelectField("Concepto", coerce=int, validators=[DataRequired()])
    plaza = StringField("Plaza", validators=[DataRequired(), Length(max=256)])
    quincena = StringField("Quincena", validators=[DataRequired(), Regexp(QUINCENA_REGEXP)])
    importe = FloatField("Importe", validators=[DataRequired()])
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones para centro_trabajo"""
        super().__init__(*args, **kwargs)
        self.centro_trabajo.choices = [
            (c.id, c.clave) for c in CentroTrabajo.query.filter_by(estatus="A").order_by(CentroTrabajo.clave).all()
        ]
        self.concepto.choices = [(c.id, c.clave) for c in Concepto.query.filter_by(estatus="A").order_by(Concepto.clave).all()]
        self.plaza.choices = [(p.id, p.clave) for p in Plaza.query.filter_by(estatus="A").order_by(Plaza.clave).all()]
