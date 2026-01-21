"""
Quincenas, modelos
"""

from typing import List

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...config.extensions import database
from ...lib.universal_mixin import UniversalMixin


class Quincena(database.Model, UniversalMixin):
    """Quincena"""

    ESTADOS = {
        "ABIERTA": "ABIERTA",
        "CERRADA": "CERRADA",
    }

    # Nombre de la tabla
    __tablename__ = "quincenas"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Columnas
    clave: Mapped[str] = mapped_column(String(6), unique=True)
    estado: Mapped[str] = mapped_column(Enum(*ESTADOS, name="quincenas_estados"), index=True)
    tiene_aguinaldos: Mapped[bool] = mapped_column(default=False)
    tiene_apoyos_anuales: Mapped[bool] = mapped_column(default=False)
    tiene_primas_vacacionales: Mapped[bool] = mapped_column(default=False)

    # Hijos
    beneficiarios_quincenas: Mapped[List["BeneficiarioQuincena"]] = relationship(
        "BeneficiarioQuincena", back_populates="quincena"
    )
    quincenas_productos: Mapped[List["QuincenaProducto"]] = relationship("QuincenaProducto", back_populates="quincena")
    nominas: Mapped[List["Nomina"]] = relationship("Nomina", back_populates="quincena")
    percepciones_deducciones: Mapped[List["PercepcionDeduccion"]] = relationship(
        "PercepcionDeduccion", back_populates="quincena"
    )

    def __repr__(self):
        """Representación"""
        return f"<Quincena {self.clave}>"
