"""
Cuentas, formularios
"""

from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length

from ..bancos.models import Banco


class CuentaEditForm(FlaskForm):
    """Formulario para editar el numero de cuenta de una Cuenta"""

    banco_nombre = StringField("Banco")  # Solo lectura
    persona_rfc = StringField("Persona RFC")  # Solo lectura
    persona_nombre = StringField("Persona nombre")  # Solo lectura
    num_cuenta = StringField("No. de cuenta", validators=[DataRequired(), Length(max=256)])
    guardar = SubmitField("Guardar")


class CuentaNewWithPersonaForm(FlaskForm):
    """Formulario para agregar una Cuenta con la persona como parametro"""

    banco = SelectField("Banco", coerce=int, validators=[DataRequired()])
    persona_rfc = StringField("RFC")  # Solo lectura
    persona_nombre = StringField("Nombre")  # Solo lectura
    num_cuenta = StringField("No. de cuenta", validators=[DataRequired(), Length(max=256)])
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones para banco"""
        super().__init__(*args, **kwargs)
        self.banco.choices = [(b.id, b.nombre) for b in Banco.query.filter_by(estatus="A").order_by(Banco.nombre).all()]
