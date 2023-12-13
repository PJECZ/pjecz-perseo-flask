"""
Beneficiarios, modelos
"""
from sqlalchemy import Column, Date, Integer, String
from sqlalchemy.orm import relationship

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
    id = Column(Integer, primary_key=True)

    # Columnas
    rfc = Column(String(13), nullable=False, unique=True)
    nombres = Column(String(256), nullable=False, index=True)
    apellido_primero = Column(String(256), nullable=False, index=True)
    apellido_segundo = Column(String(256), nullable=False, default="", server_default="")
    curp = Column(String(18), nullable=False, default="", server_default="")
    nacimiento_fecha = Column(Date)

    # Columna modelo en Beneficiario
    # 4: Beneficiario
    # 5: Consejero
    # 6: Escolta
    modelo = Column(Integer, nullable=False, default=0, index=True)

    # Hijos
    beneficiarios_cuentas = relationship("BeneficiarioCuenta", back_populates="beneficiario")
    beneficiarios_quincenas = relationship("BeneficiarioQuincena", back_populates="beneficiario")

    @property
    def nombre_completo(self):
        """Nombre completo"""
        return f"{self.nombres} {self.apellido_primero} {self.apellido_segundo}"

    def __repr__(self):
        """Representación"""
        return f"<Beneficiario {self.rfc}>"
