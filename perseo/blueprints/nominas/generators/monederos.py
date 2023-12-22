"""
Nominas, generadores de monederos
"""
from datetime import datetime
from pathlib import Path

import pytz
from openpyxl import Workbook

from config.settings import get_settings
from lib.exceptions import MyAnyError, MyEmptyError, MyNotExistsError
from lib.storage import GoogleCloudStorage
from perseo.blueprints.bancos.models import Banco
from perseo.blueprints.nominas.generators.common import (
    GCS_BASE_DIRECTORY,
    LOCAL_BASE_DIRECTORY,
    TIMEZONE,
    actualizar_quincena_producto,
    bitacora,
    consultar_validar_quincena,
    database,
)
from perseo.blueprints.nominas.models import Nomina
from perseo.blueprints.personas.models import Persona

FUENTE = "MONEDEROS"


def crear_monederos(
    quincena_clave: str,
    quincena_producto_id: int,
    fijar_num_cheque=False,
) -> str:
    """Crear archivo XLSX con los monederos de una quincena"""

    # Consultar y validar quincena
    quincena = consultar_validar_quincena(quincena_clave)  # Puede provocar una excepcion

    # Iniciar sesion con la base de datos para que la alimentacion sea rapida
    sesion = database.session

    # Cargar solo el banco con la clave 9 que es PREVIVALE
    banco = Banco.query.filter_by(clave="9").first()

    # Si no existe el banco, provocar error y salir
    if banco is None:
        raise MyNotExistsError("No existe el banco con clave 9")

    # Igualar el consecutivo_generado al consecutivo
    banco.consecutivo_generado = banco.consecutivo

    # Consultar las nominas de la quincena solo tipo DESPENSA
    nominas = (
        Nomina.query.join(Persona)
        .filter(Nomina.quincena_id == quincena.id)
        .filter(Nomina.tipo == "DESPENSA")
        .filter(Nomina.estatus == "A")
        .order_by(Persona.rfc)
        .all()
    )

    # Si no hay registros, provocar error
    if len(nominas) == 0:
        mensaje = "No hay registros en nominas de tipo DESPENSA"
        actualizar_quincena_producto(quincena_producto_id, quincena.id, FUENTE, [mensaje])
        raise MyNotExistsError(mensaje)

    # Iniciar el archivo XLSX
    libro = Workbook()

    # Tomar la hoja del libro XLSX
    hoja = libro.active

    # Agregar la fila con las cabeceras de las columnas
    hoja.append(
        [
            "CT_CLASIF",
            "RFC",
            "TOT NET CHEQUE",
            "NUM CHEQUE",
            "NUM TARJETA",
            "QUINCENA",
            "MODELO",
        ]
    )

    # Bucle para crear cada fila del archivo XLSX
    contador = 0
    personas_sin_cuentas = []
    for nomina in nominas:
        # Tomar las cuentas de la persona
        cuentas = nomina.persona.cuentas

        # Si no tiene cuentas, entonces se agrega a la lista de personas_sin_cuentas y se salta
        if len(cuentas) == 0:
            personas_sin_cuentas.append(nomina.persona)
            continue

        # Tomar la cuenta de la persona que no tenga la clave 9, porque esa clave es la de DESPENSA
        su_cuenta = None
        for cuenta in cuentas:
            if cuenta.banco.clave == "9" and cuenta.estatus == "A":
                su_cuenta = cuenta
                break

        # Si no tiene cuenta bancaria, entonces se agrega a la lista de personas_sin_cuentas y se salta
        if su_cuenta is None:
            personas_sin_cuentas.append(nomina.persona)
            continue

        # Incrementar el consecutivo_generado del banco
        banco.consecutivo_generado += 1

        # Elaborar el numero de cheque, juntando la clave del banco y el consecutivo_generado, siempre de 9 digitos
        num_cheque = f"{su_cuenta.banco.clave.zfill(2)}{banco.consecutivo_generado:07}"

        # Agregar la fila
        hoja.append(
            [
                "J",
                nomina.persona.rfc,
                nomina.importe,
                num_cheque,
                su_cuenta.num_cuenta,
                nomina.quincena.clave,
                nomina.persona.modelo,
            ]
        )

        # Si fijar_num_cheque es verdadero, entonces actualizar el registro de la nominas con el numero de cheque
        if fijar_num_cheque:
            nomina.num_cheque = num_cheque
            sesion.add(nomina)

        # Incrementar contador
        contador += 1

    # Si contador es cero, provocar error
    if contador == 0:
        mensaje = "No hubo filas que agregar al archivo XLSX"
        actualizar_quincena_producto(quincena_producto_id, quincena.id, FUENTE, [mensaje])
        raise MyEmptyError(mensaje)

    # Actualizar los consecutivo_generado de cada banco
    sesion.commit()

    # Determinar la fecha y tiempo actual en la zona horaria de Mexico
    ahora = datetime.now(tz=pytz.timezone(TIMEZONE))

    # Determinar el nombre y ruta del archivo XLSX
    nombre_archivo_xlsx = f"monederos_{quincena_clave}_{ahora.strftime('%Y-%m-%d_%H%M%S')}.xlsx"
    descripcion_archivo_xlsx = f"Monederos {quincena_clave} {ahora.strftime('%Y-%m-%d %H%M%S')}"
    archivo_xlsx = Path(LOCAL_BASE_DIRECTORY, nombre_archivo_xlsx)

    # Si no existe la carpeta LOCAL_BASE_DIRECTORY, crearla
    Path(LOCAL_BASE_DIRECTORY).mkdir(parents=True, exist_ok=True)

    # Guardar el archivo XLSX
    libro.save(archivo_xlsx)

    # Si esta configurado settings.CLOUD_STORAGE_DEPOSITO, entonces subir el archivo XLSX a Google Cloud Storage
    settings = get_settings()
    if settings.CLOUD_STORAGE_DEPOSITO != "":
        with open(archivo_xlsx, "rb") as archivo:
            try:
                bitacora.info("GCS: Bucket %s", settings.CLOUD_STORAGE_DEPOSITO)
                gcstorage = GoogleCloudStorage(
                    base_directory=GCS_BASE_DIRECTORY,
                    upload_date=ahora.date(),
                    allowed_extensions=["xlsx"],
                    month_in_word=False,
                    bucket_name=settings.CLOUD_STORAGE_DEPOSITO,
                )
                gcs_nombre_archivo_xlsx = gcstorage.set_filename(
                    description=descripcion_archivo_xlsx,
                    extension="xlsx",
                    start_with_date=False,
                )
                bitacora.info("GCS: Subiendo %s", gcs_nombre_archivo_xlsx)
                gcs_public_path = gcstorage.upload(archivo.read())
                bitacora.info("GCS: Depositado %s", gcs_public_path)
            except MyAnyError as error:
                mensaje = str(error)
                actualizar_quincena_producto(quincena_producto_id, quincena.id, FUENTE, [mensaje])
                raise error

    # Si hubo personas sin cuentas, entonces juntarlas para mensajes
    mensajes = []
    if len(personas_sin_cuentas) > 0:
        mensajes.append(f"AVISO: Hubo {len(personas_sin_cuentas)} personas sin cuentas:")
        mensajes += [f"- {p.rfc} {p.nombre_completo}" for p in personas_sin_cuentas]

    # Si hubo mensajes, entonces no es satifactorio
    es_satisfactorio = True
    if len(mensajes) > 0:
        es_satisfactorio = False
        for m in mensajes:
            bitacora.warning(m)

    # Agregar el ultimo mensaje con la cantidad de filas en el archivo XLSX
    mensaje_termino = f"Se generaron {contador} filas"
    mensajes.append(mensaje_termino)

    # Actualizar quincena_producto
    actualizar_quincena_producto(
        quincena_producto_id=quincena_producto_id,
        quincena_id=quincena.id,
        fuente=FUENTE,
        mensajes=mensajes,
        archivo=nombre_archivo_xlsx,
        url=gcs_public_path,
        es_satisfactorio=es_satisfactorio,
    )

    # Entregar mensaje de termino
    return f"Crear monederos: {mensaje_termino}"
