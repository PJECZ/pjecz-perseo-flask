"""
Conceptos, tareas en el fondo
"""
import logging
from datetime import datetime
from pathlib import Path

import pytz
from openpyxl import Workbook

from config.settings import get_settings
from lib.exceptions import MyBucketNotFoundError, MyEmptyError, MyFileNotAllowedError, MyFileNotFoundError, MyUploadError
from lib.google_cloud_storage import upload_file_to_gcs
from lib.tasks import set_task_error, set_task_progress
from perseo.app import create_app
from perseo.blueprints.conceptos.models import Concepto
from perseo.extensions import database

GCS_BASE_DIRECTORY = "conceptos"
LOCAL_BASE_DIRECTORY = "exports/conceptos"
TIMEZONE = "America/Mexico_City"

bitacora = logging.getLogger(__name__)
bitacora.setLevel(logging.INFO)
formato = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")
empunadura = logging.FileHandler("logs/conceptos.log")
empunadura.setFormatter(formato)
bitacora.addHandler(empunadura)

app = create_app()
app.app_context().push()
database.app = app


def exportar_conceptos() -> str:
    """Tarea en el fondo para exportar Conceptos a un archivo XLSX"""

    # Consultar Conceptos
    conceptos = Concepto.query.filter_by(estatus="A").order_by(Concepto.clave).all()

    # Iniciar el archivo XLSX
    libro = Workbook()

    # Tomar la hoja del libro XLSX
    hoja = libro.active

    # Agregar la fila con las cabeceras de las columnas
    hoja.append(
        [
            "CLAVE",
            "DESCRIPCION",
        ]
    )

    # Inicializar el contador
    contador = 0

    # Bucle por los Conceptos
    for concepto in conceptos:
        # Agregar la fila con los datos
        hoja.append(
            [
                concepto.clave,
                concepto.descripcion,
            ]
        )

        # Incrementar el contador
        contador += 1

    # Si el contador es cero, entonces no hay Conceptos
    if contador == 0:
        raise MyEmptyError("No hay Conceptos para exportar.")

    # Determinar el nombre del archivo XLSX
    ahora = datetime.now(tz=pytz.timezone(TIMEZONE))
    nombre_archivo_xlsx = f"conceptos_{ahora.strftime('%Y-%m-%d_%H%M%S')}.xlsx"

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
            public_url = upload_file_to_gcs(
                bucket_name=settings.CLOUD_STORAGE_DEPOSITO,
                blob_name=f"{ruta_gcs}/{nombre_archivo_xlsx}",
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                data=archivo.read(),
            )
            mensaje_gcs = f"Se subio el archivo XLSX a {public_url}"

    # Entregar mensaje de termino
    return f"Se exportaron {contador} Conceptos a {nombre_archivo_xlsx}. {mensaje_gcs}"


def lanzar_exportar_conceptos():
    """Exportar Conceptos a un archivo XLSX"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, "Exportando Conceptos a un archivo XLSX...")

    # Ejecutar el creador
    try:
        mensaje_termino = exportar_conceptos()
    except (MyEmptyError, MyBucketNotFoundError, MyFileNotAllowedError, MyFileNotFoundError, MyUploadError) as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        bitacora.error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo y entregar el mensaje de termino
    set_task_progress(100, mensaje_termino)
    bitacora.info(mensaje_termino)
    return mensaje_termino
