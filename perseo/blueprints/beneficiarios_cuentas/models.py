"""
Beneficiarios Cuentas, modelos
"""
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from lib.universal_mixin import UniversalMixin
from perseo.extensions import database


class BeneficiarioCuenta(database.Model, UniversalMixin):
    """BeneficiarioCuenta"""

    # Nombre de la tabla
    __tablename__ = "beneficiarios_cuentas"

    # Clave primaria
    id = Column(Integer, primary_key=True)

    # Clave foránea
    banco_id = Column(Integer, ForeignKey("bancos.id"), index=True, nullable=False)
    banco = relationship("Banco", back_populates="beneficiarios_cuentas")
    beneficiario_id = Column(Integer, ForeignKey("beneficiarios.id"), index=True, nullable=False)
    beneficiario = relationship("Beneficiario", back_populates="beneficiarios_cuentas")

    # Columnas
    num_cuenta = Column(String(24), nullable=False)

    def __repr__(self):
        """Representación"""
        return f"<BeneficiarioCuenta {self.id}>"
