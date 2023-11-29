"""
Nominas, tareas en el fondo
"""
from lib.exceptions import MyAnyError
from lib.tasks import set_task_error, set_task_progress
from perseo.blueprints.bancos.tasks import reiniciar_consecutivos_generados
from perseo.blueprints.nominas.generators.common import bitacora
from perseo.blueprints.nominas.generators.dispersiones_pensionados import crear_dispersiones_pensionados
from perseo.blueprints.nominas.generators.monederos import crear_monederos
from perseo.blueprints.nominas.generators.nominas import crear_nominas
from perseo.blueprints.nominas.generators.pensionados import crear_pensionados
from perseo.blueprints.nominas.generators.timbrados import crear_timbrados


def generar_nominas(quincena_clave: str, quincena_producto_id: int) -> str:
    """Tarea en el fondo para crear un archivo XLSX con las nominas de una quincena"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, f"Generar archivo XLSX con las nominas de {quincena_clave}...")

    # Ejecutar el creador
    try:
        mensaje_termino = crear_nominas(quincena_clave, quincena_producto_id)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        bitacora.error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo y entregar el mensaje de termino
    set_task_progress(100, mensaje_termino)
    bitacora.info(mensaje_termino)
    return mensaje_termino


def generar_monederos(quincena_clave: str, quincena_producto_id: int) -> str:
    """Tarea en el fondo para crear un archivo XLSX con los monederos de una quincena"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, f"Generar archivo XLSX con los monederos de {quincena_clave}...")

    # Ejecutar el creador
    try:
        mensaje_termino = crear_monederos(quincena_clave, quincena_producto_id)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        bitacora.error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo y entregar el mensaje de termino
    set_task_progress(100, mensaje_termino)
    bitacora.info(mensaje_termino)
    return mensaje_termino


def generar_pensionados(quincena_clave: str, quincena_producto_id: int) -> str:
    """Tarea en el fondo para crear un archivo XLSX con los pensionados de una quincena"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, f"Generar archivo XLSX con los pensionados de {quincena_clave}...")

    # Ejecutar el creador
    try:
        mensaje_termino = crear_pensionados(quincena_clave, quincena_producto_id)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        bitacora.error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo y entregar el mensaje de termino
    set_task_progress(100, mensaje_termino)
    bitacora.info(mensaje_termino)
    return mensaje_termino


def generar_dispersiones_pensionados(quincena_clave: str, quincena_producto_id: int) -> str:
    """Tarea en el fondo para crear un archivo XLSX con las dispersiones pensionados de una quincena"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, f"Generar archivo XLSX con las dispersiones pensionados de {quincena_clave}...")

    # Ejecutar el creador
    try:
        mensaje_termino = crear_dispersiones_pensionados(quincena_clave, quincena_producto_id)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        bitacora.error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo y entregar el mensaje de termino
    set_task_progress(100, mensaje_termino)
    bitacora.info(mensaje_termino)
    return mensaje_termino


def generar_timbrados(quincena_clave: str, quincena_producto_id: int) -> str:
    """Tarea en el fondo para crear un archivo XLSX con los timbrados de una quincena"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, f"Generar archivo XLSX con los timbrados de {quincena_clave}...")

    # Ejecutar el creador
    try:
        mensaje_termino = crear_timbrados(quincena_clave, quincena_producto_id)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        bitacora.error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo y entregar el mensaje de termino
    set_task_progress(100, mensaje_termino)
    bitacora.info(mensaje_termino)
    return mensaje_termino


def generar_todos(quincena_clave: str) -> str:
    """Ejecutar todas las tareas en el fondo"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, f"Generar todos los archivos XLSX de {quincena_clave}...")

    # Ejecutar cada uno de los generadores
    mensajes = []
    try:
        mensajes.append(msg := reiniciar_consecutivos_generados())
        set_task_progress(20, msg)
        mensajes.append(msg := crear_nominas(quincena_clave, 0, True))
        set_task_progress(40, msg)
        mensajes.append(msg := crear_monederos(quincena_clave, 0, True))
        set_task_progress(60, msg)
        mensajes.append(msg := crear_pensionados(quincena_clave, 0, True))
        set_task_progress(80, msg)
        mensajes.append(msg := crear_dispersiones_pensionados(quincena_clave, 0))
        set_task_progress(100, msg)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        bitacora.error(mensaje_error)

    # Entregar mensajes de termino
    mensaje_termino = "\n".join(mensajes)
    set_task_progress(100, mensaje_termino)
    bitacora.info(mensaje_termino)
    return mensaje_termino
