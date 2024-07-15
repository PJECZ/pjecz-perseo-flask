"""
Cuentas, modelos
"""

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lib.universal_mixin import UniversalMixin
from perseo.extensions import database


class Cuenta(database.Model, UniversalMixin):
    """Cuenta"""

    # Nombre de la tabla
    __tablename__ = "cuentas"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Claves foráneas
    banco_id: Mapped[int] = mapped_column(ForeignKey("bancos.id"), index=True)
    banco: Mapped["Banco"] = relationship(back_populates="cuentas")
    persona_id: Mapped[int] = mapped_column(ForeignKey("personas.id"), index=True)
    persona: Mapped["Persona"] = relationship(back_populates="cuentas")

    # Columnas
    num_cuenta: Mapped[str] = mapped_column(String(24))

    def __repr__(self):
        """Representación"""
        return f"<Cuenta {self.id}>"
