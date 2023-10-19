"""
Distritos, formularios
"""
from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, Optional


class DistritoForm(FlaskForm):
    """Formulario Distrito"""

    clave = StringField("Clave (única, máximo 16 caracteres)", validators=[DataRequired(), Length(max=16)])
    nombre = StringField("Nombre", validators=[DataRequired(), Length(max=256)])
    nombre_corto = StringField("Nombre corto", validators=[Optional(), Length(max=64)])
    es_distrito = BooleanField("Es Distrito (geográfico)", validators=[Optional()])
    es_jurisdiccional = BooleanField("Es Jurisdiccional", validators=[Optional()])
    guardar = SubmitField("Guardar")
