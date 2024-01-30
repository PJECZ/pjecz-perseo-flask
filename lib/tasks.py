"""
Tareas en el fondo
"""
from rq import get_current_job

from perseo.blueprints.tareas.models import Tarea


def set_task_progress(progress: int, message: str = None, archivo: str = "", url: str = "") -> None:
    """Cambiar el progreso de la tarea"""
    job = get_current_job()
    if job:
        job.meta["progress"] = progress
        job.save_meta()
        tarea = Tarea.query.get(job.get_id())
        if tarea:
            hay_cambios = False
            if archivo != "":
                tarea.archivo = archivo
                hay_cambios = True
            if url != "":
                tarea.url = url
                hay_cambios = True
            if progress >= 100:
                tarea.ha_terminado = True
                hay_cambios = True
            if message is not None:
                tarea.mensaje = message
                hay_cambios = True
            if hay_cambios:
                tarea.save()


def set_task_error(message: str) -> str:
    """Al fallar la tarea debe tomar el message y terminarla"""
    job = get_current_job()
    if job:
        job.meta["progress"] = 100
        job.save_meta()
        tarea = Tarea.query.get(job.get_id())
        if tarea:
            tarea.ha_terminado = True
            tarea.mensaje = message
            tarea.save()
    return message
