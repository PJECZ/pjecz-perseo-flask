"""
Percepciones Deducciones, modelos
"""

from decimal import Decimal, getcontext

from sqlalchemy import Enum, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lib.universal_mixin import UniversalMixin
from perseo.extensions import database

getcontext().prec = 4  # Cuatro decimales en los cálculos monetarios


class PercepcionDeduccion(database.Model, UniversalMixin):
    """PercepcionDeduccion"""

    TIPOS = {
        "AGUINALDO": "AGUINALDO",
        "APOYO ANUAL": "APOYO ANUAL",
        "DESPENSA": "DESPENSA",
        "SALARIO": "SALARIO",
        "EXTRAORDINARIO": "EXTRAORDINARIO",
        "PRIMA VACACIONAL": "PRIMA VACACIONAL",
    }

    # Nombre de la tabla
    __tablename__ = "percepciones_deducciones"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Claves foráneas
    centro_trabajo_id: Mapped[int] = mapped_column(ForeignKey("centros_trabajos.id"))
    centro_trabajo: Mapped["CentroTrabajo"] = relationship(back_populates="percepciones_deducciones")
    concepto_id: Mapped[int] = mapped_column(ForeignKey("conceptos.id"))
    concepto: Mapped["Concepto"] = relationship(back_populates="percepciones_deducciones")
    persona_id: Mapped[int] = mapped_column(ForeignKey("personas.id"))
    persona: Mapped["Persona"] = relationship(back_populates="percepciones_deducciones")
    plaza_id: Mapped[int] = mapped_column(ForeignKey("plazas.id"))
    plaza: Mapped["Plaza"] = relationship(back_populates="percepciones_deducciones")
    quincena_id: Mapped[int] = mapped_column(ForeignKey("quincenas.id"))
    quincena: Mapped["Quincena"] = relationship(back_populates="percepciones_deducciones")

    # Columnas
    tipo: Mapped[str] = mapped_column(Enum(*TIPOS, name="percepciones_deducciones_tipos"), index=True)
    importe: Mapped[Decimal] = mapped_column(Numeric(precision=24, scale=4))

    def __repr__(self):
        """Representación"""
        return f"<PercepcionDeduccion {self.id}>"
