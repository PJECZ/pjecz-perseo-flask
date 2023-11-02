"""
Quincenas, tareas en el fondo
"""
import re
from datetime import datetime

from openpyxl import Workbook

from lib.safe_string import QUINCENA_REGEXP
from lib.storage import GoogleCloudStorage, NotAllowedExtesionError, NotConfiguredError, UnknownExtensionError
from lib.tasks import set_task_error, set_task_progress
from perseo.app import create_app
from perseo.blueprints.bancos.models import Banco
from perseo.blueprints.nominas.models import Nomina
from perseo.blueprints.quincenas.models import Quincena
from perseo.extensions import database

app = create_app()
app.app_context().push()
database.app = app


def cerrar() -> None:
    """Cerrar TODAS las quincenas con estado ABIERTA"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, "Cerrando quincenas...")

    # Iniciar sesion con la base de datos para que la alimentacion sea rapida
    sesion = database.session

    # Consultar todas las quincenas con estatus "A"
    quincenas = sesion.query(Quincena).order_by(Quincena.quincena).filter_by(estatus="A").all()

    # Si no hay quincenas, mostrar mensaje de error y salir
    if len(quincenas) == 0:
        set_task_error("No hay quincenas activas.")
        return

    # Inicializar listado de quincenas cerradas
    quincenas_cerradas = []

    # Bucle por las quincenas
    for quincena_obj in quincenas:
        # Si la quincena esta abierta, cerrarla
        if quincena_obj.estado == "ABIERTA":
            quincena_obj.estado = "CERRADA"
            sesion.add(quincena_obj)
            quincenas_cerradas.append(quincena_obj)

    # Si no hubo cambios, mostrar mensaje y salir
    if len(quincenas_cerradas) == 0:
        set_task_progress(100, "No se hicieron cambios.")
        return

    # Igualar los consecutivos a los consecutivos_generado de los bancos
    bancos_actualizados = []
    for banco in Banco.query.filter_by(estatus="A").all():
        if banco.consecutivo != banco.consecutivo_generado:
            antes = banco.consecutivo
            ahora = banco.consecutivo_generado
            banco.consecutivo = banco.consecutivo_generado
            sesion.add(banco)
            bancos_actualizados.append(f"{banco.nombre} ({antes} -> {ahora})")

    # TODO: Actualizar en cada registro de nominas el numero de cheque

    # Hacer commit de los cambios en la base de datos
    sesion.commit()

    # Mensaje de termino
    bancos_actualizados_str = ""
    if len(bancos_actualizados) > 0:
        bancos_actualizados_str = "Consecutivos:" + ", ".join([b for b in bancos_actualizados])
    cerradas_str = ", ".join([q.quincena for q in quincenas_cerradas])
    set_task_progress(100, f"Quincenas cerradas: {cerradas_str}. {bancos_actualizados_str}")


def generar_nominas(quincena: str) -> None:
    """Generar archivo XLSX con las nominas de una quincena ABIERTA"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, f"Generar archivo XLSX con las nominas de {quincena}...")

    # Validar quincena
    if re.match(QUINCENA_REGEXP, quincena) is None:
        set_task_error("Quincena inválida.")
        return

    # Consultar quincena
    quincena_obj = Quincena.query.filter_by(quincena=quincena).filter_by(estatus="A").first()

    # Si no existe la quincena, provocar error y terminar
    if quincena_obj is None:
        set_task_error(f"No existe la quincena {quincena}.")
        return

    # Si la quincena no esta ABIERTA, provocar error y terminar
    if quincena_obj.estado != "ABIERTA":
        set_task_error(f"La quincena {quincena} no esta ABIERTA.")
        return

    # Iniciar sesion con la base de datos para que la alimentacion sea rapida
    sesion = database.session

    # Cargar todos los bancos
    bancos = Banco.query.filter_by(estatus="A").all()

    # Bucle para igualar el consecutivo_generado al consecutivo
    for banco in bancos:
        banco.consecutivo_generado = banco.consecutivo

    # Consultar las nominas de la quincena, solo tipo SALARIO
    nominas = Nomina.query.filter_by(quincena=quincena).filter_by(tipo="SALARIO").filter_by(estatus="A").all()

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
            if cuenta.banco.clave != "9":
                su_cuenta = cuenta
                break

        # Si no tiene cuenta bancaria, entonces se agrega a la lista de personas_sin_cuentas y se salta
        if su_cuenta is None:
            personas_sin_cuentas.append(nomina.persona)
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
                nomina.quincena,
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

        # Incrementar contador
        contador += 1

    # Actualizar los consecutivos de cada banco
    sesion.commit()

    # Determinar el nombre del archivo XLSX, juntando 'nominas' con la quincena y la fecha como YYYY-MM-DD HHMMSS
    nombre_archivo = f"nominas_{quincena}_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.xlsx"

    # Guardar el archivo XLSX
    libro.save(nombre_archivo)

    # Inicializar la liberia Google Cloud Storage con el directorio base, la fecha, las extensiones permitidas y los meses como palabras
    # gcstorage = GoogleCloudStorage(
    #     base_directory="nominas",
    #     upload_date=fecha,
    #     allowed_extensions=["xlsx"],
    #     month_in_word=False,
    #     bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO"],
    # )

    # Subir a Google Cloud Storage
    # es_exitoso = True
    # try:
    #     gcstorage.set_filename(hashed_id=lista_de_acuerdo.encode_id(), description=descripcion)
    #     gcstorage.upload(archivo.stream.read())
    # except NotConfiguredError:
    #     flash("Error al subir el archivo porque falla la configuración.", "danger")
    #     es_exitoso = False
    # except Exception:
    #     flash("Error al subir el archivo.", "danger")
    #     es_exitoso = False

    # Si se sube con exito, actualizar el registro con la URL del archivo y mostrar el detalle
    # if es_exitoso:
    #     lista_de_acuerdo.archivo = gcstorage.filename
    #     lista_de_acuerdo.url = gcstorage.url
    #     lista_de_acuerdo.save()
    #     bitacora = new_success(lista_de_acuerdo, anterior_borrada)
    #     flash(bitacora.descripcion, "success")
    #     return redirect(bitacora.url)

    # Si hubo personas sin cuentas, entonces juntarlas para mensajes
    mensajes_str = ""
    if len(personas_sin_cuentas) > 0:
        mensajes_str += f"AVISO: Hubo {len(personas_sin_cuentas)} personas sin cuentas:\n"
        mensajes_str += "\n".join([f"- {p.rfc} {p.nombre_completo}" for p in personas_sin_cuentas])
        set_task_progress(100, f"Generar nominas: {contador} filas con {len(personas_sin_cuentas)} personas sin cuentas.")
        return

    # Mensaje de termino
    set_task_progress(100, f"Generar nominas: {contador} filas.")


