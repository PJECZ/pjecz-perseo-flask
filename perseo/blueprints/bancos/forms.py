"""
Bancos, formularios
"""
from flask_wtf import FlaskForm
from wtforms import IntegerField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, Regexp

CLAVE_REGEXP = r"^\d{1,2}$"
CLAVE_DISPERSION_PENSIONADOS_REGEXP = r"^\d{1,3}$"


class BancoForm(FlaskForm):
    """Formulario Banco"""

    nombre = StringField("Nombre", validators=[DataRequired(), Length(max=256)])
    clave = StringField("Clave (1 o 2 dígitos)", validators=[DataRequired(), Regexp(CLAVE_REGEXP)])
    clave_dispersion_pensionados = StringField(
        "Clave para dispersiones pensionados (de 1 a 3 dígitos)",
        validators=[
            DataRequired(),
            Regexp(CLAVE_DISPERSION_PENSIONADOS_REGEXP),
        ],
    )
    consecutivo = IntegerField("Consecutivo (CON CUIDADO)", validators=[Optional()])
    consecutivo_generado = IntegerField("Consecutivo temporal", validators=[Optional()])
    guardar = SubmitField("Guardar")
