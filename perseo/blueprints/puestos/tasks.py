"""
Puestos, tareas en el fondo
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
from perseo.blueprints.puestos.models import Puesto
from perseo.extensions import database

GCS_BASE_DIRECTORY = "puestos"
LOCAL_BASE_DIRECTORY = "exports/puestos"
TIMEZONE = "America/Mexico_City"

bitacora = logging.getLogger(__name__)
bitacora.setLevel(logging.INFO)
formato = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")
empunadura = logging.FileHandler("logs/puestos.log")
empunadura.setFormatter(formato)
bitacora.addHandler(empunadura)

app = create_app()
app.app_context().push()
database.app = app


def exportar_puestos() -> str:
    """Tarea en el fondo para exportar Puestos a un archivo XLSX"""

    # Consultar Puestos
    puestos = Puesto.query.filter_by(estatus="A").order_by(Puesto.clave).all()

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

    # Bucle por los Puestos
    for puesto in puestos:
        # Agregar la fila con los datos
        hoja.append(
            [
                puesto.clave,
                puesto.descripcion,
            ]
        )

        # Incrementar el contador
        contador += 1

    # Si el contador es cero, entonces no hay Puestos
    if contador == 0:
        raise MyEmptyError("No hay Puestos para exportar.")

    # Determinar el nombre del archivo XLSX
    ahora = datetime.now(tz=pytz.timezone(TIMEZONE))
    nombre_archivo_xlsx = f"puestos_{ahora.strftime('%Y-%m-%d_%H%M%S')}.xlsx"

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
    return f"Se exportaron {contador} Puestos a {nombre_archivo_xlsx}. {mensaje_gcs}"


def lanzar_exportar_puestos():
    """Exportar Puestos a un archivo XLSX"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, "Exportando Puestos a un archivo XLSX...")

    # Ejecutar el creador
    try:
        mensaje_termino = exportar_puestos()
    except (MyEmptyError, MyBucketNotFoundError, MyFileNotAllowedError, MyFileNotFoundError, MyUploadError) as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        bitacora.error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo y entregar el mensaje de termino
    set_task_progress(100, mensaje_termino)
    bitacora.info(mensaje_termino)
    return mensaje_termino
