"""
Usuarios, modelos
"""
from flask_login import UserMixin
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from lib.universal_mixin import UniversalMixin
from perseo.blueprints.permisos.models import Permiso
from perseo.blueprints.usuarios_roles.models import UsuarioRol
from perseo.extensions import database, pwd_context


class Usuario(database.Model, UserMixin, UniversalMixin):
    """Usuario"""

    # Nombre de la tabla
    __tablename__ = "usuarios"

    # Clave primaria
    id = Column(Integer, primary_key=True)

    # Claves foráneas
    autoridad_id = Column(Integer, ForeignKey("autoridades.id"), index=True, nullable=False)
    autoridad = relationship("Autoridad", back_populates="usuarios")

    # Columnas
    email = Column(String(256), nullable=False, unique=True, index=True)
    nombres = Column(String(256), nullable=False)
    apellido_primero = Column(String(256), nullable=False)
    apellido_segundo = Column(String(256))
    curp = Column(String(18), default="", server_default="")
    puesto = Column(String(256), default="", server_default="")

    # Columnas que no deben ser expuestas
    api_key = Column(String(128), nullable=False)
    api_key_expiracion = Column(DateTime(), nullable=False)
    contrasena = Column(String(256), nullable=False)

    # Hijos
    bitacoras = relationship("Bitacora", back_populates="usuario", lazy="noload")
    entradas_salidas = relationship("EntradaSalida", back_populates="usuario", lazy="noload")
    usuarios_roles = relationship("UsuarioRol", back_populates="usuario")

    # Propiedades
    modulos_menu_principal_consultados = []
    permisos_consultados = {}

    @property
    def nombre(self):
        """Junta nombres, apellido primero y apellido segundo"""
        return self.nombres + " " + self.apellido_primero + " " + self.apellido_segundo

    @property
    def modulos_menu_principal(self):
        """Elaborar listado con los modulos ordenados para el menu principal"""
        if len(self.modulos_menu_principal_consultados) > 0:
            return self.modulos_menu_principal_consultados
        modulos = []
        modulos_nombres = []
        for usuario_rol in self.usuarios_roles:
            if usuario_rol.estatus == "A":
                for permiso in usuario_rol.rol.permisos:
                    if (
                        permiso.modulo.nombre not in modulos_nombres
                        and permiso.estatus == "A"
                        and permiso.nivel > 0
                        and permiso.modulo.en_navegacion
                    ):
                        modulos.append(permiso.modulo)
                        modulos_nombres.append(permiso.modulo.nombre)
        self.modulos_menu_principal_consultados = sorted(modulos, key=lambda x: x.nombre_corto)
        return self.modulos_menu_principal_consultados

    @property
    def permisos(self):
        """Entrega un diccionario con todos los permisos"""
        if len(self.permisos_consultados) > 0:
            return self.permisos_consultados
        self.permisos_consultados = {}
        for usuario_rol in self.usuarios_roles:
            if usuario_rol.estatus == "A":
                for permiso in usuario_rol.rol.permisos:
                    if permiso.estatus == "A":
                        etiqueta = permiso.modulo.nombre
                        if etiqueta not in self.permisos_consultados or permiso.nivel > self.permisos_consultados[etiqueta]:
                            self.permisos_consultados[etiqueta] = permiso.nivel
        return self.permisos_consultados

    @classmethod
    def find_by_identity(cls, identity):
        """Encontrar a un usuario por su correo electrónico"""
        return Usuario.query.filter(Usuario.email == identity).first()

    @property
    def is_active(self):
        """¿Es activo?"""
        return self.estatus == "A"

    def authenticated(self, with_password=True, password=""):
        """Ensure a user is authenticated, and optionally check their password."""
        if self.id and with_password:
            return pwd_context.verify(password, self.contrasena)
        return True

    def can(self, modulo_nombre: str, permission: int):
        """¿Tiene permiso?"""
        if modulo_nombre in self.permisos:
            return self.permisos[modulo_nombre] >= permission
        return False

    def can_view(self, modulo_nombre: str):
        """¿Tiene permiso para ver?"""
        return self.can(modulo_nombre, Permiso.VER)

    def can_edit(self, modulo_nombre: str):
        """¿Tiene permiso para editar?"""
        return self.can(modulo_nombre, Permiso.MODIFICAR)

    def can_insert(self, modulo_nombre: str):
        """¿Tiene permiso para agregar?"""
        return self.can(modulo_nombre, Permiso.CREAR)

    def can_admin(self, modulo_nombre: str):
        """¿Tiene permiso para administrar?"""
        return self.can(modulo_nombre, Permiso.ADMINISTRAR)

    def get_roles(self):
        """Obtener roles"""
        usuarios_roles = UsuarioRol.query.filter_by(usuario_id=self.id).filter_by(estatus="A").all()
        return [usuario_rol.rol.nombre for usuario_rol in usuarios_roles]

    def __repr__(self):
        """Representación"""
        return f"<Usuario {self.email}>"
