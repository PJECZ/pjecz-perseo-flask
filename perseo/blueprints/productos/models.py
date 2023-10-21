"""
Productos, modelos
"""
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from lib.universal_mixin import UniversalMixin
from perseo.extensions import database


class Producto(database.Model, UniversalMixin):
    """Producto"""

    # Nombre de la tabla
    __tablename__ = "productos"

    # Clave primaria
    id = Column(Integer, primary_key=True)

    # Columnas
    clave = Column(String(16), unique=True, nullable=False)
    descripcion = Column(String(256), nullable=False)

    # Hijos
    conceptos_productos = relationship("ConceptoProducto", back_populates="producto")

    def __repr__(self):
        """Representación"""
        return f"<Producto {self.clave}>"
