"""
Nominas, modelos
"""

from sqlalchemy import Column, Date, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from lib.universal_mixin import UniversalMixin
from perseo.extensions import database


class Nomina(database.Model, UniversalMixin):
    """Nomina"""

    TIPOS = {
        "AGUINALDO": "AGUINALDO",
        "APOYO ANUAL": "APOYO ANUAL",
        "DESPENSA": "DESPENSA",
        "SALARIO": "SALARIO",
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
    quincena_id = Column(Integer, ForeignKey("quincenas.id"), index=True, nullable=False)
    quincena = relationship("Quincena", back_populates="nominas")

    # Columnas
    tipo = Column(Enum(*TIPOS, name="nominas_tipos"), nullable=False, index=True)
    desde = Column(Date(), nullable=False)
    desde_clave = Column(String(6), nullable=False)
    hasta = Column(Date(), nullable=False)
    hasta_clave = Column(String(6), nullable=False)
    percepcion = Column(Numeric(precision=24, scale=4), nullable=False)
    deduccion = Column(Numeric(precision=24, scale=4), nullable=False)
    importe = Column(Numeric(precision=24, scale=4), nullable=False)
    num_cheque = Column(String(24), nullable=False, default="", server_default="")
    fecha_pago = Column(Date(), nullable=False)
    timbrado_id = Column(Integer())  # Pueder ser nulo o el ID del Timbrado

    # Hijos
    timbrados = relationship("Timbrado", back_populates="nomina", lazy="noload")

    def __repr__(self):
        """Representación"""
        return f"<Nomina {self.id}>"
