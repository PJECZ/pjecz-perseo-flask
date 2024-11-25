"""
Timbrados, tareas en el fondo
"""

import logging
from datetime import datetime
from pathlib import Path

import pytz
from openpyxl import Workbook

from config.settings import get_settings
from lib.exceptions import (
    MyAnyError,
    MyBucketNotFoundError,
    MyEmptyError,
    MyFileNotAllowedError,
    MyFileNotFoundError,
    MyIsDeletedError,
    MyNotExistsError,
    MyUploadError,
)
from lib.google_cloud_storage import upload_file_to_gcs
from lib.tasks import set_task_error, set_task_progress
from perseo.app import create_app
from perseo.blueprints.nominas.models import Nomina
from perseo.blueprints.personas.models import Persona
from perseo.blueprints.quincenas.models import Quincena
from perseo.blueprints.timbrados.models import Timbrado
from perseo.extensions import database

GCS_BASE_DIRECTORY = "timbrados"
LOCAL_BASE_DIRECTORY = "exports/timbrados"
TIMEZONE = "America/Mexico_City"

bitacora = logging.getLogger(__name__)
bitacora.setLevel(logging.INFO)
formato = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")
empunadura = logging.FileHandler("logs/timbrados.log")
empunadura.setFormatter(formato)
bitacora.addHandler(empunadura)

app = create_app()
app.app_context().push()
database.app = app


def exportar_xlsx(quincena_clave: str, nomina_tipo: str) -> tuple[str, str, str]:
    """Exportar Timbrados (con datos particulares dentro de los XML) a un archivo XLSX"""
    bitacora.info("Inicia exportar Timbrados a un archivo XLSX de la quincena %s del tipo %s", quincena_clave, nomina_tipo)

    # TODO: Consultar los Timbrados
    contador = 0
    nombre_archivo_xlsx = "timbrados.xlsx"
    public_url = "https://google.com"

    # Entregar mensaje de termino, el nombre del archivo XLSX y la URL publica
    mensaje_termino = f"Se exportaron {contador} Timbrados a {nombre_archivo_xlsx}"
    bitacora.info(mensaje_termino)
    return mensaje_termino, nombre_archivo_xlsx, public_url


def lanzar_exportar_xlsx(quincena_clave: str, nomina_tipo: str):
    """Exportar Timbrados (con datos particulares dentro de los XML) a un archivo XLSX"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, f"Inicia exportar Timbrados a un archivo XLSX de la quincena {quincena_clave} del tipo {nomina_tipo}")

    # Ejecutar el creador
    try:
        mensaje_termino, nombre_archivo_xlsx, public_url = exportar_xlsx(quincena_clave, nomina_tipo)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo y entregar el mensaje de termino
    set_task_progress(100, mensaje_termino, nombre_archivo_xlsx, public_url)
    return mensaje_termino
