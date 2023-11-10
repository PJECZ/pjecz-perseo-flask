"""
Beneficiarios Quincenas, formularios
"""
from flask_wtf import FlaskForm
from wtforms import FloatField, StringField, SubmitField
from wtforms.validators import DataRequired, Regexp

from lib.safe_string import QUINCENA_REGEXP


class BeneficiarioQuincenaEditForm(FlaskForm):
    """Formulario BeneficiarioQuincena"""

    quincena = StringField("Quincena")  # Solo lectura
    beneficiario_rfc = StringField("Beneficiario RFC")  # Solo lectura
    beneficiario_nombre = StringField("Beneficiario nombre")  # Solo lectura
    importe = FloatField("Importe", validators=[DataRequired()])
    num_cheque = StringField("No. de cheque")  # Solo lectura
    guardar = SubmitField("Guardar")


class BeneficiarioQuincenaNewWithBeneficiarioForm(FlaskForm):
    """Formulario BeneficiarioQuincena"""

    quincena = StringField("Quincena (6 dígitos)", validators=[DataRequired(), Regexp(QUINCENA_REGEXP)])
    beneficiario_rfc = StringField("Beneficiario RFC")  # Solo lectura
    beneficiario_nombre = StringField("Beneficiario nombre")  # Solo lectura
    importe = FloatField("Importe", validators=[DataRequired()])
    num_cheque = StringField("No. de cheque")  # Solo lectura
    guardar = SubmitField("Guardar")
