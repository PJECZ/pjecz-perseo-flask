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
    clave = Column(String(16), unique=True, nullable=False)
    nombre = Column(String(256), nullable=False)
    consecutivo = Column(Integer, nullable=False)

    # Hijos
    cuentas = relationship("Cuenta", back_populates="banco")

    def __repr__(self):
        """Representación"""
        return f"<Banco {self.clave}>"
