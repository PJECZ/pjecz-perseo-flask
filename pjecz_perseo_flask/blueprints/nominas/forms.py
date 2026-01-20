"""
Nominas, formularios
"""

from flask_wtf import FlaskForm
from wtforms import DateField, FloatField, RadioField, StringField, SubmitField
from wtforms.validators import DataRequired, Optional, Regexp

from ...lib.safe_string import QUINCENA_REGEXP

TIPOS = [
    ("AGUINALDO", "AGUINALDO"),
    ("APOYO ANUAL", "APOYO ANUAL"),
    ("APOYO DIA DE LA MADRE", "APOYO DIA DE LA MADRE"),
    ("ASIMILADOS", "ASIMILADOS"),
    ("DESPENSA", "DESPENSA"),
    ("SALARIO", "SALARIO"),
    ("EXTRAORDINARIO", "EXTRAORDINARIO"),
    ("PENSION ALIMENTICIA", "PENSION ALIMENTICIA"),
    ("PRIMA VACACIONAL", "PRIMA VACACIONAL"),
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


class NominaExtraordinarioNewForm(FlaskForm):
    """Formulario Nueva Nomina Extraordinario"""

    persona_texto = StringField("Persona")  # Solo lectura
    centro_trabajo_texto = StringField("Centro de Trabajo")  # Solo lectura
    plaza_texto = StringField("Plaza")  # Solo lectura
    quincena = StringField("Quincena", validators=[DataRequired(), Regexp(QUINCENA_REGEXP)])
    desde_clave = StringField("Desde", validators=[DataRequired(), Regexp(QUINCENA_REGEXP)])
    hasta_clave = StringField("Hasta", validators=[DataRequired(), Regexp(QUINCENA_REGEXP)])
    tipo = StringField("Tipo")  # Solo lectura
    fecha_pago = DateField("Fecha de pago", validators=[DataRequired()])
    p30 = FloatField("P30 PRIMA DE ANTIGUEDAD (EXCENTA)", validators=[Optional()])
    pgn = FloatField("PGN PRIMA DE ANTIGUEDAD (GRAVABLE)", validators=[Optional()])
    pga = FloatField("PGA AGUINALDO (GRAVABLE)", validators=[Optional()])
    p22 = FloatField("P22 AGUINALDO (EXCENTO)", validators=[Optional()])
    pvd = FloatField("PVD VACACIONES NO DISFRUTADAS", validators=[Optional()])
    pgp = FloatField("PGP PRIMA VACACIONAL (GRAVABLE)", validators=[Optional()])
    p20 = FloatField("P20 PRIMA VACACIONAL (EXCENTA)", validators=[Optional()])
    pam = FloatField("PAM EMOLUMENTO SUPERNUMERARIO", validators=[Optional()])
    ps3 = FloatField("PS3 APOYO CASUISTICO", validators=[Optional()])
    p07 = FloatField("P07 PENSION VITALICIA (EXENTO)", validators=[Optional()])
    p7g = FloatField("P7G PENSION VITALICIA (GRAVABLE)", validators=[Optional()])
    phr = FloatField("PHR HABER POR RETIRO", validators=[Optional()])
    pfb = FloatField("PFB APOYO FUNERARIO Y BECAS", validators=[Optional()])
    d01 = FloatField("D01 IMPUESTO FEDERAL RETENIDO ISR", validators=[Optional()])
    d1a = FloatField("D1A IMPUESTO FEDERAL RETENIDO (ISR) PENSION VITALICIA", validators=[Optional()])
    guardar = SubmitField("Guardar")
