"""
Cuentas, tareas en el fondo
"""

import logging
from datetime import datetime
from pathlib import Path

import pytz
from openpyxl import Workbook

from pjecz_perseo_flask.blueprints.bancos.models import Banco
from pjecz_perseo_flask.blueprints.cuentas.models import Cuenta
from pjecz_perseo_flask.blueprints.personas.models import Persona
from pjecz_perseo_flask.config.settings import get_settings
from pjecz_perseo_flask.lib.exceptions import (
    MyAnyError,
    MyBucketNotFoundError,
    MyEmptyError,
    MyFileNotAllowedError,
    MyFileNotFoundError,
    MyUploadError,
)
from pjecz_perseo_flask.lib.google_cloud_storage import upload_file_to_gcs
from pjecz_perseo_flask.lib.tasks import set_task_error, set_task_progress
from pjecz_perseo_flask.main import app

GCS_BASE_DIRECTORY = "cuentas"
LOCAL_BASE_DIRECTORY = "exports/cuentas"
TIMEZONE = "America/Mexico_City"

bitacora = logging.getLogger(__name__)
bitacora.setLevel(logging.INFO)
formato = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")
empunadura = logging.FileHandler("logs/cuentas.log")
empunadura.setFormatter(formato)
bitacora.addHandler(empunadura)

# Inicializar el contexto de la aplicación Flask
app.app_context().push()


def exportar_xlsx() -> tuple[str, str, str]:
    """Exportar Cuentas a un archivo XLSX"""
    bitacora.info("Inicia exportar Cuentas a un archivo XLSX")

    # Consultar Cuentas
    cuentas = Cuenta.query.join(Banco).join(Persona).filter(Cuenta.estatus == "A").order_by(Persona.rfc).all()

    # Iniciar el archivo XLSX
    libro = Workbook()

    # Tomar la hoja del libro XLSX
    hoja = libro.active
    if hoja is None:
        mensaje_error = "No se pudo crear la hoja del archivo XLSX."
        bitacora.error(mensaje_error)
        raise MyEmptyError(mensaje_error)

    # Agregar la fila con las cabeceras de las columnas
    hoja.append(
        [
            "RFC",
            "NOMBRES",
            "APELLIDO PRIMERO",
            "APELLIDO SEGUNDO",
            "BANCO",
            "CLAVE D.P.",
            "NÚMERO DE CUENTA",
        ]
    )

    # Inicializar el contador
    contador = 0

    # Bucle por las Cuentas
    for cuenta in cuentas:
        # Agregar la fila con los datos
        hoja.append(
            [
                cuenta.persona.rfc,
                cuenta.persona.nombres,
                cuenta.persona.apellido_primero,
                cuenta.persona.apellido_segundo,
                cuenta.banco.nombre,
                cuenta.banco.clave_dispersion_pensionados,
                cuenta.num_cuenta,
            ]
        )

        # Incrementar el contador
        contador += 1

    # Si el contador es 0, entonces no hay Cuentas
    if contador == 0:
        mensaje_error = "No hay Cuentas para exportar."
        bitacora.error(mensaje_error)
        raise MyEmptyError(mensaje_error)

    # Determinar el nombre del archivo XLSX
    ahora = datetime.now(tz=pytz.timezone(TIMEZONE))
    nombre_archivo_xlsx = f"cuentas_{ahora.strftime('%Y-%m-%d_%H%M%S')}.xlsx"

    # Determinar las rutas con directorios con el año y el número de mes en dos digitos
    ruta_local = Path(LOCAL_BASE_DIRECTORY, ahora.strftime("%Y"), ahora.strftime("%m"))
    ruta_gcs = Path(GCS_BASE_DIRECTORY, ahora.strftime("%Y"), ahora.strftime("%m"))

    # Si no existe el directorio local, crearlo
    Path(ruta_local).mkdir(parents=True, exist_ok=True)

    # Guardar el archivo XLSX
    ruta_local_archivo_xlsx = str(Path(ruta_local, nombre_archivo_xlsx))
    libro.save(ruta_local_archivo_xlsx)

    # Si esta configurado Google Cloud Storage
    mensaje_gcs = ""
    public_url = ""
    settings = get_settings()
    if settings.CLOUD_STORAGE_DEPOSITO != "":
        # Leer el contenido del archivo XLSX
        with open(ruta_local_archivo_xlsx, "rb") as archivo:
            # Subir el archivo XLSX a Google Cloud Storage
            try:
                public_url = upload_file_to_gcs(
                    bucket_name=settings.CLOUD_STORAGE_DEPOSITO,
                    blob_name=f"{ruta_gcs}/{nombre_archivo_xlsx}",
                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    data=archivo.read(),
                )
                mensaje_gcs = f"Se subio el archivo XLSX a GCS {public_url}"
                bitacora.info(mensaje_gcs)
            except (MyEmptyError, MyBucketNotFoundError, MyFileNotAllowedError, MyFileNotFoundError, MyUploadError) as error:
                mensaje_fallo_gcs = str(error)
                bitacora.warning("Falló al subir el archivo XLSX a GCS: %s", mensaje_fallo_gcs)

    # Entregar mensaje de término, el nombre del archivo XLSX y la URL pública
    mensaje_termino = f"Se exportaron {contador} Cuentas a {nombre_archivo_xlsx}"
    bitacora.info(mensaje_termino)
    return mensaje_termino, nombre_archivo_xlsx, public_url


def lanzar_exportar_xlsx():
    """Exportar Cuentas a un archivo XLSX"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, "Inicia exportar Cuentas a un archivo XLSX")

    # Ejecutar el creador
    try:
        mensaje_termino, nombre_archivo_xlsx, public_url = exportar_xlsx()
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo y entregar el mensaje de termino
    set_task_progress(100, mensaje_termino, nombre_archivo_xlsx, public_url)
    return mensaje_termino
