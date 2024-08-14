"""
Personas, modelos
"""

from datetime import date
from typing import List

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lib.universal_mixin import UniversalMixin
from perseo.blueprints.centros_trabajos.models import CentroTrabajo
from perseo.blueprints.plazas.models import Plaza
from perseo.blueprints.puestos.models import Puesto
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
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    tabulador_id: Mapped[int] = mapped_column(ForeignKey("tabuladores.id"))
    tabulador: Mapped["Tabulador"] = relationship(back_populates="personas")

    # Columnas
    rfc: Mapped[str] = mapped_column(String(13), unique=True, index=True)
    nombres: Mapped[str] = mapped_column(String(256), index=True)
    apellido_primero: Mapped[str] = mapped_column(String(256), index=True)
    apellido_segundo: Mapped[str] = mapped_column(String(256), default="", server_default="")
    curp: Mapped[str] = mapped_column(String(18), default="", server_default="")
    num_empleado: Mapped[int]
    ingreso_gobierno_fecha: Mapped[date]
    ingreso_pj_fecha: Mapped[date]
    nacimiento_fecha: Mapped[date]
    codigo_postal_fiscal: Mapped[int] = mapped_column(Integer, default=0)
    seguridad_social: Mapped[str] = mapped_column(String(24))

    # Columna modelo es entero del 1 al 6
    modelo: Mapped[int] = mapped_column(Integer, index=True)

    # Columnas para mantener el ultimo centro_trabajo, plaza y puesto
    # que se actualizan cada vez que se alimiente una quincena
    ultimo_centro_trabajo_id: Mapped[int] = mapped_column(Integer, default=137)
    ultimo_plaza_id: Mapped[int] = mapped_column(Integer, default=2182)
    ultimo_puesto_id: Mapped[int] = mapped_column(Integer, default=135)

    # Columnas para sindicalizados
    sub_sis: Mapped[int] = mapped_column(Integer, default=0)
    nivel: Mapped[int] = mapped_column(Integer, default=0)
    puesto_equivalente: Mapped[str] = mapped_column(String(16), default="")

    # Columna es_activo que indica si la persona está activa o inactiva
    es_activo: Mapped[bool] = mapped_column(default=False)

    # Hijos
    cuentas: Mapped[List["Cuenta"]] = relationship("Cuenta", back_populates="persona")
    nominas: Mapped[List["Nomina"]] = relationship("Nomina", back_populates="persona")
    percepciones_deducciones: Mapped[List["PercepcionDeduccion"]] = relationship(
        "PercepcionDeduccion", back_populates="persona"
    )

    @property
    def nombre_completo(self):
        """Nombre completo"""
        return f"{self.nombres} {self.apellido_primero} {self.apellido_segundo}"

    def __repr__(self):
        """Representación"""
        return f"<Persona {self.rfc}>"
