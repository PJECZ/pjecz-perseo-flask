"""
Beneficiarios, formularios
"""
from flask_wtf import FlaskForm
from wtforms import DateField, RadioField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, Regexp

from lib.safe_string import CURP_REGEXP, RFC_REGEXP

MODELOS = [
    (4, "4) BENEFICIARIO"),
]


class BeneficiarioForm(FlaskForm):
    """Formulario Beneficiario"""

    rfc = StringField("RFC", validators=[DataRequired(), Regexp(RFC_REGEXP)])
    nombres = StringField("Nombres", validators=[DataRequired(), Length(max=256)])
    apellido_primero = StringField("Apellido primero", validators=[DataRequired(), Length(max=256)])
    apellido_segundo = StringField("Apellido segundo", validators=[Optional(), Length(max=256)])
    curp = StringField("CURP", validators=[Optional(), Regexp(CURP_REGEXP)])
    nacimiento_fecha = DateField("Fecha de nacimiento", validators=[Optional()])
    modelo = RadioField("Modelo", validators=[DataRequired()], choices=MODELOS, coerce=int)
    guardar = SubmitField("Guardar")
