"""
Personas, modelos
"""
from sqlalchemy import Column, Date, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from lib.universal_mixin import UniversalMixin
from perseo.extensions import database


class Persona(database.Model, UniversalMixin):
    """Persona"""

    # Nombre de la tabla
    __tablename__ = "personas"

    # Clave primaria
    id = Column(Integer, primary_key=True)

    # Clave foránea
    tabulador_id = Column(Integer, ForeignKey("tabuladores.id"), index=True, nullable=False)
    tabulador = relationship("Tabulador", back_populates="personas")

    # Columnas
    rfc = Column(String(13), nullable=False, unique=True)
    nombres = Column(String(256), nullable=False, index=True)
    apellido_primero = Column(String(256), nullable=False, index=True)
    apellido_segundo = Column(String(256), nullable=False, default="", server_default="")
    curp = Column(String(18), nullable=False, default="", server_default="")
    modelo = Column(Integer, nullable=False, default=0, index=True)  # 1: Empleado, 2: Sindicato, 3: Jubilado, 4: Beneficiario
    num_empleado = Column(Integer, nullable=False, default=0)
    ingreso_gobierno_fecha = Column(Date)
    ingreso_pj_fecha = Column(Date)
    nacimiento_fecha = Column(Date)
    codigo_postal_fiscal = Column(Integer)
    seguridad_social = Column(String(24))

    # Hijos
    cuentas = relationship("Cuenta", back_populates="persona")
    nominas = relationship("Nomina", back_populates="persona")
    percepciones_deducciones = relationship("PercepcionDeduccion", back_populates="persona")
    # puestos_historiales = relationship("PuestoHistorial", back_populates="persona")

    @property
    def nombre_completo(self):
        """Nombre completo"""
        return f"{self.nombres} {self.apellido_primero} {self.apellido_segundo}"

    def __repr__(self):
        """Representación"""
        return f"<Persona {self.rfc}>"
