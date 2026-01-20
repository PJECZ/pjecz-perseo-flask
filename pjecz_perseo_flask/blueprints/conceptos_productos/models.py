"""
Conceptos-Productos, modelos
"""

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...config.extensions import database
from ...lib.universal_mixin import UniversalMixin


class ConceptoProducto(database.Model, UniversalMixin):
    """ConceptoProducto"""

    # Nombre de la tabla
    __tablename__ = "conceptos_productos"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    concepto_id: Mapped[int] = mapped_column(ForeignKey("conceptos.id"), index=True)
    concepto: Mapped["Concepto"] = relationship(back_populates="conceptos_productos")
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"), index=True)
    producto: Mapped["Producto"] = relationship(back_populates="conceptos_productos")

    # Columnas
    descripcion: Mapped[str] = mapped_column(String(256))

    def __repr__(self):
        """Representación"""
        return f"<ConceptoProducto {self.id}>"
