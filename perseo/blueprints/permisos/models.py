"""
Permisos
"""

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lib.universal_mixin import UniversalMixin
from perseo.extensions import database


class Permiso(database.Model, UniversalMixin):
    """Permiso"""

    VER = 1
    MODIFICAR = 2
    CREAR = 3
    BORRAR = 3
    ADMINISTRAR = 4
    NIVELES = {
        1: "VER",
        2: "VER y MODIFICAR",
        3: "VER, MODIFICAR y CREAR",
        4: "ADMINISTRAR",
    }

    # Nombre de la tabla
    __tablename__ = "permisos"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Claves foráneas
    rol_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    rol: Mapped["Rol"] = relationship(back_populates="permisos")
    modulo_id: Mapped[int] = mapped_column(ForeignKey("modulos.id"))
    modulo: Mapped["Modulo"] = relationship(back_populates="permisos")

    # Columnas
    nombre: Mapped[str] = mapped_column(String(256), unique=True)
    nivel: Mapped[int]

    @property
    def rol_nombre(self):
        """Nombre del rol"""
        return self.rol.nombre

    @property
    def modulo_nombre(self):
        """Nombre del modulo"""
        return self.modulo.nombre

    @property
    def nivel_descrito(self):
        """Nivel descrito"""
        return self.NIVELES[self.nivel]

    def __repr__(self):
        """Representación"""
        return f"<Permiso {self.id}>"
