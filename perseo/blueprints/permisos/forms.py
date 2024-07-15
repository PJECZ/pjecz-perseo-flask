"""
Permisos, formularios
"""

from flask_wtf import FlaskForm
from wtforms import RadioField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired

from perseo.blueprints.modulos.models import Modulo
from perseo.blueprints.roles.models import Rol

NIVELES = [
    (1, "1) Ver"),
    (2, "2) Ver y Modificar"),
    (3, "3) Ver, Modificar y Crear"),
    (4, "4) ADMINISTRAR (Todos los anteriores más eliminar y recuperar)"),
]


class PermisoEditForm(FlaskForm):
    """Formulario para editar Permiso"""

    modulo = StringField("Módulo")  # Solo lectura
    rol = StringField("Rol")  # Solo lectura
    nivel = RadioField("Nivel", validators=[DataRequired()], choices=NIVELES, coerce=int)
    guardar = SubmitField("Guardar")


class PermisoNewWithModuloForm(FlaskForm):
    """Formulario para agregar Permiso con el modulo como parametro"""

    modulo = StringField("Módulo")  # Solo lectura
    rol = SelectField("Rol", coerce=int, validators=[DataRequired()])
    nivel = RadioField("Nivel", validators=[DataRequired()], choices=NIVELES, coerce=int)
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones para rol"""
        super().__init__(*args, **kwargs)
        self.rol.choices = [(r.id, r.nombre) for r in Rol.query.filter_by(estatus="A").order_by(Rol.nombre).all()]


class PermisoNewWithRolForm(FlaskForm):
    """Formulario para agregar Permiso con el rol como parametro"""

    modulo = SelectField("Modulo", coerce=int, validators=[DataRequired()])
    rol = StringField("Rol")  # Solo lectura
    nivel = RadioField("Nivel", validators=[DataRequired()], choices=NIVELES, coerce=int)
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones para modulo"""
        super().__init__(*args, **kwargs)
        self.modulo.choices = [(m.id, m.nombre) for m in Modulo.query.filter_by(estatus="A").order_by(Modulo.nombre).all()]
