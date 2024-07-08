"""
Tareas, modelos
"""

import redis
import rq
from flask import current_app
from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lib.universal_mixin import UniversalMixin
from perseo.extensions import database


class Tarea(database.Model, UniversalMixin):
    """Tarea"""

    # Nombre de la tabla
    __tablename__ = "tareas"

    # Clave primaria NOTA: El id es string y es el mismo que usa el RQ worker
    id: Mapped[str] = mapped_column(Uuid, primary_key=True)

    # Clave foránea
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    usuario: Mapped["Usuario"] = relationship("Usuario", back_populates="tareas")

    # Columnas
    archivo: Mapped[str] = mapped_column(String(256))
    comando: Mapped[str] = mapped_column(String(256), index=True)
    ha_terminado: Mapped[bool] = mapped_column(default=False)
    mensaje: Mapped[str] = mapped_column(String(1024))
    url: Mapped[str] = mapped_column(String(512))

    def get_rq_job(self):
        """Helper method that loads the RQ Job instance"""
        try:
            rq_job = rq.job.Job.fetch(self.id, connection=current_app.redis)
        except (redis.exceptions.RedisError, rq.exceptions.NoSuchJobError):
            return None
        return rq_job

    def get_progress(self):
        """Returns the progress percentage for the task"""
        job = self.get_rq_job()
        return job.meta.get("progress", 0) if job is not None else 100

    def __repr__(self):
        """Representación"""
        return f"<Tarea {self.id}>"
