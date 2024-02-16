"""
Conceptos, modelos
"""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from lib.universal_mixin import UniversalMixin
from perseo.extensions import database


class Concepto(database.Model, UniversalMixin):
    """Concepto"""

    # Nombre de la tabla
    __tablename__ = "conceptos"

    # Clave primaria
    id = Column(Integer, primary_key=True)

    # Columnas
    clave = Column(String(16), unique=True, nullable=False)
    descripcion = Column(String(256), nullable=False)

    # Hijos
    conceptos_productos = relationship("ConceptoProducto", back_populates="concepto", lazy="noload")
    percepciones_deducciones = relationship("PercepcionDeduccion", back_populates="concepto", lazy="noload")

    def __repr__(self):
        """Representación"""
        return f"<Concepto {self.clave}>"
