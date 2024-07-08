"""
Entradas-Salidas
"""

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lib.universal_mixin import UniversalMixin
from perseo.extensions import database


class EntradaSalida(database.Model, UniversalMixin):
    """Entrada-Salida"""

    TIPOS = {
        "INGRESO": "Ingresó",
        "SALIO": "Salió",
    }

    # Nombre de la tabla
    __tablename__ = "entradas_salidas"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Claves foráneas
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    usuario: Mapped["Usuario"] = relationship(back_populates="entradas_salidas")

    # Columnas
    tipo: Mapped[str] = mapped_column(Enum(*TIPOS, name="entradas_salidas_tipos"), index=True)
    direccion_ip: Mapped[str] = mapped_column(String(64))

    def __repr__(self):
        """Representación"""
        return f"<EntradaSalida {self.id}>"
