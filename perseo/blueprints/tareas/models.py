"""
Tareas, modelos
"""
import redis
import rq
from flask import current_app
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from lib.universal_mixin import UniversalMixin
from perseo.extensions import database


class Tarea(database.Model, UniversalMixin):
    """Tarea"""

    # Nombre de la tabla
    __tablename__ = "tareas"

    # Clave primaria NOTA: El id es string y es el mismo que usa el RQ worker
    id = Column(String(36), primary_key=True)

    # Clave foránea
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), index=True, nullable=False)
    usuario = relationship("Usuario", back_populates="tareas")

    # Columnas
    comando = Column(String(256), nullable=False, index=True)
    mensaje = Column(String(1024), default="", server_default="")
    ha_terminado = Column(Boolean, nullable=False, default=False)

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
