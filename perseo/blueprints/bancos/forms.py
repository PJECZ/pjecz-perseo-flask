"""
Bancos, formularios
"""

from flask_wtf import FlaskForm
from wtforms import IntegerField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, Regexp

CLAVE_REGEXP = r"^\d{1,2}$"
CLAVE_DISPERSION_PENSIONADOS_REGEXP = r"^\d{3}$"


class BancoForm(FlaskForm):
    """Formulario Banco"""

    nombre = StringField("Nombre", validators=[DataRequired(), Length(max=256)])
    clave = StringField("Clave (1 o 2 dígitos)", validators=[DataRequired(), Regexp(CLAVE_REGEXP)])
    clave_dispersion_pensionados = StringField(
        "Clave SAT/Dispersiones Pensionados (3 dígitos)",
        validators=[
            DataRequired(),
            Regexp(CLAVE_DISPERSION_PENSIONADOS_REGEXP),
        ],
    )
    consecutivo = IntegerField("Consecutivo (CON CUIDADO)", validators=[DataRequired()])
    consecutivo_generado = IntegerField("Consecutivo temporal", validators=[DataRequired()])
    guardar = SubmitField("Guardar")
