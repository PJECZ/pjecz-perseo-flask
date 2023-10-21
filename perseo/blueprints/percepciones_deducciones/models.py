"""
Deducciones Percepciones, modelos
"""
from sqlalchemy import Column, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from lib.universal_mixin import UniversalMixin
from perseo.extensions import database


class PercepcionDeduccion(database.Model, UniversalMixin):
    """PercepcionDeduccion"""

    # Nombre de la tabla
    __tablename__ = "percepciones_deducciones"

    # Clave primaria
    id = Column(Integer, primary_key=True)

    # Clave foránea
    persona_id = Column(Integer, ForeignKey("personas.id"), index=True, nullable=False)
    persona = relationship("Persona", back_populates="percepciones_deducciones")

    # Columnas
    quincena = Column(String(6), nullable=False)
    importe = Column(Numeric(precision=24, scale=4), nullable=False)

    def __repr__(self):
        """Representación"""
        return f"<PercepcionDeduccion {self.id}>"
