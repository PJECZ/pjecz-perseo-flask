"""
Nominas, generadores de timbrados
"""

from datetime import datetime
from pathlib import Path

import pytz
from openpyxl import Workbook

from config.settings import get_settings
from lib.exceptions import (
    MyBucketNotFoundError,
    MyEmptyError,
    MyFileNotAllowedError,
    MyFileNotFoundError,
    MyNotExistsError,
    MyNotValidParamError,
    MyUploadError,
)
from lib.fechas import quincena_to_fecha
from lib.google_cloud_storage import upload_file_to_gcs
from perseo.blueprints.centros_trabajos.models import CentroTrabajo
from perseo.blueprints.conceptos.models import Concepto
from perseo.blueprints.cuentas.models import Cuenta
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
from perseo.blueprints.percepciones_deducciones.models import PercepcionDeduccion
from perseo.blueprints.personas.models import Persona
from perseo.blueprints.plazas.models import Plaza
from perseo.blueprints.quincenas.models import Quincena
from perseo.blueprints.tabuladores.models import Tabulador

PATRON_RFC = "PJE901211TI9"
COMPANIA_NOMBRE = "PODER JUDICIAL DEL ESTADO DE COAHUILA DE ZARAGOZA"
COMPANIA_RFC = PATRON_RFC
COMPANIA_CP = "25000"


