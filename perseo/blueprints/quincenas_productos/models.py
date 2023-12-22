"""
Quincenas Productos, modelos
"""
from sqlalchemy import Boolean, Column, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from lib.universal_mixin import UniversalMixin
from perseo.extensions import database


class QuincenaProducto(database.Model, UniversalMixin):
    """QuincenaProducto"""

    FUENTES = {
        "DISPERSIONES PENSIONADOS": "DISPERSIONES PENSIONADOS",
        "MONEDEROS": "MONEDEROS",
        "NOMINAS": "NOMINAS",
        "PENSIONADOS": "PENSIONADOS",
        "TIMBRADOS": "TIMBRADOS",
        "TIMBRADOS AGUINALDOS": "TIMBRADOS AGUINALDOS",
        "TIMBRADOS APOYOS ANUALES": "TIMBRADOS APOYOS ANUALES",
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
    es_satisfactorio = Column(Boolean, nullable=False)
    fuente = Column(Enum(*FUENTES, name="quincenas_productos_fuentes"), index=True, nullable=False)
    mensajes = Column(Text)
    url = Column(String(512), nullable=False)

    def __repr__(self):
        """Representación"""
        return f"<QuincenaProducto {self.id}>"
