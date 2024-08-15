"""
Personas, tareas en el fondo
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
from perseo.blueprints.centros_trabajos.models import CentroTrabajo
from perseo.blueprints.nominas.models import Nomina
from perseo.blueprints.personas.models import Persona
from perseo.blueprints.plazas.models import Plaza
from perseo.blueprints.quincenas.models import Quincena
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


def actualizar_ultimos_xlsx(persona_id: int = None) -> tuple[str, str, str]:
    """Actualizar último centro de trabajo y plaza de las Personas"""
    bitacora.info("Inicia actualizar último centro de trabajo y plaza de las Personas")

    # Si se proporciona un ID de Persona, entonces actualizar solo esa Persona
    if persona_id is not None:
        persona = Persona.query.filter_by(id=persona_id).first()
        if persona is None:
            mensaje_error = f"No existe la Persona con ID {persona_id}"
            bitacora.error(mensaje_error)
            raise MyNotExistsError(mensaje_error)
        if persona.estatus != "A":
            mensaje_error = f"La Persona con ID {persona_id} está eliminada"
            bitacora.error(mensaje_error)
            raise MyIsDeletedError(mensaje_error)
        personas = [persona]
    else:
        personas = Persona.query.filter_by(estatus="A").order_by(Persona.rfc).all()

    # Definir la instancia con el centro de trabajo "NO DEFINIDO"
    centro_trabajo_no_definido = CentroTrabajo.query.filter_by(clave="ND").first()
    if centro_trabajo_no_definido is None:
        mensaje_error = "No existe el Centro de Trabajo con clave ND"
        bitacora.error(mensaje_error)
        raise MyNotExistsError(mensaje_error)

    # Definir la instancia con la plaza "NO DEFINIDA"
    plaza_no_definida = Plaza.query.filter_by(clave="ND").first()
    if plaza_no_definida is None:
        mensaje_error = "No existe la Plaza con clave ND"
        bitacora.error(mensaje_error)
        raise MyNotExistsError(mensaje_error)

    # Iniciar listado con los mensajes
    mensajes = []

    # Tomar la última Quinena
    quincena = Quincena.query.order_by(Quincena.clave.desc()).filter_by(estatus="A").first()
    if quincena is None:
        raise MyNotExistsError("No hay Quincenas")
    mensaje = f"Se tomará la Quincena {quincena.clave}"
    bitacora.info(mensaje)
    mensajes.append(mensaje)

    # Iniciar el archivo XLSX
    libro = Workbook()

    # Tomar la hoja del libro XLSX
    hoja = libro.active

    # Agregar la fila con las cabeceras de las columnas
    hoja.append(
        [
            "ES ACTIVO",
            "RFC",
            "NOMBRES",
            "APELLIDO PRIMERO",
            "APELLIDO SEGUNDO",
            "CURP",
            "MODELO",
            "NUMERO DE EMPLEADO",
            "CENTRO DE TRABAJO CLAVE",
            "CENTRO DE TRABAJO DESCRIPCION",
            "PLAZA CLAVE",
            "PLAZA DESCRIPCION",
            "FUE ACTUALIZADO",
        ]
    )

    # Bucle por las Personas
    contador = 0
    activos_contador = 0
    inactivos_contador = 0
    actualizaciones_contador = 0
    for persona in personas:
        # Incrementar el contador
        contador += 1

        # Consultar la última nómina de la Persona y de la Quincena tomada
        nomina = (
            Nomina.query.filter(Nomina.persona_id == persona.id)
            .filter(Nomina.quincena_id == quincena.id)
            .filter_by(tipo="SALARIO")
            .first()
        )

        # Si no hay nómina..
        if nomina is None:
            # Entonces los ultimos seran no definidos y se desactiva
            ultimo_centro_trabajo_id = centro_trabajo_no_definido.id
            ultimo_plaza_id = plaza_no_definida.id
            es_activa_o_inactiva = False
            inactivos_contador += 1
        else:
            # De lo contrario, se toman los valores de la nómina
            ultimo_centro_trabajo_id = nomina.centro_trabajo_id
            ultimo_plaza_id = nomina.plaza_id
            es_activa_o_inactiva = True
            activos_contador += 1

        # Iniciar bandera para saber si se va a actualizar
        se_va_a_actualizar = False

        # Si cambia el último centro de trabajo
        if persona.ultimo_centro_trabajo_id != ultimo_centro_trabajo_id:
            persona.ultimo_centro_trabajo_id = ultimo_centro_trabajo_id
            se_va_a_actualizar = True

        # Si cambia la última plaza
        if persona.ultimo_plaza_id != ultimo_plaza_id:
            persona.ultimo_plaza_id = ultimo_plaza_id
            se_va_a_actualizar = True

        # Si cambia es_activo
        if persona.es_activa != es_activa_o_inactiva:
            persona.es_activa = es_activa_o_inactiva
            se_va_a_actualizar = True

        # Si se va a actualizar
        if se_va_a_actualizar:
            # database.session.add(persona)
            # database.session.commit()
            actualizaciones_contador += 1

        # Si el ultimo centro de trabajo NO es NO DEFINIDO, se consulta
        if persona.ultimo_centro_trabajo_id != centro_trabajo_no_definido.id:
            ultimo_centro_trabajo = CentroTrabajo.query.filter_by(id=persona.ultimo_centro_trabajo_id).first()
        else:
            ultimo_centro_trabajo = centro_trabajo_no_definido

        # Si la última plaza NO es NO DEFINIDA, se consulta
        if persona.ultimo_plaza_id != plaza_no_definida.id:
            ultimo_plaza = Plaza.query.filter_by(id=persona.ultimo_plaza_id).first()
        else:
            ultimo_plaza = plaza_no_definida

        # Agregar la fila con los datos
        hoja.append(
            [
                int(persona.es_activa),
                persona.rfc,
                persona.nombres,
                persona.apellido_primero,
                persona.apellido_segundo,
                persona.curp,
                persona.modelo,
                persona.num_empleado,
                ultimo_centro_trabajo.clave,
                ultimo_centro_trabajo.descripcion,
                ultimo_plaza.clave,
                ultimo_plaza.descripcion,
                int(se_va_a_actualizar),
            ]
        )

    # Agregar mensajes
    mensaje = f"Ahora hay un total de {activos_contador} personas activas."
    bitacora.info(mensaje)
    mensajes.append(mensaje)
    mensaje = f"Ahora hay un total de {inactivos_contador} personas inactivas."
    bitacora.info(mensaje)
    mensajes.append(mensaje)
    mensaje = f"Se actualizaron {actualizaciones_contador} registros."
    bitacora.info(mensaje)
    mensajes.append(mensaje)

    # Determinar el nombre del archivo XLSX
    ahora = datetime.now(tz=pytz.timezone(TIMEZONE))
    nombre_archivo_xlsx = f"personas_actualizaciones_{ahora.strftime('%Y-%m-%d_%H%M%S')}.xlsx"

    # Determinar las rutas con directorios con el año y el número de mes en dos digitos
    ruta_local = Path(LOCAL_BASE_DIRECTORY, ahora.strftime("%Y"), ahora.strftime("%m"))
    ruta_gcs = Path(GCS_BASE_DIRECTORY, ahora.strftime("%Y"), ahora.strftime("%m"))

    # Si no existe el directorio local, crearlo
    Path(ruta_local).mkdir(parents=True, exist_ok=True)

    # Guardar el archivo XLSX
    ruta_local_archivo_xlsx = str(Path(ruta_local, nombre_archivo_xlsx))
    libro.save(ruta_local_archivo_xlsx)

    # Si esta configurado Google Cloud Storage
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
                mensaje = f"Se subió el archivo XLSX a GCS {public_url}"
                bitacora.info(mensaje)
                mensajes.append(mensaje)
            except (MyEmptyError, MyBucketNotFoundError, MyFileNotAllowedError, MyFileNotFoundError, MyUploadError) as error:
                mensaje = f"Falló el subir el archivo XLSX a GCS: {str(error)}"
                bitacora.warning(mensaje)
                mensajes.append(mensaje)

    # Entregar mensaje de termino, el nombre del archivo XLSX y la URL publica
    mensaje_termino = "\n".join(mensajes)
    return mensaje_termino, nombre_archivo_xlsx, public_url


def lanzar_actualizar_ultimos_xlsx(persona_id: int = None):
    """Actualizar último centro de trabajo, plaza y puesto de las Personas"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, "Inicia actualizar último centro de trabajo, plaza y puesto de las Personas")

    # Ejecutar el creador
    try:
        mensaje_termino, nombre_archivo_xlsx, public_url = actualizar_ultimos_xlsx(persona_id)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo y entregar el mensaje de termino
    set_task_progress(100, mensaje_termino, nombre_archivo_xlsx, public_url)
    return mensaje_termino


def exportar_xlsx() -> tuple[str, str, str]:
    """Exportar Personas a un archivo XLSX"""
    bitacora.info("Inicia exportar Personas a un archivo XLSX")

    # Consultar Personas
    personas = Persona.query.filter_by(estatus="A").order_by(Persona.rfc).all()

    # Iniciar el archivo XLSX
    libro = Workbook()

    # Tomar la hoja del libro XLSX
    hoja = libro.active

    # Agregar la fila con las cabeceras de las columnas
    hoja.append(
        [
            "ID",
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
                persona.id,
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
        mensaje_error = "No hay Personas para exportar."
        bitacora.error(mensaje_error)
        raise MyEmptyError(mensaje_error)

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

    # Entregar mensaje de termino, el nombre del archivo XLSX y la URL publica
    mensaje_termino = f"Se exportaron {contador} Personas a {nombre_archivo_xlsx}"
    bitacora.info(mensaje_termino)
    return mensaje_termino, nombre_archivo_xlsx, public_url


def lanzar_exportar_xlsx():
    """Exportar Personas a un archivo XLSX"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, "Inicia exportar Personas a un archivo XLSX")

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
