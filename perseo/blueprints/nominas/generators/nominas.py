"""
Nominas, generadores de nominas
"""
from datetime import datetime
from pathlib import Path

import pytz
from openpyxl import Workbook

from config.settings import get_settings
from lib.exceptions import MyAnyError, MyNotExistsError
from lib.storage import GoogleCloudStorage
from perseo.blueprints.bancos.models import Banco
from perseo.blueprints.cuentas.models import Cuenta
from perseo.blueprints.nominas.generators.common import (
    GCS_BASE_DIRECTORY,
    LOCAL_BASE_DIRECTORY,
    TIMEZONE,
    bitacora,
    consultar_validar_quincena,
    database,
)
from perseo.blueprints.nominas.models import Nomina
from perseo.blueprints.quincenas_productos.models import QuincenaProducto


def crear_nominas(quincena_clave: str, quincena_producto_id: int, fijar_num_cheque=False) -> str:
    """Crear archivo XLSX con las nominas de una quincena"""

    # Consultar y validar quincena
    quincena = consultar_validar_quincena(quincena_clave)  # Puede provocar una excepcion

    # Iniciar sesion con la base de datos para que la alimentacion sea rapida
    sesion = database.session

    # Consultar las nominas de la quincena, solo tipo AGUINALDO
    nominas = Nomina.query.filter_by(quincena_id=quincena.id).filter_by(tipo="AGUINALDO").filter_by(estatus="A").all()

    # Consultar las nominas de la quincena, solo tipo SALARIO
    # nominas = Nomina.query.filter_by(quincena_id=quincena.id).filter_by(tipo="SALARIO").filter_by(estatus="A").all()

    # Si no hay nominas, provocar error y salir
    if len(nominas) == 0:
        raise MyNotExistsError(f"No hay nominas de tipo SALARIO en la quincena {quincena_clave}")

    # Iniciar el archivo XLSX
    libro = Workbook()

    # Tomar la hoja del libro XLSX
    hoja = libro.active

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
        # Si el modelo de la persona es 3, se omite
        if nomina.persona.modelo == 3:
            continue

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

        # Validar que no haya otra persona con el mismo banco y numero de cuenta
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

        # Incrementar la consecutivo del banco
        su_banco.consecutivo_generado += 1

        # Elaborar el numero de cheque, juntando la clave del banco y la consecutivo, siempre de 9 digitos
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

        # Si fijar_num_cheque es verdadero, entonces actualizar el registro de la nominas con el numero de cheque
        if fijar_num_cheque:
            nomina.num_cheque = num_cheque
            sesion.add(nomina)

        # Incrementar contador
        contador += 1

    # Si contador es cero, entregar mensaje de aviso y terminar
    if contador == 0:
        return "AVISO: No hubo registros para generar nominas. Tarea terminada sin generar archivo."

    # Actualizar los consecutivos de cada banco
    sesion.commit()

    # Determinar la fecha y tiempo actual en la zona horaria de Mexico
    ahora = datetime.now(tz=pytz.timezone(TIMEZONE))

    # Determinar el nombre y ruta del archivo XLSX
    nombre_archivo_xlsx = f"nominas_{quincena_clave}_{ahora.strftime('%Y-%m-%d_%H%M%S')}.xlsx"
    descripcion_archivo_xlsx = f"Nominas {quincena_clave} {ahora.strftime('%Y-%m-%d %H%M%S')}"
    archivo_xlsx = Path(LOCAL_BASE_DIRECTORY, nombre_archivo_xlsx)

    # Si no existe la carpeta LOCAL_BASE_DIRECTORY, crearla
    Path(LOCAL_BASE_DIRECTORY).mkdir(parents=True, exist_ok=True)

    # Guardar el archivo XLSX
    libro.save(archivo_xlsx)

    # Si esta configurado settings.CLOUD_STORAGE_DEPOSITO, entonces subir el archivo XLSX a Google Cloud Storage
    gcs_public_path = ""
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
                raise error

    # Si hubo personas sin cuentas, entonces juntarlas para mensajes
    mensajes = []
    if len(personas_sin_cuentas) > 0:
        mensajes.append(f"AVISO: Hubo {len(personas_sin_cuentas)} personas sin cuentas:")
        mensajes += [f"- {p.rfc} {p.nombre_completo}" for p in personas_sin_cuentas]
    if len(mensajes) > 0:
        for m in mensajes:
            bitacora.warning(m)

    # Si hubo cuentas duplicadas, entonces juntarlas para mensajes
    if len(cuentas_duplicadas) > 0:
        mensajes.append(f"AVISO: Hubo {len(cuentas_duplicadas)} cuentas duplicadas:")
        mensajes += cuentas_duplicadas

    # Si quincena_producto_id es cero, agregar un registro para conservar las rutas y mensajes
    if quincena_producto_id == 0:
        quincena_producto = QuincenaProducto(
            quincena=quincena,
            archivo=nombre_archivo_xlsx,
            es_satisfactorio=(len(mensajes) == 0),
            fuente="NOMINAS",
            mensajes="\n".join(mensajes),
            url=gcs_public_path,
        )
    else:
        # Si quincena_producto_id es diferente de cero, actualizar el registro
        quincena_producto = QuincenaProducto.query.get(quincena_producto_id)
        quincena_producto.archivo = nombre_archivo_xlsx
        quincena_producto.es_satisfactorio = len(mensajes) == 0
        quincena_producto.fuente = "NOMINAS"
        quincena_producto.mensajes = "\n".join(mensajes)
        quincena_producto.url = gcs_public_path
    quincena_producto.save()

    # Entregar mensaje de termino
    return f"Crear nominas: {contador} filas en {nombre_archivo_xlsx}"
