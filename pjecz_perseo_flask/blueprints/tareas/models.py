"""
Tareas, modelos
"""

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...config.extensions import database
from ...lib.universal_mixin import UniversalMixin


class Tarea(database.Model, UniversalMixin):
    """Tarea"""

    # Nombre de la tabla
    __tablename__ = "tareas"

    # Clave primaria
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Clave foránea
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    usuario: Mapped["Usuario"] = relationship(back_populates="tareas")

    # Columnas
    archivo: Mapped[str] = mapped_column(String(256), default="")
    comando: Mapped[str] = mapped_column(String(256), index=True)
    ha_terminado: Mapped[bool] = mapped_column(default=False)
    mensaje: Mapped[str] = mapped_column(String(1024))
    url: Mapped[str] = mapped_column(String(512), default="")

    def __repr__(self):
        """Representación"""
        return f"<Tarea {self.id}>"
