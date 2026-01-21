"""
Bancos, tareas en el fondo
"""

import logging

from pjecz_perseo_flask.blueprints.bancos.models import Banco
from pjecz_perseo_flask.config.extensions import database
from pjecz_perseo_flask.lib.exceptions import MyAnyError, MyNotExistsError
from pjecz_perseo_flask.lib.tasks import set_task_error, set_task_progress
from pjecz_perseo_flask.main import app

bitacora = logging.getLogger(__name__)
bitacora.setLevel(logging.INFO)
formato = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")
empunadura = logging.FileHandler("logs/bancos.log")
empunadura.setFormatter(formato)
bitacora.addHandler(empunadura)

# Inicializar el contexto de la aplicación Flask
app.app_context().push()


def reiniciar_consecutivos_generados():
    """Reiniciar los consecutivos generados de cada banco con el consecutivo"""

    # Iniciar sesion con la base de datos para que la alimentacion sea rapida
    sesion = database.session

    # Consultar los bancos
    bancos = sesion.query(Banco).order_by(Banco.clave).filter_by(estatus="A").all()

    # Si no hay bancos, mostrar mensaje de error y salir
    if len(bancos) == 0:
        raise MyNotExistsError("No hay bancos activos.")

    # Igualar los consecutivos a los consecutivos_generado de los bancos
    bancos_actualizados = []
    for banco in bancos:
        if banco.consecutivo != banco.consecutivo_generado:
            valor_anterior = banco.consecutivo_generado
            valor_nuevo = banco.consecutivo
            banco.consecutivo_generado = valor_nuevo
            sesion.add(banco)
            bancos_actualizados.append(f"{banco.nombre} {valor_anterior} -> {valor_nuevo}")

    # Si no hubo actualizaciones, mostrar mensaje y salir
    if len(bancos_actualizados) == 0:
        return "No se hicieron actualizaciones."

    # Hacer commit de los cambios en la base de datos
    sesion.commit()

    # Entregar mensaje de termino
    return f"Reiniciar Consecutivos Generados: {len(bancos_actualizados)} cambios en {' ,'.join(bancos_actualizados)}"


def lanzar_reiniciar_consecutivos_generados():
    """Reiniciar los consecutivos generados de cada banco con el consecutivo"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, "Reiniciando los consecutivos generados...")

    # Reiniciar los consecutivos generados
    try:
        mensaje_termino = reiniciar_consecutivos_generados()
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        bitacora.error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo y entregar el mensaje de termino
    set_task_progress(100, mensaje_termino)
    bitacora.info(mensaje_termino)
    return mensaje_termino
