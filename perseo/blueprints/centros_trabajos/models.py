"""
Centros de Trabajo, modelos
"""

from typing import List

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lib.universal_mixin import UniversalMixin
from perseo.extensions import database


class CentroTrabajo(database.Model, UniversalMixin):
    """CentroTrabajo"""

    # Nombre de la tabla
    __tablename__ = "centros_trabajos"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Columnas
    clave: Mapped[str] = mapped_column(String(16), unique=True)
    descripcion: Mapped[str] = mapped_column(String(256))

    # Hijos
    nominas: Mapped[List["Nomina"]] = relationship(back_populates="centro_trabajo")
    percepciones_deducciones: Mapped[List["PercepcionDeduccion"]] = relationship(back_populates="centro_trabajo")

    def __repr__(self):
        """Representación"""
        return f"<CentroTrabajo {self.clave}>"
