"""
Personas, modelos
"""
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from lib.universal_mixin import UniversalMixin
from perseo.extensions import database


class Persona(database.Model, UniversalMixin):
    """Persona"""

    # Nombre de la tabla
    __tablename__ = "personas"

    # Clave primaria
    id = Column(Integer, primary_key=True)

    # Columnas
    nombres = Column(String(256), nullable=False)
    apellido_primero = Column(String(256), nullable=False)
    apellido_segundo = Column(String(256))
    rfc = Column(String(13), nullable=False, unique=True)
    curp = Column(String(18), nullable=False, unique=True)

    # Hijos
    percepciones_deducciones = relationship("PercepcionDeduccion", back_populates="persona")

    def __repr__(self):
        """Representación"""
        return f"<Persona {self.rfc}>"
