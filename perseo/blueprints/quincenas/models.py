"""
Quincenas, modelos
"""

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lib.universal_mixin import UniversalMixin
from perseo.extensions import database


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
    tiene_aguinaldos: Mapped[bool] = mapped_column(Boolean(), default=False)
    tiene_apoyos_anuales: Mapped[bool] = mapped_column(Boolean(), default=False)
    tiene_primas_vacacionales: Mapped[bool] = mapped_column(Boolean(), default=False)

    # Hijos
    beneficiarios_quincenas: Mapped["BeneficiarioQuincena"] = relationship(
        "BeneficiarioQuincena",
        back_populates="quincena",
        lazy="noload",
    )
    quincenas_productos: Mapped["QuincenaProducto"] = relationship(
        "QuincenaProducto",
        back_populates="quincena",
    )
    nominas: Mapped["Nomina"] = relationship(
        "Nomina",
        back_populates="quincena",
        lazy="noload",
    )
    percepciones_deducciones: Mapped["PercepcionDeduccion"] = relationship(
        "PercepcionDeduccion",
        back_populates="quincena",
        lazy="noload",
    )

    def __repr__(self):
        """Representación"""
        return f"<Quincena {self.clave}>"
