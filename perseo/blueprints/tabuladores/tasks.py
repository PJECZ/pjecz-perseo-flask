"""
Tabuladores, tareas en el fondo
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
from perseo.blueprints.tabuladores.models import Tabulador
from perseo.extensions import database

GCS_BASE_DIRECTORY = "tabuladores"
LOCAL_BASE_DIRECTORY = "exports/tabuladores"
TIMEZONE = "America/Mexico_City"

bitacora = logging.getLogger(__name__)
bitacora.setLevel(logging.INFO)
formato = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")
empunadura = logging.FileHandler("logs/tabuladores.log")
empunadura.setFormatter(formato)
bitacora.addHandler(empunadura)

app = create_app()
app.app_context().push()
database.app = app


def exportar_tabuladores() -> str:
    """Tarea en el fondo para exportar Tabuladores a un archivo XLSX"""

    # Consultar Tabuladores
    tabuladores = (
        Tabulador.query.join(Puesto)
        .filter(Tabulador.estatus == "A")
        .order_by(Puesto.clave, Tabulador.modelo, Tabulador.nivel, Tabulador.quinquenio)
        .all()
    )

    # Iniciar el archivo XLSX
    libro = Workbook()

    # Tomar la hoja del libro XLSX
    hoja = libro.active

    # Agregar la fila con las cabeceras de las columnas
    hoja.append(
        [
            "PUESTO CLAVE",
            "MODELO",
            "NIVEL",
            "QUINQUENIO",
            "FECHA",
            "SUELDO BASE",
            "INCENTIVO",
            "MONEDERO",
            "REC CUL DEP",
            "SOBRESUELDO",
            "REC DEP CUL GRAVADO",
            "REC DEP CUL EXCENTO",
            "AYUDA TRANSP",
            "MONTO QUINQUENIO",
            "TOTAL PERCEPCIONES",
            "SALARIO DIARIO",
            "PRIMA VACACIONAL MENSUAL",
            "AGUINALDO MENSUAL",
            "PRIMA VACACIONAL MENSUAL ADICIONAL",
            "TOTAL PERCEPCIONES INTEGRADO",
            "SALARIO DIARIO INTEGRADO",
            "PENSION VITALICIA EXCENTO",
            "PENSION VITALICIA GRAVABLE",
            "PENSION BONIFICACION",
        ]
    )

    # Inicializar el contador
    contador = 0

    # Bucle por los Tabuladores
    for tabulador in tabuladores:
        # Agregar la fila con los datos
        hoja.append(
            [
                tabulador.puesto.clave,
                tabulador.modelo,
                tabulador.nivel,
                tabulador.quinquenio,
                tabulador.fecha,
                tabulador.sueldo_base,
                tabulador.incentivo,
                tabulador.monedero,
                tabulador.rec_cul_dep,
                tabulador.sobresueldo,
                tabulador.rec_dep_cul_gravado,
                tabulador.rec_dep_cul_excento,
                tabulador.ayuda_transp,
                tabulador.monto_quinquenio,
                tabulador.total_percepciones,
                tabulador.salario_diario,
                tabulador.prima_vacacional_mensual,
                tabulador.aguinaldo_mensual,
                tabulador.prima_vacacional_mensual_adicional,
                tabulador.total_percepciones_integrado,
                tabulador.salario_diario_integrado,
                tabulador.pension_vitalicia_excento,
                tabulador.pension_vitalicia_gravable,
                tabulador.pension_bonificacion,
            ]
        )

        # Incrementar el contador
        contador += 1

    # Si el contador es cero, entonces no hay Tabuladores
    if contador == 0:
        raise MyEmptyError("No hay Tabuladores para exportar.")

    # Determinar el nombre del archivo XLSX
    ahora = datetime.now(tz=pytz.timezone(TIMEZONE))
    nombre_archivo_xlsx = f"tabuladores_{ahora.strftime('%Y-%m-%d_%H%M%S')}.xlsx"

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
    return f"Se exportaron {contador} Tabuladores a {nombre_archivo_xlsx}. {mensaje_gcs}"


def lanzar_exportar_tabuladores():
    """Exportar Tabuladores a un archivo XLSX"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, "Exportando Tabuladores a un archivo XLSX...")

    # Ejecutar el creador
    try:
        mensaje_termino = exportar_tabuladores()
    except (MyEmptyError, MyBucketNotFoundError, MyFileNotAllowedError, MyFileNotFoundError, MyUploadError) as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        bitacora.error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo y entregar el mensaje de termino
    set_task_progress(100, mensaje_termino)
    bitacora.info(mensaje_termino)
    return mensaje_termino
