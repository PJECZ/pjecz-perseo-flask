"""
Bancos, modelos
"""

from typing import List

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lib.universal_mixin import UniversalMixin
from perseo.extensions import database


class Banco(database.Model, UniversalMixin):
    """Banco"""

    # Nombre de la tabla
    __tablename__ = "bancos"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Columnas
    clave: Mapped[str] = mapped_column(String(2), unique=True)
    clave_dispersion_pensionados: Mapped[str] = mapped_column(String(2), unique=True)
    nombre: Mapped[str] = mapped_column(String(256), unique=True)
    consecutivo: Mapped[int] = mapped_column(default=0)
    consecutivo_generado: Mapped[int] = mapped_column(default=0)

    # Hijos
    beneficiarios_cuentas: Mapped[List["BeneficiarioCuenta"]] = relationship(back_populates="banco")
    cuentas: Mapped[List["Cuenta"]] = relationship(back_populates="banco")

    def __repr__(self):
        """Representación"""
        return f"<Banco {self.clave}>"
