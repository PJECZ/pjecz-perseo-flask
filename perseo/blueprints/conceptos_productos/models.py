"""
Conceptos-Productos, modelos
"""
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from lib.universal_mixin import UniversalMixin
from perseo.extensions import database


class ConceptoProducto(database.Model, UniversalMixin):
    """ConceptoProducto"""

    # Nombre de la tabla
    __tablename__ = "conceptos_productos"

    # Clave primaria
    id = Column(Integer, primary_key=True)

    # Clave foránea
    concepto_id = Column(Integer, ForeignKey("conceptos.id"), index=True, nullable=False)
    concepto = relationship("Concepto", back_populates="conceptos_productos")
    producto_id = Column(Integer, ForeignKey("productos.id"), index=True, nullable=False)
    producto = relationship("Productos", back_populates="conceptos_productos")

    # Columnas
    descripcion = Column(String(256), nullable=False)

    def __repr__(self):
        """Representación"""
        return f"<ConceptoProducto {self.id}>"
