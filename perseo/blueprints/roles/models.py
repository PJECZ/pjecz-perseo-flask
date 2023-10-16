"""
Roles
"""
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from perseo.extensions import database
from lib.universal_mixin import UniversalMixin


class Rol(database.Model, UniversalMixin):
    """Rol"""

    # Nombre de la tabla
    __tablename__ = "roles"

    # Clave primaria
    id = Column(Integer, primary_key=True)

    # Columnas
    nombre = Column(String(256), unique=True, nullable=False)

    # Hijos
    permisos = relationship("Permiso", back_populates="rol")
    usuarios_roles = relationship("UsuarioRol", back_populates="rol")

    def __repr__(self):
        """Representación"""
        return f"<Rol {self.nombre}>"
