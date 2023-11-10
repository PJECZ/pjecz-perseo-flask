"""
Cuentas, modelos
"""
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from lib.universal_mixin import UniversalMixin
from perseo.extensions import database


class Cuenta(database.Model, UniversalMixin):
    """Cuenta"""

    # Nombre de la tabla
    __tablename__ = "cuentas"

    # Clave primaria
    id = Column(Integer, primary_key=True)

    # Claves foráneas
    banco_id = Column(Integer, ForeignKey("bancos.id"), index=True, nullable=False)
    banco = relationship("Banco", back_populates="cuentas")
    persona_id = Column(Integer, ForeignKey("personas.id"), index=True, nullable=False)
    persona = relationship("Persona", back_populates="cuentas")

    # Columnas
    num_cuenta = Column(String(24), nullable=False)

    def __repr__(self):
        """Representación"""
        return f"<Cuenta {self.id}>"
