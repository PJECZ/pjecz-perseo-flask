"""
Bancos, tareas en el fondo
"""
import logging

from lib.tasks import set_task_error, set_task_progress
from perseo.app import create_app
from perseo.blueprints.bancos.models import Banco
from perseo.extensions import database

bitacora = logging.getLogger(__name__)
bitacora.setLevel(logging.INFO)
formato = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")
empunadura = logging.FileHandler("bancos.log")
empunadura.setFormatter(formato)
bitacora.addHandler(empunadura)

app = create_app()
app.app_context().push()
database.app = app


def reiniciar_consecutivos_generados():
    """Reiniciar los consecutivos generados de cada banco con el consecutivo"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, "Reiniciando los consecutivos generados...")

    # Iniciar sesion con la base de datos para que la alimentacion sea rapida
    sesion = database.session

    # Consultar los bancos
    bancos = sesion.query(Banco).order_by(Banco.clave).filter_by(estatus="A").all()

    # Si no hay bancos, mostrar mensaje de error y salir
    if len(bancos) == 0:
        mensaje_error = "No hay bancos activos."
        set_task_error(mensaje_error)
        bitacora.error(mensaje_error)
        return mensaje_error

    # Igualar los consecutivos a los consecutivos_generado de los bancos
    bancos_actualizados = []
    for banco in bancos:
        if banco.consecutivo != banco.consecutivo_generado:
            antes = banco.consecutivo
            ahora = banco.consecutivo_generado
            banco.consecutivo = banco.consecutivo_generado
            sesion.add(banco)
            bancos_actualizados.append(f"{banco.nombre} ({antes} -> {ahora})")

    # Si no hubo actualizaciones, mostrar mensaje y salir
    if len(bancos_actualizados) == 0:
        mensaje = "No se hicieron actualizaciones."
        set_task_progress(100, mensaje)
        bitacora.info(mensaje)
        return mensaje

    # Hacer commit de los cambios en la base de datos
    sesion.commit()

    # Mensaje de termino
    bancos_actualizados_str = ", ".join(bancos_actualizados)
    mensaje = f"Reiniciados los consecutivos generados: {bancos_actualizados_str}"
    set_task_progress(100, mensaje)
    bitacora.info(mensaje)
    return mensaje
