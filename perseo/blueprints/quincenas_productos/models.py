"""
Quincenas Productos, modelos
"""
from sqlalchemy import Column, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from lib.universal_mixin import UniversalMixin
from perseo.extensions import database


class QuincenaProducto(database.Model, UniversalMixin):
    """QuincenaProducto"""

    FUENTES = {
        "NOMINAS": "NOMINAS",
        "MONEDEROS": "MONEDEROS",
        "PENSIONADOS": "PENSIONADOS",
        "DIPSERSIONES PENSIONADOS": "DIPSERSIONES PENSIONADOS",
    }

    # Nombre de la tabla
    __tablename__ = "quincenas_productos"

    # Clave primaria
    id = Column(Integer, primary_key=True)

    # Clave foránea
    quincena_id = Column(Integer, ForeignKey("quincenas.id"), index=True, nullable=False)
    quincena = relationship("Quincena", back_populates="quincenas_productos")

    # Columnas
    archivo = Column(String(256), nullable=False)
    fuente = Column(Enum(*FUENTES, name="quincenas_productos_fuentes"), nullable=False)
    mensajes = Column(Text)
    url = Column(String(512), nullable=False)

    def __repr__(self):
        """Representación"""
        return f"<QuincenaProducto {self.id}>"