def generar_monederos(quincena: str) -> None:
    """Generar archivo XLSX con los monederos de una quincena ABIERTA"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, f"Generar archivo XLSX con los monederos de {quincena}...")

    # Validar quincena
    if re.match(QUINCENA_REGEXP, quincena) is None:
        set_task_error("Quincena inválida.")
        return

    # Consultar quincena
    quincena_obj = Quincena.query.filter_by(quincena=quincena).filter_by(estatus="A").first()

    # Si no existe la quincena, provocar error y terminar
    if quincena_obj is None:
        set_task_error(f"No existe la quincena {quincena}.")
        return

    # Si la quincena no esta ABIERTA, provocar error y terminar
    if quincena_obj.estado != "ABIERTA":
        set_task_error(f"La quincena {quincena} no esta ABIERTA.")
        return

    # Iniciar sesion con la base de datos para que la alimentacion sea rapida
    sesion = database.session

    # Cargar solo el banco con la clave 9 que es PREVIVALE
    banco = Banco.query.filter_by(clave="9").first()
    if banco is None:
        set_task_error("ERROR: No existe el banco con clave 9.")
        return

    # Igualar el consecutivo_generado al consecutivo
    banco.consecutivo_generado = banco.consecutivo

    # Consultar las nominas de la quincena solo tipo DESPENSA
    nominas = Nomina.query.filter_by(quincena=quincena).filter_by(tipo="DESPENSA").filter_by(estatus="A").all()

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
            if cuenta.banco.clave == "9":
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
                nomina.quincena,
                nomina.persona.modelo,
            ]
        )

        # Incrementar contador
        contador += 1

    # Actualizar los consecutivo_generado de cada banco
    sesion.commit()

    # Determinar el nombre del archivo XLSX, juntando 'monederos' con la quincena y la fecha como YYYY-MM-DD HHMMSS
    nombre_archivo = f"monederos_{quincena}_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.xlsx"

    # Guardar el archivo XLSX
    libro.save(nombre_archivo)

    # Si hubo personas sin cuentas, entonces juntarlas para mensajes
    mensajes_str = ""
    if len(personas_sin_cuentas) > 0:
        mensajes_str += f"AVISO: Hubo {len(personas_sin_cuentas)} personas sin cuentas:\n"
        mensajes_str += "\n".join([f"- {p.rfc} {p.nombre_completo}" for p in personas_sin_cuentas])
        set_task_progress(100, f"Generar monederos: {contador} filas con {len(personas_sin_cuentas)} personas sin cuentas.")
        return

    # Mensaje de termino
    set_task_progress(100, f"Generar monederos: {contador} filas.")
