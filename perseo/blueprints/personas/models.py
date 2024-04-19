"""
Personas, modelos
"""

from sqlalchemy import Column, Date, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from lib.universal_mixin import UniversalMixin
from perseo.extensions import database


class Persona(database.Model, UniversalMixin):
    """Persona"""

    MODELOS = {
        1: "CONFIANZA",
        2: "SINDICALIZADO",
        3: "PENSIONADO",
        4: "BENEFICIARIO PENSION ALIMENTICIA",
        5: "ASIMILADO A SALARIOS",
        6: "EXTRAORDINARIO",
    }

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
    apellido_segundo = Column(String(256), nullable=False, default="")
    curp = Column(String(18), nullable=False, default="")
    num_empleado = Column(Integer)
    ingreso_gobierno_fecha = Column(Date)
    ingreso_pj_fecha = Column(Date)
    nacimiento_fecha = Column(Date)
    codigo_postal_fiscal = Column(Integer, nullable=False, default=0)
    seguridad_social = Column(String(24))

    # Columna modelo es entero del 1 al 6
    modelo = Column(Integer, nullable=False, index=True)

    # Columnas para mantener el ultimo centro_trabajo, plaza y puesto que se actualizan cada vez que se alimiente una quincena
    ultimo_centro_trabajo_id = Column(Integer, nullable=False, default=137)  # 137 es ND
    ultimo_plaza_id = Column(Integer, nullable=False, default=2182)  # 2182 es ND
    ultimo_puesto_id = Column(Integer, nullable=False, default=135)  # 135 es ND

    # Columnas nuevas
    sub_sis = Column(Integer, nullable=False, default=0)
    nivel = Column(Integer, nullable=False, default=0)
    puesto_equivalente = Column(String(16), nullable=False, default="")

    # Hijos
    cuentas = relationship("Cuenta", back_populates="persona")  # Sin lazy="noload" para elaborar el timbrado
    nominas = relationship("Nomina", back_populates="persona", lazy="noload")
    percepciones_deducciones = relationship("PercepcionDeduccion", back_populates="persona", lazy="noload")

    @property
    def nombre_completo(self):
        """Nombre completo"""
        return f"{self.nombres} {self.apellido_primero} {self.apellido_segundo}"

    def __repr__(self):
        """Representación"""
        return f"<Persona {self.rfc}>"
