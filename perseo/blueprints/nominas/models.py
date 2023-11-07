"""
Nominas, modelos
"""
from sqlalchemy import Column, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from lib.universal_mixin import UniversalMixin
from perseo.extensions import database


class Nomina(database.Model, UniversalMixin):
    """Nomina"""

    TIPOS = {
        "SALARIO": "SALARIO",
        "DESPENSA": "DESPENSA",
    }

    # Nombre de la tabla
    __tablename__ = "nominas"

    # Clave primaria
    id = Column(Integer, primary_key=True)

    # Clave foránea
    centro_trabajo_id = Column(Integer, ForeignKey("centros_trabajos.id"), index=True, nullable=False)
    centro_trabajo = relationship("CentroTrabajo", back_populates="nominas")
    persona_id = Column(Integer, ForeignKey("personas.id"), index=True, nullable=False)
    persona = relationship("Persona", back_populates="nominas")
    plaza_id = Column(Integer, ForeignKey("plazas.id"), index=True, nullable=False)
    plaza = relationship("Plaza", back_populates="nominas")

    # Columnas
    quincena = Column(String(6), nullable=False)
    percepcion = Column(Numeric(precision=24, scale=4), nullable=False)
    deduccion = Column(Numeric(precision=24, scale=4), nullable=False)
    importe = Column(Numeric(precision=24, scale=4), nullable=False)
    tipo = Column(Enum(*TIPOS, name="tipo_nomina"), nullable=False)
    num_cheque = Column(String(24), nullable=False, default="", server_default="")

    # Hijos
    nominas_reportes = relationship("NominaReporte", back_populates="nomina")

    def __repr__(self):
        """Representación"""
        return f"<Nomina {self.id}>"
