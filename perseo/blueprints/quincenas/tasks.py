"""
Quincenas, tareas en el fondo
"""
import logging

from lib.tasks import set_task_error, set_task_progress
from perseo.app import create_app
from perseo.blueprints.bancos.models import Banco
from perseo.blueprints.quincenas.models import Quincena
from perseo.extensions import database

GCS_BASE_DIRECTORY = "reports/quincenas"
LOCAL_BASE_DIRECTORY = "reports/quincenas"
TIMEZONE = "America/Mexico_City"

bitacora = logging.getLogger(__name__)
bitacora.setLevel(logging.INFO)
formato = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")
empunadura = logging.FileHandler("quincenas.log")
empunadura.setFormatter(formato)
bitacora.addHandler(empunadura)

app = create_app()
app.app_context().push()
database.app = app


def cerrar() -> str:
    """Cerrar TODAS las quincenas con estado ABIERTA"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, "Cerrando quincenas...")

    # Iniciar sesion con la base de datos para que la alimentacion sea rapida
    sesion = database.session

    # Consultar todas las quincenas con estatus "A"
    quincenas = sesion.query(Quincena).order_by(Quincena.clave).filter_by(estatus="A").all()

    # Si no hay quincenas, mostrar mensaje de error y salir
    if len(quincenas) == 0:
        mensaje_error = "No hay quincenas activas."
        set_task_error(mensaje_error)
        bitacora.error(mensaje_error)
        return mensaje_error

    # Bucle por las quincenas
    quincenas_cerradas = []
    for quincena in quincenas:
        # Si la quincena esta abierta, cerrarla
        if quincena.estado == "ABIERTA":
            quincena.estado = "CERRADA"
            sesion.add(quincena)
            quincenas_cerradas.append(quincena.clave)

    # Si no hubo cambios, mostrar mensaje y salir
    if len(quincenas_cerradas) == 0:
        mensaje = "No se hicieron cambios."
        set_task_progress(100, mensaje)
        bitacora.info(mensaje)
        return mensaje

    # Igualar los consecutivos a los consecutivos_generado de los bancos
    bancos_actualizados = []
    for banco in Banco.query.filter_by(estatus="A").all():
        if banco.consecutivo != banco.consecutivo_generado:
            antes = banco.consecutivo
            ahora = banco.consecutivo_generado
            banco.consecutivo = banco.consecutivo_generado
            sesion.add(banco)
            bancos_actualizados.append(f"{banco.nombre} ({antes} -> {ahora})")

    # TODO: Actualizar en cada registro de nominas el numero de cheque

    # Hacer commit de los cambios en la base de datos
    sesion.commit()

    # Definir el mensaje con las quincenas cerradas
    quincenas_cerradas_str = ", ".join(quincenas_cerradas)

    # Definir el mensaje con los bancos actualizados
    bancos_actualizados_str = ""
    if len(bancos_actualizados) > 0:
        bancos_actualizados_str = ", ".join(bancos_actualizados)

    # Mensaje de termino
    mensaje = f"Quincenas cerradas: {quincenas_cerradas_str}. Bancos actualizados {bancos_actualizados_str}"
    set_task_progress(100, mensaje)
    bitacora.info(mensaje)
    return mensaje
