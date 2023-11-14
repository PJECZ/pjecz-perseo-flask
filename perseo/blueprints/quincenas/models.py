"""
Quincenas, modelos
"""
from sqlalchemy import Column, Enum, Integer, String
from sqlalchemy.orm import relationship

from lib.universal_mixin import UniversalMixin
from perseo.extensions import database


class Quincena(database.Model, UniversalMixin):
    """Quincena"""

    ESTADOS = {
        "ABIERTA": "ABIERTA",
        "CERRADA": "CERRADA",
    }

    # Nombre de la tabla
    __tablename__ = "quincenas"

    # Clave primaria
    id = Column(Integer, primary_key=True)

    # Columnas
    clave = Column(String(6), unique=True, nullable=False)
    estado = Column(Enum(*ESTADOS, name="quincenas_estados"), nullable=False)

    # Hijos
    beneficiarios_quincenas = relationship("BeneficiarioQuincena", back_populates="quincena")
    quincenas_productos = relationship("QuincenaProducto", back_populates="quincena")
    nominas = relationship("Nomina", back_populates="quincena")
    percepciones_deducciones = relationship("PercepcionDeduccion", back_populates="quincena")

    def __repr__(self):
        """Representación"""
        return f"<Quincena {self.quincena}>"
