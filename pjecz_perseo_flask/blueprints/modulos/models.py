"""
Modulos
"""

from typing import List

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...config.extensions import database
from ...lib.universal_mixin import UniversalMixin


class Modulo(database.Model, UniversalMixin):
    """Modulo"""

    # Nombre de la tabla
    __tablename__ = "modulos"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Columnas
    nombre: Mapped[str] = mapped_column(String(256), unique=True)
    nombre_corto: Mapped[str] = mapped_column(String(64))
    icono: Mapped[str] = mapped_column(String(48))
    ruta: Mapped[str] = mapped_column(String(64))
    en_navegacion: Mapped[bool] = mapped_column(default=False)

    # Hijos
    bitacoras: Mapped[List["Bitacora"]] = relationship("Bitacora", back_populates="modulo")
    permisos: Mapped[List["Permiso"]] = relationship("Permiso", back_populates="modulo")

    def __repr__(self):
        """Representación"""
        return f"<Modulo {self.nombre}>"
