"""
Percepciones Deducciones, modelos
"""

from sqlalchemy import Column, Enum, ForeignKey, Integer, Numeric
from sqlalchemy.orm import relationship

from lib.universal_mixin import UniversalMixin
from perseo.extensions import database


class PercepcionDeduccion(database.Model, UniversalMixin):
    """PercepcionDeduccion"""

    TIPOS = {
        "AGUINALDO": "AGUINALDO",
        "APOYO ANUAL": "APOYO ANUAL",
        "DESPENSA": "DESPENSA",
        "SALARIO": "SALARIO",
        "EXTRAORDINARIO": "EXTRAORDINARIO",
    }

    # Nombre de la tabla
    __tablename__ = "percepciones_deducciones"

    # Clave primaria
    id = Column(Integer, primary_key=True)

    # Claves foráneas
    centro_trabajo_id = Column(Integer, ForeignKey("centros_trabajos.id"), index=True, nullable=False)
    centro_trabajo = relationship("CentroTrabajo", back_populates="percepciones_deducciones")
    concepto_id = Column(Integer, ForeignKey("conceptos.id"), index=True, nullable=False)
    concepto = relationship("Concepto", back_populates="percepciones_deducciones")
    persona_id = Column(Integer, ForeignKey("personas.id"), index=True, nullable=False)
    persona = relationship("Persona", back_populates="percepciones_deducciones")
    plaza_id = Column(Integer, ForeignKey("plazas.id"), index=True, nullable=False)
    plaza = relationship("Plaza", back_populates="percepciones_deducciones")
    quincena_id = Column(Integer, ForeignKey("quincenas.id"), index=True, nullable=False)
    quincena = relationship("Quincena", back_populates="percepciones_deducciones")

    # Columnas
    tipo = Column(Enum(*TIPOS, name="percepciones_deducciones_tipos"), nullable=False, index=True)
    importe = Column(Numeric(precision=24, scale=4), nullable=False)

    def __repr__(self):
        """Representación"""
        return f"<PercepcionDeduccion {self.id}>"
