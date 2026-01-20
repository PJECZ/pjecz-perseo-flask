"""
Nóminas, generadores de aguinaldos
"""

from datetime import datetime
from pathlib import Path

import pytz
from openpyxl import Workbook

from pjecz_perseo_flask.blueprints.cuentas.models import Cuenta
from pjecz_perseo_flask.blueprints.nominas.generators.common import (
    GCS_BASE_DIRECTORY,
    LOCAL_BASE_DIRECTORY,
    TIMEZONE,
    actualizar_quincena_producto,
    bitacora,
    consultar_validar_quincena,
    database,
)
from pjecz_perseo_flask.blueprints.nominas.models import Nomina
from pjecz_perseo_flask.blueprints.personas.models import Persona
from pjecz_perseo_flask.config.settings import get_settings
from pjecz_perseo_flask.lib.exceptions import (
    MyBucketNotFoundError,
    MyEmptyError,
    MyFileNotAllowedError,
    MyFileNotFoundError,
    MyNotValidParamError,
    MyUploadError,
)
from pjecz_perseo_flask.lib.google_cloud_storage import upload_file_to_gcs

FUENTE = "NOMINAS"


def crear_aguinaldos(
    quincena_clave: str,
    quincena_producto_id: int,
    fijar_num_cheque: bool = False,
    modelos_separados_por_comas: str = "1,2",
) -> str:
    """Crear archivo XLSX con los aguinaldos de una quincena"""

    # Consultar y validar quincena
    quincena = consultar_validar_quincena(quincena_clave)  # Puede provocar una excepción

    # Validar los números de modelos separados por comas
    try:
        modelos = [int(m) for m in modelos_separados_por_comas.split(",")]
    except (ValueError, TypeError):
        raise MyNotValidParamError("No es válido un modelo")

    # Mandar mensaje de inicio a la bitácora
    bitacora.info("Inicia crear aguinaldos %s", quincena_clave)

    # Iniciar sesión con la base de datos para que la alimentación sea rápida
    sesion = database.session

    # Consultar las nóminas de la quincena
    nominas = (
        sesion.query(Nomina)
        .outerjoin(Persona)
        .filter(Nomina.quincena_id == quincena.id)
        .filter(Nomina.tipo == "AGUINALDO")
        .filter(Persona.modelo.in_(modelos))
        .filter(Nomina.estatus == "A")
        .order_by(Persona.rfc, Nomina.id)
        .all()
    )

    # Si no hay registros, provocar error
    if len(nominas) == 0:
        mensaje = f"No hay registros en nóminas de tipo AGUINALDO en {quincena_clave} de modelos {modelos_separados_por_comas}"
        actualizar_quincena_producto(quincena_producto_id, quincena.id, FUENTE, [mensaje])
        raise MyEmptyError(mensaje)

    # Iniciar el archivo XLSX
    libro = Workbook()

    # Tomar la hoja del libro XLSX
    hoja = libro.active
    if hoja is None:
        mensaje = "No se pudo crear la hoja del archivo XLSX."
        actualizar_quincena_producto(quincena_producto_id, quincena.id, FUENTE, [mensaje])
        raise MyEmptyError(mensaje)

    # Agregar la fila con las cabeceras de las columnas
    hoja.append(
        [
            "QUINCENA",
            "CENTRO DE TRABAJO",
            "RFC",
            "NOMBRE COMPLETO",
            "NUMERO DE EMPLEADO",
            "MODELO",
            "PLAZA",
            "NOMBRE DEL BANCO",
            "BANCO ADMINISTRADOR",
            "NUMERO DE CUENTA",
            "MONTO A DEPOSITAR",
            "NO DE CHEQUE",
        ]
    )

    # Bucle para crear cada fila del archivo XLSX
    contador = 0
    personas_sin_cuentas = []
    cuentas_duplicadas = []
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
            if cuenta.banco.clave != "9" and cuenta.estatus == "A":
                su_cuenta = cuenta
                break

        # Si no tiene cuenta bancaria, entonces se agrega a la lista de personas_sin_cuentas y se salta
        if su_cuenta is None:
            personas_sin_cuentas.append(nomina.persona)
            continue

        # Validar que no haya otra persona con el mismo banco y número de cuenta
        hay_cuenta_duplicada = False
        for posible_cuenta_duplicada in (
            Cuenta.query.filter_by(banco_id=su_cuenta.banco_id)
            .filter_by(num_cuenta=su_cuenta.num_cuenta)
            .filter_by(estatus="A")
            .all()
        ):
            if posible_cuenta_duplicada.persona_id != nomina.persona_id:
                cuentas_duplicadas.append(f"  Duplicada {nomina.persona.rfc} {su_cuenta.banco.nombre} {su_cuenta.num_cuenta}")
                hay_cuenta_duplicada = False
        if hay_cuenta_duplicada:
            continue

        # Tomar el banco de la cuenta de la persona
        su_banco = su_cuenta.banco

        # Incrementar el consecutivo del banco
        su_banco.consecutivo_generado += 1

        # Elaborar el número de cheque, juntando la clave del banco y el consecutivo, siempre de 9 digitos
        num_cheque = f"{su_cuenta.banco.clave.zfill(2)}{su_banco.consecutivo_generado:07}"

        # Agregar la fila
        hoja.append(
            [
                nomina.quincena.clave,
                nomina.centro_trabajo.clave,
                nomina.persona.rfc,
                nomina.persona.nombre_completo,
                nomina.persona.num_empleado,
                nomina.persona.modelo,
                nomina.plaza.clave,
                su_banco.nombre,
                su_banco.clave,
                su_cuenta.num_cuenta,
                nomina.importe,
                num_cheque,
            ]
        )

        # Si fijar_num_cheque es verdadero, entonces actualizar el registro de la nómina con el número de cheque
        if fijar_num_cheque:
            nomina.num_cheque = num_cheque
            sesion.add(nomina)

        # Incrementar contador
        contador += 1

    # Si el contador es cero, provocar error
    if contador == 0:
        mensaje = "No hubo filas que agregar al archivo XLSX"
        actualizar_quincena_producto(quincena_producto_id, quincena.id, FUENTE, [mensaje])
        raise MyEmptyError(mensaje)

    # Actualizar los consecutivos de cada banco
    sesion.commit()

    # Determinar el nombre del archivo XLSX
    ahora = datetime.now(tz=pytz.timezone(TIMEZONE))
    nombre_archivo_xlsx = f"aguinaldos_{quincena_clave}_{ahora.strftime('%Y-%m-%d_%H%M%S')}.xlsx"

    # Determinar las rutas con directorios con el año y el número de mes en dos dígitos
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
                actualizar_quincena_producto(quincena_producto_id, quincena.id, FUENTE, [mensaje_fallo_gcs])
                raise error

    # Si hubo personas sin cuentas, entonces juntarlas para mensajes
    mensajes = []
    if len(personas_sin_cuentas) > 0:
        mensajes.append(f"AVISO: Hubo {len(personas_sin_cuentas)} personas sin cuentas:")
        mensajes += [f"- {p.rfc} {p.nombre_completo}" for p in personas_sin_cuentas]

    # Si hubo mensajes, entonces no es satisfactorio
    es_satisfactorio = True
    if len(mensajes) > 0:
        es_satisfactorio = False
        for m in mensajes:
            bitacora.warning(m)

    # Agregar el último mensaje con la cantidad de filas en el archivo XLSX
    mensaje_termino = f"Se generaron {contador} filas"
    mensajes.append(mensaje_termino)

    # Si hubo cuentas duplicadas, entonces juntarlas para mensajes
    if len(cuentas_duplicadas) > 0:
        mensajes.append(f"AVISO: Hubo {len(cuentas_duplicadas)} cuentas duplicadas:")
        mensajes += cuentas_duplicadas

    # Actualizar quincena_producto
    actualizar_quincena_producto(
        quincena_producto_id=quincena_producto_id,
        quincena_id=quincena.id,
        fuente=FUENTE,
        mensajes=mensajes,
        archivo=nombre_archivo_xlsx,
        url=public_url,
        es_satisfactorio=es_satisfactorio,
    )

    # Entregar mensaje de termino
    mensaje_termino = f"Termina crear aguinaldos: {mensaje_termino}"
    bitacora.info(mensaje_termino)
    return mensaje_termino
