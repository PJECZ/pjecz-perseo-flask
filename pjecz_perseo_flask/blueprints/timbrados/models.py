"""
Timbrados, modelos
"""

from datetime import date, datetime
from decimal import Decimal, getcontext

from sqlalchemy import Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...config.extensions import database
from ...lib.universal_mixin import UniversalMixin

getcontext().prec = 4  # Cuatro decimales en los cálculos monetarios


class Timbrado(database.Model, UniversalMixin):
    """Timbrado"""

    ESTADOS = {
        "CANCELADO": "CANCELADO",
        "TIMBRADO": "TIMBRADO",
    }

    # Nombre de la tabla
    __tablename__ = "timbrados"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    nomina_id: Mapped[int] = mapped_column(Integer, ForeignKey("nominas.id"), index=True)
    nomina: Mapped["Nomina"] = relationship(back_populates="timbrados")

    # Columnas
    estado: Mapped[str] = mapped_column(Enum(*ESTADOS, name="timbrados_estados"), index=True)
    tfd: Mapped[str] = mapped_column(Text())  # XML del Timbre Fiscal Digital

    # Columnas con los datos del XML en cfdi:Emisor
    cfdi_emisor_rfc: Mapped[str] = mapped_column(String(13))
    cfdi_emisor_nombre: Mapped[str] = mapped_column(String(256))
    cfdi_emisor_regimen_fiscal: Mapped[str] = mapped_column(String(8))

    # Columnas con los datos del XML en cfdi:Receptor
    cfdi_receptor_rfc: Mapped[str] = mapped_column(String(13))
    cfdi_receptor_nombre: Mapped[str] = mapped_column(String(256))

    # Columnas con los datos del XML en tfd:TimbreFiscalDigital
    tfd_version: Mapped[str] = mapped_column(String(8))
    tfd_uuid: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # UUID debe ser único
    tfd_fecha_timbrado: Mapped[datetime]
    tfd_sello_cfd: Mapped[str] = mapped_column(String(512))
    tfd_num_cert_sat: Mapped[str] = mapped_column(String(64))
    tfd_sello_sat: Mapped[str] = mapped_column(String(512))

    # Columnas con los datos del XML en nomina12:Nomina
    nomina12_nomina_version: Mapped[str] = mapped_column(String(8))
    nomina12_nomina_tipo_nomina: Mapped[str] = mapped_column(String(8))
    nomina12_nomina_fecha_pago: Mapped[date]
    nomina12_nomina_fecha_inicial_pago: Mapped[date]
    nomina12_nomina_fecha_final_pago: Mapped[date]
    nomina12_nomina_total_percepciones: Mapped[Decimal] = mapped_column(Numeric(precision=24, scale=4))
    nomina12_nomina_total_deducciones: Mapped[Decimal] = mapped_column(Numeric(precision=24, scale=4))
    nomina12_nomina_total_otros_pagos: Mapped[Decimal] = mapped_column(Numeric(precision=24, scale=4))

    # Columnas con los nombres de descarga de archivos y URLs
    archivo_pdf: Mapped[str] = mapped_column(String(256), default="", server_default="")
    url_pdf: Mapped[str] = mapped_column(String(512), default="", server_default="")
    archivo_xml: Mapped[str] = mapped_column(String(256), default="", server_default="")
    url_xml: Mapped[str] = mapped_column(String(512), default="", server_default="")

    def __repr__(self):
        """Representación"""
        return f"<Timbrado {self.id}>"
