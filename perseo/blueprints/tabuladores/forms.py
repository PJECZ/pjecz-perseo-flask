"""
Tabuladores, formularios
"""

from flask_wtf import FlaskForm
from wtforms import DateField, DecimalField, SelectField, SubmitField
from wtforms.validators import DataRequired, Optional

from perseo.blueprints.puestos.models import Puesto

MODELOS = [
    (1, "1) CONFIANZA"),
    (2, "2) SINDICALIZADO"),
    (3, "3) JUBILADO"),
]

NIVELES = [
    (0, "0) SIN NIVEL"),
    (1, "1) NIVEL 1"),
    (2, "2) NIVEL 2"),
    (3, "3) NIVEL 3"),
    (4, "4) NIVEL 4"),
    (5, "5) NIVEL 5"),
    (6, "6) NIVEL 6"),
    (7, "7) NIVEL 7"),
    (8, "8) NIVEL 8"),
    (9, "9) NIVEL 9"),
]

QUINQUENIOS = [
    (0, "0) SIN QUINQUENIO"),
    (1, "1) 1° QUINQUENIO"),
    (2, "2) 2° QUINQUENIO"),
    (3, "3) 3° QUINQUENIO"),
    (4, "4) 4° QUINQUENIO"),
    (5, "5) 5° QUINQUENIO"),
    (6, "6) 6° QUINQUENIO"),
]


class TabuladorForm(FlaskForm):
    """Formulario Tabulador"""

    puesto = SelectField("Puesto", coerce=int, validators=[DataRequired()])
    modelo = SelectField("Modelo", validators=[DataRequired()], choices=MODELOS, coerce=int)
    nivel = SelectField("Nivel", validators=[Optional()], choices=NIVELES, coerce=int)
    quinquenio = SelectField("Quinquenio", validators=[Optional()], choices=QUINQUENIOS, coerce=int)
    fecha = DateField("Fecha", validators=[DataRequired()])
    sueldo_base = DecimalField("Sueldo base", validators=[Optional()], default=0.0)
    incentivo = DecimalField("Incentivo", validators=[Optional()], default=0.0)
    monedero = DecimalField("Monedero", validators=[Optional()], default=0.0)
    rec_cul_dep = DecimalField("Rec. Cul. Dep.", validators=[Optional()], default=0.0)
    sobresueldo = DecimalField("Sobresueldo", validators=[Optional()], default=0.0)
    rec_dep_cul_gravado = DecimalField("Rec. Dep. Cul. Gravado", validators=[Optional()], default=0.0)
    rec_dep_cul_excento = DecimalField("Rec. Dep. Cul. Excento", validators=[Optional()], default=0.0)
    ayuda_transp = DecimalField("Ayuda transp.", validators=[Optional()], default=0.0)
    monto_quinquenio = DecimalField("Monto quinquenio", validators=[Optional()], default=0.0)
    total_percepciones = DecimalField("Total percepciones", validators=[Optional()], default=0.0)
    salario_diario = DecimalField("Salario diario", validators=[Optional()], default=0.0)
    prima_vacacional_mensual = DecimalField("Prima vacacional mensual", validators=[Optional()], default=0.0)
    aguinaldo_mensual = DecimalField("Aguinaldo mensual", validators=[Optional()], default=0.0)
    prima_vacacional_mensual_adicional = DecimalField("Prima vacacional men. adic.", validators=[Optional()], default=0.0)
    total_percepciones_integrado = DecimalField("Total percepciones integrado", validators=[Optional()], default=0.0)
    salario_diario_integrado = DecimalField("Salario diario integrado", validators=[Optional()], default=0.0)
    pension_vitalicia_excento = DecimalField("Pensión vitalicia excento", validators=[Optional()], default=0.0)
    pension_vitalicia_gravable = DecimalField("Pensión vitalicia gravable", validators=[Optional()], default=0.0)
    pension_bonificacion = DecimalField("Pensión bonificación", validators=[Optional()], default=0.0)
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones de puestos"""
        super().__init__(*args, **kwargs)
        self.puesto.choices = [
            (d.id, d.clave + " - " + d.descripcion) for d in Puesto.query.filter_by(estatus="A").order_by(Puesto.clave).all()
        ]
