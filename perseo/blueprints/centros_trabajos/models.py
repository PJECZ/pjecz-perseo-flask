"""
Centros de Trabajo, modelos
"""
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from lib.universal_mixin import UniversalMixin
from perseo.extensions import database


class CentroTrabajo(database.Model, UniversalMixin):
    """CentroTrabajo"""

    # Nombre de la tabla
    __tablename__ = "centros_trabajos"

    # Clave primaria
    id = Column(Integer, primary_key=True)

    # Columnas
    clave = Column(String(16), unique=True, nullable=False)
    descripcion = Column(String(256), nullable=False)

    # Hijos
    percepciones_deducciones = relationship("PercepcionDeduccion", back_populates="centro_trabajo")

    def __repr__(self):
        """Representación"""
        return f"<CentroTrabajo {self.clave}>"
