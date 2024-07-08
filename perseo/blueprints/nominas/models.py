"""
Nominas, modelos
"""

from datetime import date
from decimal import Decimal, getcontext
from typing import List, Optional

from sqlalchemy import Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lib.universal_mixin import UniversalMixin
from perseo.extensions import database

getcontext().prec = 4  # Cuatro decimales en los cálculos monetarios


class Nomina(database.Model, UniversalMixin):
    """Nomina"""

    TIPOS = {
        "AGUINALDO": "AGUINALDO",
        "APOYO ANUAL": "APOYO ANUAL",
        "DESPENSA": "DESPENSA",
        "SALARIO": "SALARIO",
        "EXTRAORDINARIO": "EXTRAORDINARIO",
        "PENSION ALIMENTICIA": "PENSION ALIMENTICIA",
    }

    # Nombre de la tabla
    __tablename__ = "nominas"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    centro_trabajo_id: Mapped[int] = mapped_column(ForeignKey("centros_trabajos.id"))
    centro_trabajo: Mapped["CentroTrabajo"] = relationship(back_populates="nominas")
    persona_id: Mapped[int] = mapped_column(ForeignKey("personas.id"))
    persona: Mapped["Persona"] = relationship(back_populates="nominas")
    plaza_id: Mapped[int] = mapped_column(ForeignKey("plazas.id"))
    plaza: Mapped["Plaza"] = relationship(back_populates="nominas")
    quincena_id: Mapped[int] = mapped_column(ForeignKey("quincenas.id"))
    quincena: Mapped["Quincena"] = relationship(back_populates="nominas")

    # Columnas
    tipo: Mapped[str] = mapped_column(Enum(*TIPOS, name="nominas_tipos"), index=True)
    desde: Mapped[date]
    desde_clave: Mapped[str] = mapped_column(String(6))
    hasta: Mapped[date]
    hasta_clave: Mapped[str] = mapped_column(String(6))
    percepcion: Mapped[Decimal] = mapped_column(Numeric(precision=24, scale=4))
    deduccion: Mapped[Decimal] = mapped_column(Numeric(precision=24, scale=4))
    importe: Mapped[Decimal] = mapped_column(Numeric(precision=24, scale=4))
    num_cheque: Mapped[str] = mapped_column(String(24), default="", server_default="")
    fecha_pago: Mapped[date]
    timbrado_id: Mapped[Optional[int]]

    # Hijos
    timbrados: Mapped[List["Timbrado"]] = relationship("Timbrado", back_populates="nomina")

    def __repr__(self):
        """Representación"""
        return f"<Nomina {self.id}>"
