"""
Universal Mixin
"""

from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.functions import now
from sqlalchemy.types import CHAR

from ..config.extensions import database


class UniversalMixin:
    """Columnas y metodos universales"""

    creado: Mapped[datetime] = mapped_column(default=now(), server_default=now())
    modificado: Mapped[datetime] = mapped_column(default=now(), onupdate=now(), server_default=now())
    estatus: Mapped[str] = mapped_column(CHAR, default="A", server_default="A")

    def delete(self):
        """Eliminar registro"""
        # Borrado lógico: Cambiar a estatus B de Borrado
        if self.estatus == "A":
            self.estatus = "B"
            return self.save()
        return None

    def recover(self):
        """Recuperar registro"""
        if self.estatus == "B":
            self.estatus = "A"
            return self.save()
        return None

    def save(self):
        """Guardar registro"""
        database.session.add(self)
        database.session.commit()
        return self
