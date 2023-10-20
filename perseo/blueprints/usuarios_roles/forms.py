"""
Usuarios-Roles, formularios
"""
from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField
from wtforms.validators import DataRequired

from perseo.blueprints.roles.models import Rol
from perseo.blueprints.usuarios.models import Usuario


class UsuarioRolNewWithRolForm(FlaskForm):
    """Formulario para agregar Usuario-Rol con el rol como parametro"""

    rol_nombre = StringField("Rol")  # Solo lectura
    usuario = SelectField("Usuario", coerce=int, validators=[DataRequired()])
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones para rol"""
        super().__init__(*args, **kwargs)
        self.usuario.choices = [(u.id, u.email) for u in Usuario.query.filter_by(estatus="A").order_by(Usuario.email).all()]


class UsuarioRolNewWithUsuarioForm(FlaskForm):
    """Formulario para agregar Usuario-Rol con el usuario como parametro"""

    rol = SelectField("Rol", coerce=int, validators=[DataRequired()])
    usuario_email = StringField("Usuario e-mail")  # Solo lectura
    usuario_nombre = StringField("Usuario nombre")  # Solo lectura
    usuario_puesto = StringField("Usuario puesto")  # Solo lectura
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones para rol"""
        super().__init__(*args, **kwargs)
        self.rol.choices = [(r.id, r.nombre) for r in Rol.query.filter_by(estatus="A").order_by(Rol.nombre).all()]
