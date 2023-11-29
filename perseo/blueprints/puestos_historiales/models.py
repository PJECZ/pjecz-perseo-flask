"""
Puestos Historiales, modelos
"""
from sqlalchemy import Column, Date, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from lib.universal_mixin import UniversalMixin
from perseo.extensions import database


class PuestoHistorial(database.Model, UniversalMixin):
    """PuestoHistorial"""

    # Nombre de la tabla
    __tablename__ = "puestos_historiales"

    # Clave primaria
    id = Column(Integer, primary_key=True)

    # Claves foráneas
    # personas_id = Column(Integer, ForeignKey("personas.id"), index=True, nullable=False)
    # personas = relationship("Persona", back_populates="puestos_historiales")
    # puesto_id = Column(Integer, ForeignKey("puestos.id"), index=True, nullable=False)
    # puesto = relationship("Puesto", back_populates="puestos_historiales")

    # Columnas
    desde = Column(Date, nullable=False)
    hasta = Column(Date)
    descripcion = Column(String(256), nullable=False)

    def __repr__(self):
        """Representación"""
        return f"<PuestoHistorial {self.id}>"