def crear_timbrados(
    quincena_clave: str,
    quincena_producto_id: int,
    modelos: list = None,
    tipo: str = "SALARIO",
) -> str:
    """Crear archivo XLSX con los timbrados de una quincena"""

    # Consultar quincena
    quincena = Quincena.query.filter_by(clave=quincena_clave).first()

    # Si no existe la quincena, provocar error y terminar
    if quincena is None:
        raise MyNotExistsError(f"No existe la quincena {quincena_clave}")

    # Si la quincena esta eliminada, provocar error y terminar
    if quincena.estatus != "A":
        raise MyNotValidParamError(f"La quincena {quincena_clave} esta eliminada")

    # Validar los modelos 1: "CONFIANZA", 2: "SINDICALIZADO", 3: "PENSIONADO"
    if modelos is None:
        modelos = [1, 2]
    else:
        for modelo in modelos:
            if modelo not in [1, 2, 3]:
                raise MyNotValidParamError(f"El modelo {modelo} no es valido")

    # Validar el tipo
    if tipo not in ["APOYO ANUAL", "AGUINALDO", "SALARIO"]:
        raise MyNotValidParamError(f"El tipo {tipo} no es valido")

    # Por defecto fuente es TIMBRADOS para el tipo SALARIO
    fuente = "TIMBRADOS"
    if tipo == "AGUINALDO":
        fuente = "TIMBRADOS AGUINALDOS"
    elif tipo == "APOYO ANUAL":
        fuente = "TIMBRADOS APOYOS ANUALES"
    elif modelos == [3]:
        fuente = "TIMBRADOS PENSIONADOS"
    elif modelos == [1, 2]:
        fuente = "TIMBRADOS EMPLEADOS ACTIVOS"

    # Inicializar el diccionario de conceptos
    conceptos_dict = {}

    # Determinar las fechas inicial y final de la quincena
    if tipo == "SALARIO":
        quincena_fecha_inicial = quincena_to_fecha(quincena_clave, dame_ultimo_dia=False)
        quincena_fecha_final = quincena_to_fecha(quincena_clave, dame_ultimo_dia=True)
    else:
        quincena_fecha_inicial = datetime(year=2023, month=1, day=1).date()
        quincena_fecha_final = datetime(year=2023, month=12, day=31).date()

    # Iniciar sesion con la base de datos para que la alimentacion sea rapida
    session = database.session

    # Si el tipo es AGUINALDO o SALARIO armar un diccionario con las percepciones y deducciones de Conceptos activos
    if tipo in ["AGUINALDO", "SALARIO"]:
        # Consultar los conceptos activos
        conceptos = session.query(Concepto).filter_by(estatus="A").order_by(Concepto.clave).all()
        # Ordenar las claves, primero las que empiezan con P
        for concepto in conceptos:
            if concepto.clave.startswith("P"):
                conceptos_dict[concepto.clave] = concepto
        # Ordenar las claves, primero las que empiezan con P
        for concepto in conceptos:
            if concepto.clave.startswith("D"):
                conceptos_dict[concepto.clave] = concepto
        # Al final agregar las claves que NO empiezan con P o D
        for concepto in conceptos:
            if not concepto.clave.startswith("P") and not concepto.clave.startswith("D"):
                conceptos_dict[concepto.clave] = concepto

    # Si el tipo es APOYO ANUAL armar un diccionario con PAZ, DAZ y D62
    if tipo == "APOYO ANUAL":
        conceptos_dict = {
            "PAZ": None,  # Percepcion de Apoyo Anual
            "DAZ": None,  # Deduccion ISR Apoyo Anual
            "D62": None,  # Deduccion Pension Alimenticia
        }

    # Si no hay conceptos, provocar error y salir
    if len(conceptos_dict) == 0:
        mensaje = f"No hay conceptos para el tipo {tipo}"
        actualizar_quincena_producto(quincena_producto_id, quincena.id, fuente, [mensaje])
        raise MyEmptyError(mensaje)

    # Mandar mensaje de inicio a la bitacora
    descripcion = f"timbrados {quincena_clave} {tipo} modelos {modelos}"
    bitacora.info("Inicia crear %s", descripcion)

    # Consultar Nominas activas de la quincena, del tipo dado, juntar con personas
    nominas = (
        session.query(Nomina)
        .join(Persona)
        .filter(Nomina.quincena_id == quincena.id)
        .filter(Nomina.tipo == tipo)
        .filter(Nomina.estatus == "A")
        .filter(Persona.modelo.in_(modelos))
        .order_by(Persona.rfc)
        .all()
    )

    # Si no hay registros, provocar error
    if len(nominas) == 0:
        mensaje = f"No hay registros en nominas de tipo {tipo}"
        actualizar_quincena_producto(quincena_producto_id, quincena.id, fuente, [mensaje])
        raise MyEmptyError(mensaje)

    # Iniciar el archivo XLSX
    libro = Workbook()

    # Tomar la hoja del libro XLSX
    hoja = libro.active

    # Encabezados primera parte
    encabezados_parte_1 = [
        "CONSECUTIVO",
        "NUMERO DE EMPLEADO",
        "APELLIDO PRIMERO",
        "APELLIDO SEGUNDO",
        "NOMBRES",
        "RFC",
        "CURP",
        "NO DE SEGURIDAD SOCIAL",
        "FECHA DE INGRESO",
        "CLAVE TIPO NOMINA",
        "SINDICALIZADO",
        "CLAVE BANCO SAT",
        "NUMERO DE CUENTA",
        "PLANTA",
        "SALARIO DIARIO",
        "SALARIO INTEGRADO",
        "FECHA INICIAL PERIODO",
        "FECHA FINAL PERIODO",
        "FECHA DE PAGO",
        "DIAS TRABAJADOS",
        "RFC DEL PATRON",
        "CLASE RIESGO PUESTO SAT",
        "TIPO CONTRATO SAT",
        "JORNADA SAT",
        "TIPO REGIMEN SAT",
        "ANIO",
        "MES",
        "PERIODO NOM",
        "CLAVE COMPANIA",
        "RFC COMPANIA",
        "NOMBRE COMPANIA",
        "CP DE LA COMPANIA",
        "REGIMEN FISCAL",
        "ESTADO SAT",
        "CLAVE PLANTA U OFICINA",
        "PLANTA U OFICINA",
        "CLAVE CENTRO COSTOS",
        "CENTRO COSTOS",
        "FORMA DE PAGO",
        "CLAVE DEPARTAMENTO",
        "NOMBRE DEPARTAMENTO",
        "NOMBRE PUESTO",
    ]

    # Encabezados segunda parte, tomar las claves de conceptos_dict
    encabezados_parte_2 = list(conceptos_dict.keys())

    # Encabezados tercera parte
    encabezados_parte_3 = [
        "ORIGEN RECURSO",
        "MONTO DEL RECURSO",
        "CODIGO POSTAL FISCAL",
        "MODELO",
        "PUESTO EQUIVALENTE",
        "PLAZA",
        "NIVEL",
    ]

    # Agregar la fila con las cabeceras de las columnas
    hoja.append(encabezados_parte_1 + encabezados_parte_2 + encabezados_parte_3)

    # Inicializar el contador
    contador = 0
    personas_sin_cuentas = []

    # Bucle para crear cada fila del archivo XLSX
    for nomina in nominas:

        # Si modelos no es None y el modelo de la persona NO esta en modelos, se omite
        # if modelos is not None and nomina.persona.modelo not in modelos:
        #     continue

        # De las cuentas hay que tomar la que NO tenga la clave 9, porque esa clave es la de DESPENSA
        su_cuenta = None
        su_cuenta_id = 0
        for cuenta in nomina.persona.cuentas:
            if cuenta.estatus == "A" and cuenta.banco.clave != "9" and cuenta.id > su_cuenta_id:
                su_cuenta = cuenta
                break

        # Si no tiene cuenta bancaria, entonces se agrega a la lista de personas_sin_cuentas y se salta
        if su_cuenta is None:
            personas_sin_cuentas.append(nomina.persona.rfc)
            continue

        # Incrementar contador
        contador += 1

        # Fila parte 1
        fila_parte_1 = [
            contador,  # CONSECUTIVO
            nomina.persona.num_empleado,  # NUMERO DE EMPLEADO
            nomina.persona.apellido_primero,  # APELLIDO PRIMERO
            nomina.persona.apellido_segundo,  # APELLIDO SEGUNDO
            nomina.persona.nombres,  # NOMBRES
            nomina.persona.rfc,  # RFC
            nomina.persona.curp,  # CURP
            nomina.persona.seguridad_social,  # NO DE SEGURIDAD SOCIAL
            nomina.persona.ingreso_pj_fecha,  # FECHA DE INGRESO
            "O" if tipo == "SALARIO" else "E",  # CLAVE TIPO NOMINA ordinarias es O, extraordinarias es E
            "SI" if nomina.persona.modelo == 2 else "NO",  # SINDICALIZADO modelo es 2
            su_cuenta.banco.clave_dispersion_pensionados,  # CLAVE BANCO SAT
            su_cuenta.num_cuenta,  # NUMERO DE CUENTA
            "",  # PLANTA nula
            nomina.persona.tabulador.salario_diario,  # SALARIO DIARIO
            nomina.persona.tabulador.salario_diario_integrado,  # SALARIO INTEGRADO
            quincena_fecha_inicial,  # FECHA INICIAL PERIODO
            quincena_fecha_final,  # FECHA FINAL PERIODO
            nomina.fecha_pago,  # FECHA DE PAGO
            "15" if tipo == "SALARIO" else "1",  # DIAS TRABAJADOS cuando es anual se pone 1
            PATRON_RFC,  # RFC DEL PATRON
            "1",  # CLASE RIESGO PUESTO es 1
            "01",  # TIPO CONTRATO SAT
            "08",  # JORNADA SAT
            "02",  # TIPO REGIMEN SAT
            nomina.fecha_pago.year,  # ANIO
            nomina.fecha_pago.month,  # MES
            quincena.clave[-2:],  # PERIODO NOM los dos ultimos digitos de la clave de la quincena
            "",  # CLAVE COMPANIA nulo
            COMPANIA_RFC,  # RFC COMPANIA
            COMPANIA_NOMBRE,  # NOMBRE COMPANIA
            COMPANIA_CP,  # CP DE LA COMPANIA
            "603",  # REGIMEN FISCAL solo la clave 603 PERSONAS MORALES CON FINES NO LUCRATIVOS
            "COA",  # ESTADO SAT
            "",  # CLAVE PLANTA U OFICINA nulo
            "",  # PLANTA U OFICINA nulo
            "",  # CLAVE CENTRO COSTOS nulo
            "",  # CENTRO COSTOS nulo
            "04" if tipo == "SALARIO" else "99",  # FORMA DE PAGO para la ayuda es 99 y para los salarios es 04
            nomina.centro_trabajo.clave,  # CLAVE DEPARTAMENTO
            nomina.centro_trabajo.descripcion,  # NOMBRE DEPARTAMENTO
            nomina.persona.tabulador.puesto.clave,  # NOMBRE PUESTO por lo pronto es la clave del puesto
        ]

        # Fila parte 2
        fila_parte_2 = []
        if tipo == "SALARIO":
            # Consultar TODAS las P-D de la quincena y la persona
            percepciones_deducciones = (
                session.query(PercepcionDeduccion)
                .filter_by(quincena_id=quincena.id)
                .filter_by(persona_id=nomina.persona_id)
                .all()
            )
            # Bucle por las P-D para definir un diccionario con las claves y los importes
            percepciones_deducciones_dict = {}
            for percepcion_deduccion in percepciones_deducciones:
                percepciones_deducciones_dict[percepcion_deduccion.concepto.clave] = percepcion_deduccion.importe
            # Bucle por los conceptos
            for _, concepto in conceptos_dict.items():
                # Si el concepto esta en el diccionario de P-D, entonces agregar el importe
                if concepto.clave in percepciones_deducciones_dict:
                    fila_parte_2.append(percepciones_deducciones_dict[concepto.clave])
                else:
                    fila_parte_2.append(0)  # De lo contrario agregar cero
        elif tipo == "APOYO ANUAL":
            # Consultar la PercepcionDeduccion con concepto PAZ
            percepcion_deduccion_paz = (
                session.query(PercepcionDeduccion)
                .join(Concepto)
                .filter(PercepcionDeduccion.quincena_id == quincena.id)
                .filter(PercepcionDeduccion.persona_id == nomina.persona_id)
                .filter(PercepcionDeduccion.tipo == "APOYO ANUAL")
                .filter(Concepto.clave == "PAZ")
                .first()
            )
            fila_parte_2.append(percepcion_deduccion_paz.importe if percepcion_deduccion_paz is not None else 0)
            # Consultar la PercepcionDeduccion con concepto DAZ
            percepcion_deduccion_daz = (
                session.query(PercepcionDeduccion)
                .join(Concepto)
                .filter(PercepcionDeduccion.quincena_id == quincena.id)
                .filter(PercepcionDeduccion.persona_id == nomina.persona_id)
                .filter(PercepcionDeduccion.tipo == "APOYO ANUAL")
                .filter(Concepto.clave == "DAZ")
                .first()
            )
            fila_parte_2.append(percepcion_deduccion_daz.importe if percepcion_deduccion_daz is not None else 0)
            # Consultar la PercepcionDeduccion con concepto D62
            percepcion_deduccion_d62 = (
                session.query(PercepcionDeduccion)
                .join(Concepto)
                .filter(PercepcionDeduccion.quincena_id == quincena.id)
                .filter(PercepcionDeduccion.persona_id == nomina.persona_id)
                .filter(PercepcionDeduccion.tipo == "APOYO ANUAL")
                .filter(Concepto.clave == "D62")
                .first()
            )
            fila_parte_2.append(percepcion_deduccion_d62.importe if percepcion_deduccion_d62 is not None else 0)

        # Si el codigo postal fiscal es cero, entonces se usa 00000
        codigo_postal_fiscal = "00000"
        if nomina.persona.codigo_postal_fiscal:
            codigo_postal_fiscal = str(nomina.persona.codigo_postal_fiscal).zfill(5)

        # Consultar la clave de la plaza a partir de persona.ultimo_plaza_id
        plaza_clave = ""
        if nomina.persona.ultimo_plaza_id:
            plaza = Plaza.query.filter_by(id=nomina.persona.ultimo_plaza_id).first()
            if plaza is not None:
                plaza_clave = plaza.clave

        # Fila parte 3
        fila_parte_3 = [
            "IP",  # ORIGEN RECURSO
            "100",  # MONTO DEL RECURSO
            codigo_postal_fiscal,  # CODIGO POSTAL FISCAL
            nomina.persona.modelo,  # MODELO
            nomina.persona.puesto_equivalente,  # PUESTO EQUIVALENTE
            plaza_clave,  # PLAZA
            nomina.persona.nivel,  # NIVEL
        ]

        # Agregar la fila
        hoja.append(fila_parte_1 + fila_parte_2 + fila_parte_3)

        # Mandar a la bitacora el contador cada 100 filas
        if contador % 100 == 0:
            bitacora.info("Van %s filas en %s", contador, descripcion)

    # Si el contador es cero, provocar error
    if contador == 0:
        mensaje = "No hubo filas que agregar al archivo XLSX"
        actualizar_quincena_producto(quincena_producto_id, quincena.id, fuente, [mensaje])
        raise MyEmptyError(mensaje)

    # Determinar la fecha y tiempo actual en la zona horaria
    ahora = datetime.now(tz=pytz.timezone(TIMEZONE))

    # Determinar el nombre del archivo XLSX
    if tipo == "SALARIO":
        prefijo = "timbrados"
        if modelos == [3]:
            prefijo = "timbrados_pensionados"
        elif modelos == [1, 2]:
            prefijo = "timbrados_empleados_activos"
    elif tipo == "AGUINALDO":
        prefijo = "timbrados_aguinaldos"
    elif tipo == "APOYO ANUAL":
        prefijo = "timbrados_apoyos_anuales"
    nombre_archivo_xlsx = f"{prefijo}_{quincena_clave}_{ahora.strftime('%Y-%m-%d_%H%M%S')}.xlsx"

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
                actualizar_quincena_producto(quincena_producto_id, quincena.id, fuente, [mensaje_fallo_gcs])
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
    mensaje_termino = f"Se generaron {contador} filas en {nombre_archivo_xlsx}"
    mensajes.append(mensaje_termino)

    # Actualizar quincena_producto
    actualizar_quincena_producto(
        quincena_producto_id=quincena_producto_id,
        quincena_id=quincena.id,
        fuente=fuente,
        mensajes=mensajes,
        archivo=nombre_archivo_xlsx,
        url=public_url,
        es_satisfactorio=es_satisfactorio,
    )

    # Entregar mensaje de termino
    mensaje_termino = f"Termina crear timbrados: {mensaje_termino}"
    bitacora.info(mensaje_termino)
    return mensaje_termino
