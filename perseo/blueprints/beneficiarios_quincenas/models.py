"""
Beneficiarios Quincenas, modelos
"""
from sqlalchemy import Column, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from lib.universal_mixin import UniversalMixin
from perseo.extensions import database


class BeneficiarioQuincena(database.Model, UniversalMixin):
    """BeneficiarioQuincena"""

    # Nombre de la tabla
    __tablename__ = "beneficiarios_quincenas"

    # Clave primaria
    id = Column(Integer, primary_key=True)

    # Clave foránea
    beneficiario_id = Column(Integer, ForeignKey("beneficiarios.id"), index=True, nullable=False)
    beneficiario = relationship("Beneficiario", back_populates="beneficiarios_quincenas")
    quincena_id = Column(Integer, ForeignKey("quincenas.id"), index=True, nullable=False)
    quincena = relationship("Quincena", back_populates="beneficiarios_quincenas")

    # Columnas
    # quincena = Column(String(6), nullable=False, index=True)
    importe = Column(Numeric(precision=24, scale=4), nullable=False)
    num_cheque = Column(String(24), nullable=False, default="", server_default="")

    def __repr__(self):
        """Representación"""
        return f"<BeneficiarioQuincena {self.id}>"
