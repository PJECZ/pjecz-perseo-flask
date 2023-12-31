"""
Bancos, modelos
"""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from lib.universal_mixin import UniversalMixin
from perseo.extensions import database


class Banco(database.Model, UniversalMixin):
    """Banco"""

    # Nombre de la tabla
    __tablename__ = "bancos"

    # Clave primaria
    id = Column(Integer, primary_key=True)

    # Columnas
    clave = Column(String(2), unique=True, nullable=False)
    clave_dispersion_pensionados = Column(String(3), unique=True, nullable=False)
    nombre = Column(String(256), unique=True, nullable=False)
    consecutivo = Column(Integer, nullable=False, default=0)
    consecutivo_generado = Column(Integer, nullable=False, default=0)

    # Hijos
    beneficiarios_cuentas = relationship("BeneficiarioCuenta", back_populates="banco")
    cuentas = relationship("Cuenta", back_populates="banco")

    def __repr__(self):
        """Representación"""
        return f"<Banco {self.clave}>"
