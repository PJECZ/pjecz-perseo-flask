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
from perseo.blueprints.nominas.generators.primas_vacacionales import crear_primas_vacacionales
from perseo.blueprints.nominas.generators.timbrados import crear_timbrados
from perseo.blueprints.quincenas.models import Quincena


def lanzar_generar_nominas(quincena_clave: str, quincena_producto_id: int) -> str:
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
    return mensaje_termino


def lanzar_generar_monederos(quincena_clave: str, quincena_producto_id: int) -> str:
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
    return mensaje_termino


def lanzar_generar_pensionados(quincena_clave: str, quincena_producto_id: int) -> str:
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
    return mensaje_termino


def lanzar_generar_primas_vacacionales(quincena_clave: str, quincena_producto_id: int) -> str:
    """Tarea en el fondo para crear un archivo XLSX con las primas vacacionales de una quincena"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, f"Generar archivo XLSX con las primas vacacionales de {quincena_clave}...")

    # Ejecutar el creador
    try:
        mensaje_termino = crear_primas_vacacionales(quincena_clave, quincena_producto_id)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        bitacora.error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo y entregar el mensaje de termino
    set_task_progress(100, mensaje_termino)
    return mensaje_termino


def lanzar_generar_dispersiones_pensionados(quincena_clave: str, quincena_producto_id: int) -> str:
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
    return mensaje_termino


def lanzar_generar_timbrados(quincena_clave: str, quincena_producto_id: int, modelos: list) -> str:
    """Tarea en el fondo para crear un archivo XLSX con los timbrados de una quincena"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, f"Generar archivo XLSX con los timbrados de {quincena_clave}...")

    # Ejecutar el creador
    try:
        mensaje_termino = crear_timbrados(
            quincena_clave=quincena_clave,
            quincena_producto_id=quincena_producto_id,
            modelos=modelos,
        )
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        bitacora.error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo y entregar el mensaje de termino
    set_task_progress(100, mensaje_termino)
    return mensaje_termino


def lanzar_generar_timbrados_aguinaldos(quincena_clave: str, quincena_producto_id: int) -> str:
    """Tarea en el fondo para crear un archivo XLSX con los timbrados aguinaldos de una quincena"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, f"Generar archivo XLSX con los timbrados aguinaldos de {quincena_clave}...")

    # Ejecutar el creador
    try:
        mensaje_termino = crear_timbrados(
            quincena_clave=quincena_clave,
            quincena_producto_id=quincena_producto_id,
            tipo="AGUINALDO",
        )
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        bitacora.error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo y entregar el mensaje de termino
    set_task_progress(100, mensaje_termino)
    return mensaje_termino


def lanzar_generar_timbrados_apoyos_anuales(quincena_clave: str, quincena_producto_id: int) -> str:
    """Tarea en el fondo para crear un archivo XLSX con los timbrados apoyos anuales de una quincena"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, f"Generar archivo XLSX con los timbrados apoyos anuales de {quincena_clave}...")

    # Ejecutar el creador
    try:
        mensaje_termino = crear_timbrados(
            quincena_clave=quincena_clave,
            quincena_producto_id=quincena_producto_id,
            tipo="APOYO ANUAL",
        )
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        bitacora.error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo y entregar el mensaje de termino
    set_task_progress(100, mensaje_termino)
    return mensaje_termino


def lanzar_generar_timbrados_primas_vacacionales(quincena_clave: str, quincena_producto_id: int) -> str:
    """Tarea en el fondo para crear un archivo XLSX con los timbrados primas vacacionales de una quincena"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, f"Generar archivo XLSX con los timbrados primas vacacionales de {quincena_clave}...")

    # Ejecutar el creador
    try:
        mensaje_termino = crear_timbrados(
            quincena_clave=quincena_clave,
            quincena_producto_id=quincena_producto_id,
            tipo="PRIMA VACACIONAL",
        )
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        bitacora.error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo y entregar el mensaje de termino
    set_task_progress(100, mensaje_termino)
    return mensaje_termino


def lanzar_generar_todos(quincena_clave: str) -> str:
    """Ejecutar todas las tareas en el fondo"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, f"Generar todos los archivos XLSX de {quincena_clave}...")

    # Consultar la quincena
    try:
        quincena = Quincena.query.filter_by(clave=quincena_clave).one()
    except Exception:
        mensaje_error = f"No existe la quincena {quincena_clave}."
        set_task_error(mensaje_error)
        bitacora.error(mensaje_error)
        return mensaje_error

    # Si la quincena NO esta ABIERTA, causar error y salir
    if quincena.estado != "ABIERTA":
        mensaje_error = f"La quincena {quincena_clave} NO esta abierta."
        set_task_error(mensaje_error)
        bitacora.error(mensaje_error)
        return mensaje_error

    # Ejecutar cada uno de los generadores
    mensajes = []
    try:
        mensajes.append(msg := reiniciar_consecutivos_generados())
        set_task_progress(25, msg)
        mensajes.append(msg := crear_nominas(quincena_clave, 0, True))
        set_task_progress(50, msg)
        mensajes.append(msg := crear_monederos(quincena_clave, 0, True))
        set_task_progress(75, msg)
        mensajes.append(msg := crear_pensionados(quincena_clave, 0, True))
        if quincena.tiene_primas_vacacionales is True:
            mensajes.append(msg := crear_primas_vacacionales(quincena_clave, 0, True))
        set_task_progress(100, msg)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        bitacora.error(mensaje_error)
        return mensaje_error

    # Entregar mensajes de termino
    mensaje_termino = "\n".join(mensajes)
    set_task_progress(100, mensaje_termino)
    return mensaje_termino
