"""
Universal Mixin
"""
from hashids import Hashids
from sqlalchemy import Column, DateTime, String
from sqlalchemy.sql import func

from config.settings import get_settings
from perseo.extensions import database

settings = get_settings()
hashids = Hashids(salt=settings.SALT, min_length=8)


class UniversalMixin:
    """Columnas y metodos universales"""

    creado = Column(DateTime, default=func.now(), nullable=False)
    modificado = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    estatus = Column(String(1), default="A", nullable=False)

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

    def encode_id(self) -> str:
        """Encode id"""
        return hashids.encode(self.id)

    @classmethod
    def decode_id(cls, id_encoded: str) -> int:
        """Decode id"""
        return hashids.decode(id_encoded)[0]
