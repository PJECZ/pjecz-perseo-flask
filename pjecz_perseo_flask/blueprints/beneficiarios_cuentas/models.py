"""
Beneficiarios Cuentas, modelos
"""

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...config.extensions import database
from ...lib.universal_mixin import UniversalMixin


class BeneficiarioCuenta(database.Model, UniversalMixin):
    """BeneficiarioCuenta"""

    # Nombre de la tabla
    __tablename__ = "beneficiarios_cuentas"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    banco_id: Mapped[int] = mapped_column(ForeignKey("bancos.id"))
    banco: Mapped["Banco"] = relationship(back_populates="beneficiarios_cuentas")
    beneficiario_id: Mapped[int] = mapped_column(ForeignKey("beneficiarios.id"))
    beneficiario: Mapped["Beneficiario"] = relationship(back_populates="beneficiarios_cuentas")

    # Columnas
    num_cuenta: Mapped[str] = mapped_column(String(24))

    def __repr__(self):
        """Representación"""
        return f"<BeneficiarioCuenta {self.id}>"
