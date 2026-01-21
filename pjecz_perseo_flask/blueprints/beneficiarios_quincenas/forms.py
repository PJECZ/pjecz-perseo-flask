"""
Beneficiarios Quincenas, formularios
"""

from flask_wtf import FlaskForm
from wtforms import FloatField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired

from ..quincenas.models import Quincena


class BeneficiarioQuincenaEditForm(FlaskForm):
    """Formulario BeneficiarioQuincena"""

    quincena_clave = StringField("Quincena")  # Solo lectura
    beneficiario_rfc = StringField("Beneficiario RFC")  # Solo lectura
    beneficiario_nombre = StringField("Beneficiario nombre")  # Solo lectura
    importe = FloatField("Importe", validators=[DataRequired()])
    num_cheque = StringField("No. de cheque")  # Solo lectura
    guardar = SubmitField("Guardar")


class BeneficiarioQuincenaNewWithBeneficiarioForm(FlaskForm):
    """Formulario BeneficiarioQuincena"""

    quincena = SelectField("Quincena", coerce=int, validators=[DataRequired()])
    beneficiario_rfc = StringField("Beneficiario RFC")  # Solo lectura
    beneficiario_nombre = StringField("Beneficiario nombre")  # Solo lectura
    importe = FloatField("Importe", validators=[DataRequired()])
    num_cheque = StringField("No. de cheque")
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones para quincena"""
        super().__init__(*args, **kwargs)
        self.quincena.choices = [
            (q.id, q.clave) for q in Quincena.query.filter_by(estado="ABIERTA").filter_by(estatus="A").all()
        ]
