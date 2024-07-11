"""
Quincenas Productos, modelos
"""

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lib.universal_mixin import UniversalMixin
from perseo.extensions import database


class QuincenaProducto(database.Model, UniversalMixin):
    """QuincenaProducto"""

    FUENTES = {
        "DISPERSIONES PENSIONADOS": "DISPERSIONES PENSIONADOS",
        "MONEDEROS": "MONEDEROS",
        "NOMINAS": "NOMINAS",
        "PENSIONADOS": "PENSIONADOS",
        "PRIMAS VACACIONALES": "PRIMAS VACACIONALES",
        "TIMBRADOS": "TIMBRADOS",
        "TIMBRADOS EMPLEADOS ACTIVOS": "TIMBRADOS EMPLEADOS ACTIVOS",
        "TIMBRADOS PENSIONADOS": "TIMBRADOS PENSIONADOS",
        "TIMBRADOS AGUINALDOS": "TIMBRADOS AGUINALDOS",
        "TIMBRADOS APOYOS ANUALES": "TIMBRADOS APOYOS ANUALES",
    }

    # Nombre de la tabla
    __tablename__ = "quincenas_productos"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    quincena_id: Mapped[int] = mapped_column(ForeignKey("quincenas.id"), index=True)
    quincena: Mapped["Quincena"] = relationship(back_populates="quincenas_productos")

    # Columnas
    archivo: Mapped[str] = mapped_column(String(256), default="", server_default="")
    es_satisfactorio: Mapped[bool] = mapped_column(Boolean, default=False)
    fuente: Mapped[str] = mapped_column(Enum(*FUENTES, name="quincenas_productos_fuentes"), index=True)
    mensajes: Mapped[str] = mapped_column(Text, default="", server_default="")
    url: Mapped[str] = mapped_column(String(512), default="", server_default="")

    def __repr__(self):
        """Representación"""
        return f"<QuincenaProducto {self.id}>"
