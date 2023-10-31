"""
Quincenas Productos, modelos
"""
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from lib.universal_mixin import UniversalMixin
from perseo.extensions import database


class QuincenaProducto(database.Model, UniversalMixin):
    """QuincenaProducto"""

    # Nombre de la tabla
    __tablename__ = "quincenas_productos"

    # Clave primaria
    id = Column(Integer, primary_key=True)

    # Clave foránea
    quincena_id = Column(Integer, ForeignKey("quincenas.id"), index=True, nullable=False)
    quincena = relationship("Quincena", back_populates="quincenas_productos")

    # Columnas
    archivo = Column(String(256), nullable=False)
    url = Column(String(512), nullable=False)
    tiene_errores = Column(Boolean, nullable=False, default=False)
    mensajes = Column(Text)

    def __repr__(self):
        """Representación"""
        return f"<QuincenaProducto {self.id}>"
