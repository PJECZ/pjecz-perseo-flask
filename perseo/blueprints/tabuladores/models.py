"""
Tabuladores, modelos
"""

from datetime import date
from decimal import Decimal, getcontext
from typing import List

from sqlalchemy import ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lib.universal_mixin import UniversalMixin
from perseo.extensions import database

getcontext().prec = 4  # Cuatro decimales en los cálculos monetarios


class Tabulador(database.Model, UniversalMixin):
    """Tabulador"""

    # Nombre de la tabla
    __tablename__ = "tabuladores"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    puesto_id: Mapped[int] = mapped_column(Integer, ForeignKey("puestos.id"), index=True)
    puesto: Mapped["Puesto"] = relationship("Puesto", back_populates="tabuladores")

    # Columnas que junto con el Puesto hacen una combinación única
    modelo: Mapped[int]
    nivel: Mapped[int]
    quinquenio: Mapped[int]

    # Columnas independientes
    fecha: Mapped[date]
    sueldo_base: Mapped[Decimal] = mapped_column(Numeric(precision=24, scale=4))
    incentivo: Mapped[Decimal] = mapped_column(Numeric(precision=24, scale=4))
    monedero: Mapped[Decimal] = mapped_column(Numeric(precision=24, scale=4))
    rec_cul_dep: Mapped[Decimal] = mapped_column(Numeric(precision=24, scale=4))
    sobresueldo: Mapped[Decimal] = mapped_column(Numeric(precision=24, scale=4))
    rec_dep_cul_gravado: Mapped[Decimal] = mapped_column(Numeric(precision=24, scale=4))
    rec_dep_cul_excento: Mapped[Decimal] = mapped_column(Numeric(precision=24, scale=4))
    ayuda_transp: Mapped[Decimal] = mapped_column(Numeric(precision=24, scale=4))
    monto_quinquenio: Mapped[Decimal] = mapped_column(Numeric(precision=24, scale=4))
    total_percepciones: Mapped[Decimal] = mapped_column(Numeric(precision=24, scale=4))
    salario_diario: Mapped[Decimal] = mapped_column(Numeric(precision=24, scale=4))
    prima_vacacional_mensual: Mapped[Decimal] = mapped_column(Numeric(precision=24, scale=4))
    aguinaldo_mensual: Mapped[Decimal] = mapped_column(Numeric(precision=24, scale=4))
    prima_vacacional_mensual_adicional: Mapped[Decimal] = mapped_column(Numeric(precision=24, scale=4))
    total_percepciones_integrado: Mapped[Decimal] = mapped_column(Numeric(precision=24, scale=4))
    salario_diario_integrado: Mapped[Decimal] = mapped_column(Numeric(precision=24, scale=4))

    # Columnas para pensionados
    pension_vitalicia_excento: Mapped[Decimal] = mapped_column(Numeric(precision=24, scale=4))
    pension_vitalicia_gravable: Mapped[Decimal] = mapped_column(Numeric(precision=24, scale=4))
    pension_bonificacion: Mapped[Decimal] = mapped_column(Numeric(precision=24, scale=4))

    # Hijos
    personas: Mapped[List["Persona"]] = relationship("Persona", back_populates="tabulador")

    def __repr__(self):
        """Representación"""
        return f"<Tabulador {self.id}>"
