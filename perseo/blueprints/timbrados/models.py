"""
Timbrados, modelos
"""
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from lib.universal_mixin import UniversalMixin
from perseo.extensions import database


class Timbrado(database.Model, UniversalMixin):
    """Timbrado"""

    ESTADOS = {
        "CANCELADO": "CANCELADO",
        "TIMBRADO": "TIMBRADO",
    }

    # Nombre de la tabla
    __tablename__ = "timbrados"

    # Clave primaria
    id = Column(Integer, primary_key=True)

    # Clave foránea
    nomina_id = Column(Integer, ForeignKey("nominas.id"), index=True, nullable=False)
    nomina = relationship("Nomina", back_populates="timbrados")

    # Columnas
    estado = Column(Enum(*ESTADOS, name="timbrados_estados"), nullable=False, index=True)
    tfd = Column(Text())
    tfd_version = Column(String(8), nullable=False)
    tfd_uuid = Column(String(64), unique=True, nullable=False, index=True)
    tfd_fecha_timbrado = Column(DateTime(), nullable=False)
    tfd_sello_cfd = Column(String(512), nullable=False)
    tfd_num_cert_sat = Column(String(64), nullable=False)
    tfd_sello_sat = Column(String(512), nullable=False)

    # Columnas con los nombres de descarga de archivos y URLs
    archivo_pdf = Column(String(256), nullable=False, default="", server_default="")
    url_pdf = Column(String(512), nullable=False, default="", server_default="")
    archivo_xml = Column(String(256), nullable=False, default="", server_default="")
    url_xml = Column(String(512), nullable=False, default="", server_default="")

    def __repr__(self):
        """Representación"""
        return f"<Timbrado {self.id}>"
