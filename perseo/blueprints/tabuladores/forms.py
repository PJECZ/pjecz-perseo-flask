"""
Tabuladores, formularios
"""
from flask_wtf import FlaskForm
from wtforms import DateField, DecimalField, IntegerField, SelectField, SubmitField
from wtforms.validators import DataRequired

from perseo.blueprints.puestos.models import Puesto


class TabuladorForm(FlaskForm):
    """Formulario Tabulador"""

    puesto = SelectField("Puesto", coerce=int, validators=[DataRequired()])
    modelo = IntegerField("Modelo", validators=[DataRequired()])
    nivel = IntegerField("Nivel", validators=[DataRequired()])
    quinquenio = IntegerField("Quinquenio", validators=[DataRequired()])
    fecha = DateField("Fecha", validators=[DataRequired()])
    sueldo_base = DecimalField("Sueldo base", validators=[DataRequired()], default=0.0)
    incentivo = DecimalField("Incentivo", validators=[DataRequired()], default=0.0)
    monedero = DecimalField("Monedero", validators=[DataRequired()], default=0.0)
    rec_cul_dep = DecimalField("Rec. Cul. Dep.", validators=[DataRequired()], default=0.0)
    sobresueldo = DecimalField("Sobresueldo", validators=[DataRequired()], default=0.0)
    rec_dep_cul_gravado = DecimalField("Rec. Dep. Cul. Gravado", validators=[DataRequired()], default=0.0)
    rec_dep_cul_excento = DecimalField("Rec. Dep. Cul. Excento", validators=[DataRequired()], default=0.0)
    ayuda_transp = DecimalField("Ayuda transp.", validators=[DataRequired()], default=0.0)
    monto_quinquenio = DecimalField("Monto quinquenio", validators=[DataRequired()], default=0.0)
    total_percepciones = DecimalField("Total percepciones", validators=[DataRequired()], default=0.0)
    salario_diario = DecimalField("Salario diario", validators=[DataRequired()], default=0.0)
    prima_vacacional_mensual = DecimalField("Prima vacacional mensual", validators=[DataRequired()], default=0.0)
    aguinaldo_mensual = DecimalField("Aguinaldo mensual", validators=[DataRequired()], default=0.0)
    prima_vacacional_mensual_adicional = DecimalField("Prima vacacional men. adic.", validators=[DataRequired()], default=0.0)
    total_percepciones_integrado = DecimalField("Total percepciones integrado", validators=[DataRequired()], default=0.0)
    salario_diario_integrado = DecimalField("Salario diario integrado", validators=[DataRequired()], default=0.0)
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones de puestos"""
        super().__init__(*args, **kwargs)
        self.puesto.choices = [
            (d.id, d.clave + " - " + d.descripcion) for d in Puesto.query.filter_by(estatus="A").order_by(Puesto.clave).all()
        ]
