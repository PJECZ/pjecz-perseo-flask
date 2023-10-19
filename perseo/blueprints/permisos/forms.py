"""
Permisos, formularios
"""
from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField
from wtforms.validators import DataRequired

from perseo.blueprints.modulos.models import Modulo
from perseo.blueprints.roles.models import Rol

NIVELES = [
    (1, "VER"),
    (2, "VER y MODIFICAR"),
    (3, "VER, MODIFICAR y CREAR"),
    (4, "ADMINISTRAR"),
]


class PermisoEditForm(FlaskForm):
    """Formulario para editar Permiso"""

    modulo = StringField("Módulo")  # Solo lectura
    rol = StringField("Rol")  # Solo lectura
    nivel = SelectField("Nivel", validators=[DataRequired()], choices=NIVELES, coerce=int)
    guardar = SubmitField("Guardar")


class PermisoNewWithModuloForm(FlaskForm):
    """Formulario para agregar Permiso con el modulo como parametro"""

    modulo = StringField("Módulo")  # Solo lectura
    rol = SelectField("Rol", coerce=int, validators=[DataRequired()])
    nivel = SelectField("Nivel", validators=[DataRequired()], choices=NIVELES, coerce=int)
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones para rol"""
        super().__init__(*args, **kwargs)
        self.rol.choices = [(d.id, d.nombre) for d in Rol.query.filter_by(estatus="A").order_by(Rol.nombre).all()]


class PermisoNewWithRolForm(FlaskForm):
    """Formulario para agregar Permiso con el rol como parametro"""

    modulo = SelectField("Modulo", coerce=int, validators=[DataRequired()])
    rol = StringField("Rol")  # Solo lectura
    nivel = SelectField("Nivel", validators=[DataRequired()], choices=NIVELES, coerce=int)
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones para modulo"""
        super().__init__(*args, **kwargs)
        self.modulo.choices = [(d.id, d.nombre) for d in Modulo.query.filter_by(estatus="A").order_by(Modulo.nombre).all()]
