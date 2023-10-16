"""
Entradas-Salidas
"""
from collections import OrderedDict

from sqlalchemy import Column, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from perseo.extensions import database
from lib.universal_mixin import UniversalMixin


class EntradaSalida(database.Model, UniversalMixin):
    """Entrada-Salida"""

    TIPOS = OrderedDict(
        [
            ("INGRESO", "Ingresó"),
            ("SALIO", "Salió"),
        ]
    )

    # Nombre de la tabla
    __tablename__ = "entradas_salidas"

    # Clave primaria
    id = Column(Integer, primary_key=True)

    # Claves foráneas
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), index=True, nullable=False)
    usuario = relationship("Usuario", back_populates="entradas_salidas")

    # Columnas
    tipo = Column(Enum(*TIPOS, name="tipos_entradas_salidas", native_enum=False), index=True, nullable=False)
    direccion_ip = Column(String(64), nullable=False)

    def __repr__(self):
        """Representación"""
        return f"<EntradaSalida {self.id}>"
