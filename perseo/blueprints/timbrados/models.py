"""
Timbrados, modelos
"""

from sqlalchemy import Column, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
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
    tfd = Column(Text())  # XML del Timbre Fiscal Digital

    # Columnas con los datos del XML en cfdi:Emisor
    cfdi_emisor_rfc = Column(String(13))
    cfdi_emisor_nombre = Column(String(256))
    cfdi_emisor_regimen_fiscal = Column(String(8))

    # Columnas con los datos del XML en cfdi:Receptor
    cfdi_receptor_rfc = Column(String(13))
    cfdi_receptor_nombre = Column(String(256))

    # Columnas con los datos del XML en tfd:TimbreFiscalDigital
    tfd_version = Column(String(8))
    tfd_uuid = Column(String(64), unique=True, nullable=False, index=True)  # UUID debe ser único
    tfd_fecha_timbrado = Column(DateTime())
    tfd_sello_cfd = Column(String(512))
    tfd_num_cert_sat = Column(String(64))
    tfd_sello_sat = Column(String(512))

    # Columnas con los datos del XML en nomina12:Nomina
    nomina12_nomina_version = Column(String(8))
    nomina12_nomina_tipo_nomina = Column(String(8))
    nomina12_nomina_fecha_pago = Column(Date())
    nomina12_nomina_fecha_inicial_pago = Column(Date())
    nomina12_nomina_fecha_final_pago = Column(Date())
    nomina12_nomina_total_percepciones = Column(Numeric(precision=24, scale=4))
    nomina12_nomina_total_deducciones = Column(Numeric(precision=24, scale=4))
    nomina12_nomina_total_otros_pagos = Column(Numeric(precision=24, scale=4))

    # Columnas con los nombres de descarga de archivos y URLs
    archivo_pdf = Column(String(256), nullable=False, default="", server_default="")
    url_pdf = Column(String(512), nullable=False, default="", server_default="")
    archivo_xml = Column(String(256), nullable=False, default="", server_default="")
    url_xml = Column(String(512), nullable=False, default="", server_default="")

    def __repr__(self):
        """Representación"""
        return f"<Timbrado {self.id}>"
