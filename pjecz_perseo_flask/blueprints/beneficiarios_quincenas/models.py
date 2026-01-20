"""
Beneficiarios Quincenas, modelos
"""

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...config.extensions import database
from ...lib.universal_mixin import UniversalMixin


class BeneficiarioQuincena(database.Model, UniversalMixin):
    """BeneficiarioQuincena"""

    # Nombre de la tabla
    __tablename__ = "beneficiarios_quincenas"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    beneficiario_id: Mapped[int] = mapped_column(ForeignKey("beneficiarios.id"), index=True)
    beneficiario: Mapped["Beneficiario"] = relationship(back_populates="beneficiarios_quincenas")
    quincena_id: Mapped[int] = mapped_column(ForeignKey("quincenas.id"), index=True)
    quincena: Mapped["Quincena"] = relationship(back_populates="beneficiarios_quincenas")

    # Columnas
    importe: Mapped[float] = mapped_column(Numeric(precision=24, scale=4))
    num_cheque: Mapped[str] = mapped_column(String(24), default="", server_default="")

    def __repr__(self):
        """Representación"""
        return f"<BeneficiarioQuincena {self.id}>"
