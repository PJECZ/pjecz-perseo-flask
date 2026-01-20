"""
Conceptos, modelos
"""

from typing import List

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...config.extensions import database
from ...lib.universal_mixin import UniversalMixin


class Concepto(database.Model, UniversalMixin):
    """Concepto"""

    # Nombre de la tabla
    __tablename__ = "conceptos"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Columnas
    clave: Mapped[str] = mapped_column(String(16), unique=True)
    descripcion: Mapped[str] = mapped_column(String(256))

    # Hijos
    conceptos_productos: Mapped[List["ConceptoProducto"]] = relationship("ConceptoProducto", back_populates="concepto")
    percepciones_deducciones: Mapped[List["PercepcionDeduccion"]] = relationship(
        "PercepcionDeduccion", back_populates="concepto"
    )

    def __repr__(self):
        """Representación"""
        return f"<Concepto {self.clave}>"
