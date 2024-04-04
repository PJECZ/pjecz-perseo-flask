"""
Personas, formularios
"""

from flask_wtf import FlaskForm
from wtforms import DateField, IntegerField, RadioField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, Regexp

from lib.safe_string import CURP_REGEXP, RFC_REGEXP

MODELOS = [
    (1, "1) CONFIANZA"),
    (2, "2) SINDICALIZADO"),
    (3, "3) PENSIONADO"),
    (4, "4) BENEFICIARIO PENSION ALIMENTICIA"),
    (5, "5) ASIMILADO A SALARIOS"),
    (6, "6) EXTRAORDINARIO"),
]


class PersonaForm(FlaskForm):
    """Formulario Persona"""

    rfc = StringField("RFC", validators=[DataRequired(), Regexp(RFC_REGEXP)])
    nombres = StringField("Nombres", validators=[DataRequired(), Length(max=256)])
    apellido_primero = StringField("Apellido primero", validators=[DataRequired(), Length(max=256)])
    apellido_segundo = StringField("Apellido segundo", validators=[Optional(), Length(max=256)])
    curp = StringField("CURP", validators=[Optional(), Regexp(CURP_REGEXP)])
    num_empleado = IntegerField("No. de empleado", validators=[Optional()])
    modelo = RadioField("Modelo", validators=[DataRequired()], choices=MODELOS, coerce=int)
    ingreso_gobierno_fecha = DateField("F. ingreso al gobierno", validators=[Optional()])
    ingreso_pj_fecha = DateField("F. ingreso al PJ", validators=[Optional()])
    nacimiento_fecha = DateField("F. nacimiento", validators=[Optional()])
    codigo_postal_fiscal = IntegerField("Código Postal fiscal", validators=[DataRequired(), NumberRange(0, 99999)], default=0)
    seguridad_social = StringField("NSS", validators=[Optional(), Length(max=24)])
    guardar = SubmitField("Guardar")
