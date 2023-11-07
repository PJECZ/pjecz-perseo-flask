"""
Nominas Reportes, modelos
"""
from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from lib.universal_mixin import UniversalMixin
from perseo.extensions import database


class NominaReporte(database.Model, UniversalMixin):
    """NominaReporte"""

    # Nombre de la tabla
    __tablename__ = "nominas_reportes"

    # Clave primaria
    id = Column(Integer, primary_key=True)

    # Clave foránea
    nomina_id = Column(Integer, ForeignKey("nominas.id"), index=True, nullable=False)
    nomina = relationship("Nomina", back_populates="nominas_reportes")

    # Columnas
    descripcion = Column(String(256), nullable=False)
    archivo = Column(String(256), nullable=False)
    url = Column(String(512), nullable=False)
    mensaje = Column(Text, nullable=False)

    def __repr__(self):
        """Representación"""
        return f"<NominaReporte {self.id}>"
