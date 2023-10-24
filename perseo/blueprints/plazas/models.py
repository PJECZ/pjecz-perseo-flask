"""
Plazas, modelos
"""
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from lib.universal_mixin import UniversalMixin
from perseo.extensions import database


class Plaza(database.Model, UniversalMixin):
    """Plaza"""

    # Nombre de la tabla
    __tablename__ = "plazas"

    # Clave primaria
    id = Column(Integer, primary_key=True)

    # Columnas
    clave = Column(String(16), unique=True, nullable=False)
    descripcion = Column(String(256), nullable=False)

    # Hijos
    percepciones_deducciones = relationship("PercepcionDeduccion", back_populates="plaza")

    def __repr__(self):
        """Representación"""
        return f"<Plaza {self.clave}>"
