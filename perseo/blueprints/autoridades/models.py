"""
Autoridad
"""
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from lib.universal_mixin import UniversalMixin
from perseo.extensions import database


class Autoridad(database.Model, UniversalMixin):
    """Autoridad"""

    # Nombre de la tabla
    __tablename__ = "autoridades"

    # Clave primaria
    id = Column(Integer, primary_key=True)

    # Claves foráneas
    distrito_id = Column(Integer, ForeignKey("distritos.id"), index=True, nullable=False)
    distrito = relationship("Distrito", back_populates="autoridades")

    # Columnas
    clave = Column(String(16), nullable=False, unique=True)
    descripcion = Column(String(256), nullable=False)
    descripcion_corta = Column(String(64), nullable=False)
    es_extinto = Column(Boolean, nullable=False, default=False)

    # Hijos
    usuarios = relationship("Usuario", back_populates="autoridad")

    def __repr__(self):
        """Representación"""
        return f"<Autoridad {self.clave}>"
