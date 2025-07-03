"""
Timbrados, tareas en el fondo
"""

import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import pandas as pd
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
    MyNotValidParamError,
    MyUploadError,
)
from lib.google_cloud_storage import upload_file_to_gcs
from lib.safe_string import QUINCENA_REGEXP
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

# Definir la constante con los tipos de nóminas que se pueden exportar
NOMINAS_TIPOS = ["AGUINALDO", "APOYO ANUAL", "APOYO DIA DE LA MADRE", "SALARIO", "PRIMA VACACIONAL"]

# Definir la constante con el espacio de nombres del XML
NAMESPACES = {
    "cfdi": "http://www.sat.gob.mx/cfd/3",
    "tfd": "http://www.sat.gob.mx/TimbreFiscalDigital",
    "nomina12": "http://www.sat.gob.mx/nomina12",
}

# Definir la constante con el listado de claves de deducciones a extraer del XML
CLAVES_DEDUCCIONES = ["D01", "D02", "D03", "D04", "D05", "DPL"]

# Definir la constante con el orden de las columnas
COLUMNAS = ["QUINCENA", "RFC", "NOMBRES", "APELLIDO PRIMERO", "APELLIDO SEGUNDO", "MODELO"] + CLAVES_DEDUCCIONES


def exportar_xlsx(quincena_clave: str, nomina_tipo: str) -> tuple[str, str, str]:
    """Exportar Timbrados (con datos particulares dentro de los XML) a un archivo XLSX"""

    # Validar quincena_clave
    if re.match(QUINCENA_REGEXP, quincena_clave) is None:
        raise MyNotValidParamError("Clave de la quincena inválida.")

    # Consultar quincena
    quincena = Quincena.query.filter_by(clave=quincena_clave).first()

    # Si no existe la quincena, provocar error y terminar
    if quincena is None:
        raise MyNotExistsError(f"No existe la quincena {quincena_clave}")

    # Si la quincena está eliminada, provocar error y terminar
    if quincena.estatus != "A":
        raise MyNotValidParamError(f"La quincena {quincena_clave} esta eliminada")

    # Validar el tipo
    nomina_tipo = nomina_tipo.upper()
    if nomina_tipo not in NOMINAS_TIPOS:
        raise MyNotValidParamError(f"El tipo de nómina {nomina_tipo} no es válido")

    # Mandar mensaje de inicio a la bitácora
    bitacora.info("Inicia exportar Timbrados a un archivo XLSX de la quincena %s del tipo %s", quincena_clave, nomina_tipo)

    # Iniciar listado con los mensajes
    mensajes = []

    # Iniciar sesión con la base de datos
    session = database.session

    # Consultar los Timbrados
    timbrados = (
        session.query(Timbrado)
        .select_from(Timbrado)
        .join(Nomina)
        .join(Persona)
        .join(Quincena)
        .filter(Nomina.tipo == nomina_tipo)
        .filter(Quincena.clave == quincena_clave)
        .filter(Timbrado.estatus == "A")
        .order_by(Persona.rfc)
        .all()
    )

    # Inicializar el contador
    contador = 0

    # Inicializar listado donde almacenaremos los datos de las nóminas
    nominas = []

    # Bucle por los timbrados
    for timbrado in timbrados:
        # La propiedad tfd es un XML en texto
        tree = ET.ElementTree(ET.fromstring(timbrado.tfd))
        # Iniciar el árbol
        root = tree.getroot()
        # Buscar el nodo nomina12:Deducciones
        deducciones = root.find(".//nomina12:Deducciones", NAMESPACES)
        # Si NO hay deducciones se omite
        if deducciones is None:
            continue
        # Inicializar el diccionario de la nomina
        nomina = dict()
        # Agregar los datos de la quincena
        nomina["QUINCENA"] = timbrado.nomina.quincena.clave
        # Agregar los datos de la persona
        nomina["RFC"] = timbrado.nomina.persona.rfc
        nomina["NOMBRES"] = timbrado.nomina.persona.nombres
        nomina["APELLIDO PRIMERO"] = timbrado.nomina.persona.apellido_primero
        nomina["APELLIDO SEGUNDO"] = timbrado.nomina.persona.apellido_segundo
        nomina["MODELO"] = timbrado.nomina.persona.modelo
        # Iterar sobre los nodos
        for deduccion in deducciones.findall(".//nomina12:Deduccion", NAMESPACES):
            # Obtener TipoDeduccion, Clave, Concepto e Importe
            tipo_deduccion = deduccion.attrib.get("TipoDeduccion", "")
            clave = deduccion.attrib.get("Clave", "")
            concepto = deduccion.attrib.get("Concepto", "")
            importe = deduccion.attrib.get("Importe", "")
            # Si la clave NO está en el listado de claves de deducciones se omite
            if clave not in CLAVES_DEDUCCIONES:
                continue
            # Agregar los datos de la deducción a la nomina
            nomina[clave] = importe
        # Agregar la nómina al listado
        nominas.append(nomina)

    # Agregar mensajes
    mensaje = f"Se encontraron {len(nominas)} timbrados en la quincena {quincena_clave} del tipo {nomina_tipo}"
    bitacora.info(mensaje)
    mensajes.append(mensaje)

    # Crear un DataFrame con las nóminas
    df = pd.DataFrame(nominas)
    df = df.fillna(0)  # Reemplazar NaN por 0
    df = df.reindex(columns=COLUMNAS)  # Reordenar las columnas
    df[CLAVES_DEDUCCIONES] = df[CLAVES_DEDUCCIONES].apply(pd.to_numeric)  # Convertir a numérico

    # Determinar el nombre del archivo XLSX
    ahora = datetime.now(tz=pytz.timezone(TIMEZONE))
    nombre_archivo_xlsx = f"timbrados_{quincena_clave}_{nomina_tipo}_{ahora.strftime('%Y-%m-%d_%H%M%S')}.xlsx"

    # Determinar las rutas con directorios con el año y el número de mes en dos digitos
    ruta_local = Path(LOCAL_BASE_DIRECTORY, ahora.strftime("%Y"), ahora.strftime("%m"))
    ruta_gcs = Path(GCS_BASE_DIRECTORY, ahora.strftime("%Y"), ahora.strftime("%m"))
    ruta_local_archivo_xlsx = str(Path(ruta_local, nombre_archivo_xlsx))

    # Si no existe el directorio local, crearlo
    Path(ruta_local).mkdir(parents=True, exist_ok=True)

    # Guardar el DataFrame a un archivo XLSX
    df.to_excel(ruta_local_archivo_xlsx, index=False, header=True)

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

    # Entregar mensaje de término, el nombre del archivo XLSX y la URL pública
    mensaje_termino = f"Se exportaron los timbrados a {nombre_archivo_xlsx}"
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
