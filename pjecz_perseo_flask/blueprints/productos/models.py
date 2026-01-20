"""
Productos, modelos
"""

from typing import List

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...config.extensions import database
from ...lib.universal_mixin import UniversalMixin


class Producto(database.Model, UniversalMixin):
    """Producto"""

    # Nombre de la tabla
    __tablename__ = "productos"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Columnas
    clave: Mapped[str] = mapped_column(String(16), unique=True)
    descripcion: Mapped[str] = mapped_column(String(256))

    # Hijos
    conceptos_productos: Mapped[List["ConceptoProducto"]] = relationship("ConceptoProducto", back_populates="producto")

    def __repr__(self):
        """Representación"""
        return f"<Producto {self.clave}>"
