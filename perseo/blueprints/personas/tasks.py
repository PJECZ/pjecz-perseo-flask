"""
Personas, tareas en el fondo
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
from perseo.blueprints.personas.models import Persona
from perseo.extensions import database

GCS_BASE_DIRECTORY = "personas"
LOCAL_BASE_DIRECTORY = "exports/personas"
TIMEZONE = "America/Mexico_City"

bitacora = logging.getLogger(__name__)
bitacora.setLevel(logging.INFO)
formato = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")
empunadura = logging.FileHandler("logs/personas.log")
empunadura.setFormatter(formato)
bitacora.addHandler(empunadura)

app = create_app()
app.app_context().push()
database.app = app


def exportar_personas() -> str:
    """Tarea en el fondo para exportar Personas a un archivo XLSX"""

    # Consultar Personas
    personas = Persona.query.filter_by(estatus="A").order_by(Persona.rfc).all()

    # Iniciar el archivo XLSX
    libro = Workbook()

    # Tomar la hoja del libro XLSX
    hoja = libro.active

    # Agregar la fila con las cabeceras de las columnas
    hoja.append(
        [
            "RFC",
            "NOMBRES",
            "APELLIDO PRIMERO",
            "APELLIDO SEGUNDO",
            "CURP",
            "CODIGO POSTAL FISCAL",
            "MODELO",
            "NUMERO DE EMPLEADO",
            "SEGURO SOCIAL",
            "INGRESO GOBIERNO FECHA",
            "INGRESO PJ FECHA",
            "NACIMIENTO FECHA",
        ]
    )

    # Inicializar el contador
    contador = 0

    # Bucle por las Personas
    for persona in personas:
        # Agregar la fila con los datos
        hoja.append(
            [
                persona.rfc,
                persona.nombres,
                persona.apellido_primero,
                persona.apellido_segundo,
                persona.curp,
                persona.codigo_postal_fiscal,
                persona.modelo,
                persona.num_empleado,
                persona.seguridad_social,
                persona.ingreso_gobierno_fecha,
                persona.ingreso_pj_fecha,
                persona.nacimiento_fecha,
            ]
        )

        # Incrementar el contador
        contador += 1

    # Si el contador es 0, entonces no hay Personas
    if contador == 0:
        raise MyEmptyError("No hay Personas para exportar.")

    # Determinar el nombre del archivo XLSX
    ahora = datetime.now(tz=pytz.timezone(TIMEZONE))
    nombre_archivo_xlsx = f"personas_{ahora.strftime('%Y-%m-%d_%H%M%S')}.xlsx"

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
    return f"Se exportaron {contador} Personas a {nombre_archivo_xlsx}. {mensaje_gcs}"


def lanzar_exportar_personas():
    """Exportar Personas a un archivo XLSX"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, "Exportando Personas a un archivo XLSX...")

    # Ejecutar el creador
    try:
        mensaje_termino = exportar_personas()
    except (MyEmptyError, MyBucketNotFoundError, MyFileNotAllowedError, MyFileNotFoundError, MyUploadError) as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        bitacora.error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo y entregar el mensaje de termino
    set_task_progress(100, mensaje_termino)
    bitacora.info(mensaje_termino)
    return mensaje_termino
