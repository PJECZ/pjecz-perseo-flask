"""
Nominas, formularios
"""

from flask_wtf import FlaskForm
from wtforms import DateField, FloatField, RadioField, StringField, SubmitField
from wtforms.validators import DataRequired, Optional

TIPOS = [
    ("AGUINALDO", "AGUINALDO"),
    ("APOYO ANUAL", "APOYO ANUAL"),
    ("DESPENSA", "DESPENSA"),
    ("SALARIO", "SALARIO"),
    ("EXTRAORDINARIO", "EXTRAORDINARIO"),
]


class NominaEditForm(FlaskForm):
    """Formulario Nomina"""

    quincena_clave = StringField("Quincena")  # Solo lectura
    persona_rfc = StringField("RFC")  # Solo lectura
    persona_nombre_completo = StringField("Nombre completo")  # Solo lectura
    centro_trabajo_clave = StringField("Centro de Trabajo")  # Solo lectura
    plaza_clave = StringField("Plaza")  # Solo lectura
    tipo = RadioField("Tipo", validators=[DataRequired()], choices=TIPOS)
    percepcion = FloatField("Percepción", validators=[DataRequired()])
    deduccion = FloatField("Deducción", validators=[DataRequired()])
    importe = FloatField("Importe", validators=[DataRequired()])
    num_cheque = StringField("Número de cheque", validators=[Optional()])
    fecha_pago = DateField("Fecha de pago", validators=[Optional()])
    guardar = SubmitField("Guardar")
