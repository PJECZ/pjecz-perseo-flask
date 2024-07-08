"""
Plazas, modelos
"""

from typing import List

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lib.universal_mixin import UniversalMixin
from perseo.extensions import database


class Plaza(database.Model, UniversalMixin):
    """Plaza"""

    # Nombre de la tabla
    __tablename__ = "plazas"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Columnas
    clave: Mapped[str] = mapped_column(String(24), unique=True)
    descripcion: Mapped[str] = mapped_column(String(256))

    # Hijos
    nominas: Mapped[List["Nomina"]] = relationship("Nomina", back_populates="plaza")
    percepciones_deducciones: Mapped[List["PercepcionDeduccion"]] = relationship("PercepcionDeduccion", back_populates="plaza")

    def __repr__(self):
        """Representación"""
        return f"<Plaza {self.clave}>"
