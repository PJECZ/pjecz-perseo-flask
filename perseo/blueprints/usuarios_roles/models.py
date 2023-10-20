"""
Usuarios-Roles
"""
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from lib.universal_mixin import UniversalMixin
from perseo.extensions import database


class UsuarioRol(database.Model, UniversalMixin):
    """UsuarioRol"""

    # Nombre de la tabla
    __tablename__ = "usuarios_roles"

    # Clave primaria
    id = Column(Integer, primary_key=True)

    # Claves foráneas
    rol_id = Column(Integer, ForeignKey("roles.id"), index=True, nullable=False)
    rol = relationship("Rol", back_populates="usuarios_roles")
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), index=True, nullable=False)
    usuario = relationship("Usuario", back_populates="usuarios_roles")

    # Columnas
    descripcion = Column(String(256), nullable=False)

    @property
    def rol_nombre(self):
        """Nombre del rol"""
        return self.rol.nombre

    @property
    def usuario_email(self):
        """Email del usuario"""
        return self.usuario.email

    def __repr__(self):
        """Representación"""
        return f"<UsuarioRol {self.id}>"
