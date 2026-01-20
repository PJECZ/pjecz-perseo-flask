"""
Beneficiarios Cuentas, formularios
"""

from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length

from ..bancos.models import Banco


class BeneficiarioCuentaEditForm(FlaskForm):
    """Formulario BeneficiarioCuenta"""

    banco_nombre = StringField("Banco")  # Solo lectura
    beneficiario_rfc = StringField("Beneficiario RFC")  # Solo lectura
    beneficiario_nombre = StringField("Beneficiario nombre")  # Solo lectura
    num_cuenta = StringField("No. de cuenta", validators=[DataRequired(), Length(max=256)])
    guardar = SubmitField("Guardar")


class BeneficiarioCuentaNewWithBeneficiarioForm(FlaskForm):
    """Formulario BeneficiarioCuenta"""

    banco = SelectField("Banco", coerce=int, validators=[DataRequired()])
    beneficiario_rfc = StringField("Beneficiario RFC")  # Solo lectura
    beneficiario_nombre = StringField("Beneficiario nombre")  # Solo lectura
    num_cuenta = StringField("No. de cuenta", validators=[DataRequired(), Length(max=256)])
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones para banco"""
        super().__init__(*args, **kwargs)
        self.banco.choices = [(b.id, b.nombre) for b in Banco.query.filter_by(estatus="A").order_by(Banco.nombre).all()]
