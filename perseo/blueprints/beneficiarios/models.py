"""
Beneficiarios, modelos
"""

from datetime import date
from typing import List

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lib.universal_mixin import UniversalMixin
from perseo.extensions import database


class Beneficiario(database.Model, UniversalMixin):
    """Beneficiario"""

    MODELOS = {
        4: "BENEFICIARIO",
        5: "CONSEJERO",
        6: "ESCOLTA",
    }

    # Nombre de la tabla
    __tablename__ = "beneficiarios"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Columnas
    rfc: Mapped[str] = mapped_column(String(13), unique=True)
    nombres: Mapped[str] = mapped_column(String(256))
    apellido_primero: Mapped[str] = mapped_column(String(256))
    apellido_segundo: Mapped[str] = mapped_column(String(256), default="", server_default="")
    nacimiento_fecha: Mapped[date] = mapped_column(default=None)
    curp: Mapped[str] = mapped_column(String(18), default="", server_default="")
    modelo: Mapped[int] = mapped_column(default=0, index=True)

    # Hijos
    beneficiarios_cuentas: Mapped[List["BeneficiarioCuenta"]] = relationship(back_populates="beneficiario")
    beneficiarios_quincenas: Mapped[List["BeneficiarioQuincena"]] = relationship(back_populates="beneficiario")

    @property
    def nombre_completo(self):
        """Nombre completo"""
        return f"{self.nombres} {self.apellido_primero} {self.apellido_segundo}"

    def __repr__(self):
        """Representación"""
        return f"<Beneficiario {self.rfc}>"
