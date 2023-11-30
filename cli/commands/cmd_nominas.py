"""
CLI Nominas
"""
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import click
import xlrd
from openpyxl import Workbook

from lib.fechas import quincena_to_fecha, quinquenio_count
from lib.safe_string import QUINCENA_REGEXP, safe_clave, safe_string
from perseo.app import create_app
from perseo.blueprints.bancos.models import Banco
from perseo.blueprints.centros_trabajos.models import CentroTrabajo
from perseo.blueprints.conceptos.models import Concepto
from perseo.blueprints.conceptos_productos.models import ConceptoProducto
from perseo.blueprints.nominas.models import Nomina
from perseo.blueprints.percepciones_deducciones.models import PercepcionDeduccion
from perseo.blueprints.personas.models import Persona
from perseo.blueprints.plazas.models import Plaza
from perseo.blueprints.productos.models import Producto
from perseo.blueprints.puestos.models import Puesto
from perseo.blueprints.quincenas.models import Quincena
from perseo.blueprints.tabuladores.models import Tabulador
from perseo.extensions import database

EXPLOTACION_BASE_DIR = os.environ.get("EXPLOTACION_BASE_DIR")

APOYOS_FILENAME_XLS = "Apoyos.XLS"
BONOS_FILENAME_XLS = "Bonos.XLS"
NOMINAS_FILENAME_XLS = "NominaFmt2.XLS"

PATRON_RFC = "PJE901211TI9"
COMPANIA_NOMBRE = "PODER JUDICIAL DEL ESTADO DE COAHUILA DE ZARAGOZA"
COMPANIA_RFC = PATRON_RFC
COMPANIA_CP = "25000"

app = create_app()
app.app_context().push()
database.app = app


@click.group()
def cli():
    """Nominas"""


@click.command()
@click.argument("quincena_clave", type=str)
@click.argument("fecha_pago_str", type=str)
def alimentar(quincena_clave: str, fecha_pago_str: str):
    """Alimentar nominas"""

    # Validar quincena
    if re.match(QUINCENA_REGEXP, quincena_clave) is None:
        click.echo("ERROR: Quincena inválida")
        sys.exit(1)

    # Definir la fecha_final en base a la clave de la quincena
    try:
        fecha_final = quincena_to_fecha(quincena_clave, dame_ultimo_dia=True)
    except ValueError:
        click.echo("ERROR: Quincena inválida")
        sys.exit(1)

    # Validar fecha_pago
    try:
        fecha_pago = datetime.strptime(fecha_pago_str, "%Y-%m-%d")
    except ValueError:
        click.echo("ERROR: Fecha de pago inválida")
        sys.exit(1)

    # Iniciar sesion con la base de datos para que la alimentacion sea rapida
    sesion = database.session

    # Validar el directorio donde espera encontrar los archivos de explotacion
    if EXPLOTACION_BASE_DIR is None:
        click.echo("ERROR: Variable de entorno EXPLOTACION_BASE_DIR no definida.")
        sys.exit(1)

    # Validar si existe el archivo
    ruta = Path(EXPLOTACION_BASE_DIR, quincena_clave, NOMINAS_FILENAME_XLS)
    if not ruta.exists():
        click.echo(f"ERROR: {str(ruta)} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        click.echo(f"ERROR: {str(ruta)} no es un archivo.")
        sys.exit(1)

    # Consultar quincena
    quincena = Quincena.query.filter_by(clave=quincena_clave).first()

    # Si existe la quincena, pero no esta ABIERTA, entonces se termina
    if quincena and quincena.estado != "ABIERTA":
        click.echo(f"ERROR: Quincena {quincena_clave} no esta ABIERTA.")
        sys.exit(1)

    # Si existe la quincena, pero ha sido eliminada, entonces se termina
    if quincena and quincena.estatus != "A":
        click.echo(f"ERROR: Quincena {quincena_clave} esta sido eliminada.")
        sys.exit(1)

    # Si no existe la quincena, se agrega
    if quincena is None:
        quincena = Quincena(clave=quincena_clave, estado="ABIERTA")
        sesion.add(quincena)
        sesion.commit()

    # Abrir el archivo XLS con xlrd
    libro = xlrd.open_workbook(str(ruta))

    # Obtener la primera hoja
    hoja = libro.sheet_by_index(0)

    # Iniciar contadores
    contador = 0
    centros_trabajos_insertados_contador = 0
    personas_insertadas_contador = 0
    personas_sin_puestos = []
    personas_sin_tabulador = []
    plazas_insertadas_contador = 0

    # Bucle por cada fila
    click.echo("Alimentando Nominas: ", nl=False)
    for fila in range(1, hoja.nrows):
        # Tomar las columnas
        centro_trabajo_clave = hoja.cell_value(fila, 1)
        rfc = hoja.cell_value(fila, 2)
        nombre_completo = hoja.cell_value(fila, 3)
        plaza_clave = hoja.cell_value(fila, 8)
        percepcion = int(hoja.cell_value(fila, 12)) / 100.0
        deduccion = int(hoja.cell_value(fila, 13)) / 100.0
        impte = int(hoja.cell_value(fila, 14)) / 100.0
        modelo = int(hoja.cell_value(fila, 236))
        num_empleado = int(hoja.cell_value(fila, 240))

        # Tomar las columnas necesarias para el timbrado
        puesto_clave = safe_clave(hoja.cell_value(fila, 20))
        nivel = int(hoja.cell_value(fila, 9))
        quincena_ingreso = str(int(hoja.cell_value(fila, 19)))

        # Si el modelo es 2, entonces es Sindicalizado y se calculan los quinquenios
        quinquenios = 0
        if modelo == 2:
            # Calcular la cantidad de quinquenios
            fecha_ingreso = quincena_to_fecha(quincena_ingreso, dame_ultimo_dia=False)
            quinquenios = quinquenio_count(fecha_ingreso, fecha_final)

        # Separar nombre_completo, en apellido_primero, apellido_segundo y nombres
        separado = safe_string(nombre_completo, save_enie=True).split(" ")
        apellido_primero = separado[0]
        apellido_segundo = separado[1]
        nombres = " ".join(separado[2:])

        # Consultar el Centro de Trabajo, si no existe se agrega
        centro_trabajo = CentroTrabajo.query.filter_by(clave=centro_trabajo_clave).first()
        if centro_trabajo is None:
            centro_trabajo = CentroTrabajo(clave=centro_trabajo_clave, descripcion="ND")
            sesion.add(centro_trabajo)
            centros_trabajos_insertados_contador += 1

        # Consultar el puesto, si no existe se agrega a personas_sin_puestos y se omite
        puesto = Puesto.query.filter_by(clave=puesto_clave).first()
        if puesto is None:
            personas_sin_puestos.append(rfc)
            continue

        # Consultar el tabulador que coincida con puesto_clave, modelo, nivel y quinquenios
        tabulador = (
            Tabulador.query.filter_by(puesto_id=puesto.id)
            .filter_by(modelo=modelo)
            .filter_by(nivel=nivel)
            .filter_by(quinquenio=quinquenios)
            .first()
        )

        # Si no existe el tabulador, se agrega a personas_sin_tabulador y se omite
        if tabulador is None:
            personas_sin_tabulador.append(rfc)
            continue

        # Revisar si la Persona existe, de lo contrario insertarlo
        persona = Persona.query.filter_by(rfc=rfc).first()
        if persona is None:
            persona = Persona(
                tabulador_id=tabulador.id,
                rfc=rfc,
                nombres=nombres,
                apellido_primero=apellido_primero,
                apellido_segundo=apellido_segundo,
                modelo=modelo,
                num_empleado=num_empleado,
            )
            sesion.add(persona)
            personas_insertadas_contador += 1

        # TODO: Con la persona...
        # 1. revisar si hubo cambios en sus datos,
        # 2. revisar si cambio de tabulador, tal vez revisando la quincena anterior
        # Si hay cambios, actualizar la persona, tabulador y puesto

        # Revisar si la Plaza existe, de lo contrario insertarla
        plaza = Plaza.query.filter_by(clave=plaza_clave).first()
        if plaza is None:
            plaza = Plaza(clave=plaza_clave, descripcion="ND")
            sesion.add(plaza)
            plazas_insertadas_contador += 1

        # Bucle entre P-D para determinar el tipo entre SALARIO y DESPENSA
        nomina_tipo = None
        col_num = 26
        while True:
            # Tomar el tipo y el conc para armar la clave del concepto
            tipo = safe_string(hoja.cell_value(fila, col_num))
            conc = safe_string(hoja.cell_value(fila, col_num + 1))
            concepto_clave = f"{tipo}{conc}"

            # Si el tipo es un texto vacio, se rompe el ciclo
            if tipo == "":
                break

            # Si el concepto_clave es PME, entonces es DESPENSA y se termina este ciclo
            if concepto_clave == "PME":
                nomina_tipo = Nomina.TIPOS["DESPENSA"]
                break

            # Incrementar col_num en SEIS
            col_num += 6

            # Romper el ciclo cuando se llega a la columna
            if col_num > 236:
                break

        # Si no se encontro el tipo, entonces es SALARIO
        if nomina_tipo is None:
            nomina_tipo = Nomina.TIPOS["SALARIO"]

        # Alimentar nomina
        nomina = Nomina(
            centro_trabajo=centro_trabajo,
            persona=persona,
            plaza=plaza,
            quincena=quincena,
            percepcion=percepcion,
            deduccion=deduccion,
            importe=impte,
            tipo=nomina_tipo,
            fecha_pago=fecha_pago,
        )
        sesion.add(nomina)

        # Incrementar contador
        contador += 1
        if contador % 100 == 0:
            click.echo(click.style(".", fg="cyan"), nl=False)

    # Poner avance de linea
    click.echo("")

    # Cerrar la sesion para que se guarden todos los datos en la base de datos
    sesion.commit()
    sesion.close()

    # Si hubo centros_trabajos_insertados, mostrar contador
    if centros_trabajos_insertados_contador > 0:
        click.echo(click.style(f"  Se insertaron {centros_trabajos_insertados_contador} Centros de Trabajo", fg="green"))

    # Si hubo personas insertadas, mostrar contador
    if personas_insertadas_contador > 0:
        click.echo(click.style(f"  Se insertaron {personas_insertadas_contador} Personas", fg="green"))

    # Si hubo plazas insertadas, mostrar contador
    if plazas_insertadas_contador > 0:
        click.echo(click.style(f"  Se insertaron {plazas_insertadas_contador} Plazas", fg="green"))

    # Si hubo personas_sin_puestos, mostrarlas en pantalla
    if len(personas_sin_puestos) > 0:
        click.echo(click.style(f"  Hubo {len(personas_sin_puestos)} Personas sin puestos:", fg="yellow"))
        # click.echo(click.style(f"  {', '.join(personas_sin_puestos)}", fg="yellow"))

    # Si hubo personas_sin_tabulador, mostrarlas en pantalla
    if len(personas_sin_tabulador) > 0:
        click.echo(click.style(f"  Hubo {len(personas_sin_tabulador)} Personas sin tabulador:", fg="yellow"))
        click.echo(click.style(f"  {', '.join(personas_sin_tabulador)}", fg="yellow"))

    # Mensaje termino
    click.echo(click.style(f"  Alimentar Nominas: {contador} insertadas en la quincena {quincena_clave}.", fg="green"))


@click.command()
@click.argument("quincena_clave", type=str)
@click.argument("fecha_pago_str", type=str)
def alimentar_apoyos_anuales(quincena_clave: str, fecha_pago_str: str):
    """Alimentar apoyos anuales"""

    # Validar quincena
    if re.match(QUINCENA_REGEXP, quincena_clave) is None:
        click.echo("ERROR: Quincena inválida")
        sys.exit(1)

    # Definir la fecha_final en base a la clave de la quincena
    try:
        fecha_final = quincena_to_fecha(quincena_clave, dame_ultimo_dia=True)
    except ValueError:
        click.echo("ERROR: Quincena inválida")
        sys.exit(1)

    # Validar fecha_pago
    try:
        fecha_pago = datetime.strptime(fecha_pago_str, "%Y-%m-%d")
    except ValueError:
        click.echo("ERROR: Fecha de pago inválida")
        sys.exit(1)

    # Iniciar sesion con la base de datos para que la alimentacion sea rapida
    sesion = database.session

    # Validar el directorio donde espera encontrar los archivos de explotacion
    if EXPLOTACION_BASE_DIR is None:
        click.echo("ERROR: Variable de entorno EXPLOTACION_BASE_DIR no definida.")
        sys.exit(1)

    # Validar si existe el archivo
    ruta = Path(EXPLOTACION_BASE_DIR, quincena_clave, APOYOS_FILENAME_XLS)
    if not ruta.exists():
        click.echo(f"ERROR: {str(ruta)} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        click.echo(f"ERROR: {str(ruta)} no es un archivo.")
        sys.exit(1)

    # Consultar quincena
    quincena = Quincena.query.filter_by(clave=quincena_clave).first()

    # Si existe la quincena, pero no esta ABIERTA, entonces se termina
    if quincena and quincena.estado != "ABIERTA":
        click.echo(f"ERROR: Quincena {quincena_clave} no esta ABIERTA.")
        sys.exit(1)

    # Si existe la quincena, pero ha sido eliminada, entonces se termina
    if quincena and quincena.estatus != "A":
        click.echo(f"ERROR: Quincena {quincena_clave} esta sido eliminada.")
        sys.exit(1)

    # Si no existe la quincena, se agrega
    if quincena is None:
        quincena = Quincena(clave=quincena_clave, estado="ABIERTA")
        sesion.add(quincena)
        sesion.commit()

    # Consultar el concepto con clave PAZ que es APOYO ANUAL, si no se encuentra, error
    concepto_paz = Concepto.query.filter_by(clave="PAZ").first()
    if concepto_paz is None:
        click.echo("ERROR: No existe el concepto con clave PAZ")
        sys.exit(1)

    # Consultar el concepto con clave DAZ que es ISR DE APOYO DE FIN DE AÑO, si no se encuentra, error
    concepto_daz = Concepto.query.filter_by(clave="DAZ").first()
    if concepto_daz is None:
        click.echo("ERROR: No existe el concepto con clave DAZ")
        sys.exit(1)

    # Consultar el concepto con clave D62 que es PENSION ALIMENTICIA, si no se encuentra, error
    concepto_d62 = Concepto.query.filter_by(clave="D62").first()
    if concepto_d62 is None:
        click.echo("ERROR: No existe el concepto con clave D62")
        sys.exit(1)

    # Abrir el archivo XLS con xlrd
    libro = xlrd.open_workbook(str(ruta))

    # Obtener la primera hoja
    hoja = libro.sheet_by_index(0)

    # Iniciar contadores
    contador = 0
    centros_trabajos_inexistentes = []
    nominas_existentes = []
    personas_inexistentes = []
    plazas_inexistentes = []

    # Bucle por cada fila
    click.echo("Alimentando Apoyos: ", nl=False)
    for fila in range(1, hoja.nrows):
        # Tomar las columnas
        rfc = hoja.cell_value(fila, 0).strip().upper()
        centro_trabajo_clave = hoja.cell_value(fila, 1).strip().upper()
        plaza_clave = hoja.cell_value(fila, 2).strip().upper()
        # puesto = hoja.cell_value(fila, 3)
        percepcion = float(hoja.cell_value(fila, 4))
        deduccion = float(hoja.cell_value(fila, 5))
        impte = float(hoja.cell_value(fila, 6))
        # fecha_pago es la columna 7
        # desde = hoja.cell_value(fila, 8)
        # hasta = hoja.cell_value(fila, 9)
        try:
            impte_concepto_d62 = float(hoja.cell_value(fila, 10))
        except ValueError:
            impte_concepto_d62 = 0.0

        # Consultar la persona, si no existe, se agrega a la lista de personas_inexistentes y se salta
        persona = Persona.query.filter_by(rfc=rfc).first()
        if persona is None:
            personas_inexistentes.append(rfc)
            continue

        # Consultar el Centro de Trabajo, si no existe se agrega a la lista de centros_trabajos_inexistentes y se salta
        centro_trabajo = CentroTrabajo.query.filter_by(clave=centro_trabajo_clave).first()
        if centro_trabajo is None:
            centros_trabajos_inexistentes.append(centro_trabajo_clave)
            continue

        # Consultar la Plaza, si no existe se agrega a la lista de plazas_inexistentes y se salta
        plaza = Plaza.query.filter_by(clave=plaza_clave).first()
        if plaza is None:
            plazas_inexistentes.append(plaza_clave)
            continue

        # Revisar que en nominas no exista una nomina con la misma persona, quincena y tipo APOYO ANUAL, si existe se omite
        nominas_posibles = (
            Nomina.query.filter_by(persona_id=persona.id)
            .filter_by(quincena_id=quincena.id)
            .filter_by(tipo="APOYO ANUAL")
            .filter_by(estatus="A")
            .all()
        )
        if len(nominas_posibles) > 0:
            nominas_existentes.append(rfc)
            continue

        # Alimentar percepcion en PercepcionDeduccion, con concepto PAZ
        percepcion_deduccion_paz = PercepcionDeduccion(
            centro_trabajo=centro_trabajo,
            concepto=concepto_paz,
            persona=persona,
            plaza=plaza,
            quincena=quincena,
            importe=percepcion,
        )
        sesion.add(percepcion_deduccion_paz)

        # Alimentar deduccion en PercepcionDeduccion, con concepto DAZ
        percepcion_deduccion_daz = PercepcionDeduccion(
            centro_trabajo=centro_trabajo,
            concepto=concepto_daz,
            persona=persona,
            plaza=plaza,
            quincena=quincena,
            importe=deduccion,
        )
        sesion.add(percepcion_deduccion_daz)

        # Si tiene concepto_d62, alimentar registro en PercepcionDeduccion
        if impte_concepto_d62 > 0:
            percepcion_deduccion_d62 = PercepcionDeduccion(
                centro_trabajo=centro_trabajo,
                concepto=concepto_d62,
                persona=persona,
                plaza=plaza,
                quincena=quincena,
                importe=impte_concepto_d62,
            )
            sesion.add(percepcion_deduccion_d62)

            # Sumar a deduccion el impte_concepto_d62
            deduccion += impte_concepto_d62

        # Alimentar registro en Nomina
        nomina = Nomina(
            centro_trabajo=centro_trabajo,
            persona=persona,
            plaza=plaza,
            quincena=quincena,
            percepcion=percepcion,
            deduccion=deduccion,
            importe=impte,
            tipo="APOYO ANUAL",
            fecha_pago=fecha_pago,
        )
        sesion.add(nomina)

        # Incrementar contador
        contador += 1
        if contador % 100 == 0:
            click.echo(click.style(".", fg="cyan"), nl=False)

    # Poner avance de linea
    click.echo("")

    # Cerrar la sesion para que se guarden todos los datos en la base de datos
    sesion.commit()
    sesion.close()

    # Si hubo centros_trabajos_inexistentes, mostrarlos
    if len(centros_trabajos_inexistentes) > 0:
        click.echo(click.style(f"  Hubo {len(centros_trabajos_inexistentes)} Centros de Trabajo que no existen:", fg="yellow"))
        click.echo(click.style(f"  {', '.join(centros_trabajos_inexistentes)}", fg="yellow"))

    # Si hubo nominas_existentes, mostrarlos
    if len(nominas_existentes) > 0:
        click.echo(click.style(f"  Hubo {len(nominas_existentes)} Apoyos Anuales que ya existen:", fg="yellow"))
        click.echo(click.style(f"  {', '.join(nominas_existentes)}", fg="yellow"))

    # Si hubo plazas_inexistentes, mostrarlos
    if len(plazas_inexistentes) > 0:
        click.echo(click.style(f"  Hubo {len(plazas_inexistentes)} Plazas que no existen:", fg="yellow"))
        click.echo(click.style(f"  {', '.join(plazas_inexistentes)}", fg="yellow"))

    # Si hubo personas_inexistentes, mostrar contador
    if len(personas_inexistentes) > 0:
        click.echo(click.style(f"  Hubo {len(personas_inexistentes)} Personas que no existen:", fg="yellow"))
        click.echo(click.style(f"  {', '.join(personas_inexistentes)}", fg="yellow"))

    # Mensaje termino
    click.echo(click.style(f"  Alimentar Apoyos Anuales:  {contador} insertadas en la quincena {quincena_clave}.", fg="green"))


@click.command()
@click.argument("quincena_clave", type=str)
def generar_nominas(quincena_clave: str):
    """Generar archivo XLSX con las nominas de una quincena"""

    # Validar quincena
    if re.match(QUINCENA_REGEXP, quincena_clave) is None:
        click.echo("ERROR: Quincena inválida.")
        sys.exit(1)

    # Iniciar sesion con la base de datos para que la alimentacion sea rapida
    sesion = database.session

    # Consultar quincena
    quincena = Quincena.query.filter_by(clave=quincena_clave).first()

    # Si no existe la quincena, entonces se termina
    if quincena is None:
        click.echo(f"ERROR: Quincena {quincena_clave} no existe.")
        sys.exit(1)

    # Si existe la quincena, pero no esta ABIERTA, entonces se termina
    if quincena.estado != "ABIERTA":
        click.echo(f"ERROR: Quincena {quincena_clave} no esta ABIERTA.")
        sys.exit(1)

    # Si existe la quincena, pero ha sido eliminada, entonces se termina
    if quincena.estatus != "A":
        click.echo(f"ERROR: Quincena {quincena_clave} esta eliminada.")
        sys.exit(1)

    # Consultar las nominas de la quincena, solo tipo SALARIO
    nominas = Nomina.query.filter_by(quincena_id=quincena.id).filter_by(tipo="SALARIO").filter_by(estatus="A").all()

    # Si no hay nominas, entonces se termina
    if len(nominas) == 0:
        click.echo(f"AVISO: No hay nominas de tipo SALARIO en la quincena {quincena_clave}.")
        sys.exit(0)

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
        # Si el modelo de la persona es 3, se omite
        if nomina.persona.modelo == 3:
            continue

        # Tomar las cuentas de la persona
        cuentas = nomina.persona.cuentas

        # Si no tiene cuentas, entonces se agrega a la lista de personas_sin_cuentas y se salta
        if len(cuentas) == 0:
            personas_sin_cuentas.append(nomina.persona.rfc)
            continue

        # Tomar la cuenta de la persona que no tenga la clave 9, porque esa clave es la de DESPENSA
        su_cuenta = None
        for cuenta in cuentas:
            if cuenta.banco.clave != "9" and cuenta.estatus == "A":
                su_cuenta = cuenta
                break

        # Si no tiene cuenta bancaria, entonces se agrega a la lista de personas_sin_cuentas y se salta
        if su_cuenta is None:
            personas_sin_cuentas.append(nomina.persona.rfc)
            continue

        # Tomar el banco de la cuenta de la persona
        su_banco = su_cuenta.banco

        # Incrementer el consecutivo_generado del banco
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

        # Incrementar contador
        contador += 1
        if contador % 100 == 0:
            click.echo(f"  Van {contador}...")

    # Actualizar los consecutivos de cada banco
    sesion.commit()

    # Determinar el nombre del archivo XLSX, juntando 'nominas' con la quincena y la fecha como YYYY-MM-DD HHMMSS
    nombre_archivo = f"nominas_{quincena_clave}_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.xlsx"

    # Guardar el archivo XLSX
    libro.save(nombre_archivo)

    # Si hubo personas sin cuentas, entonces mostrarlas en pantalla
    if len(personas_sin_cuentas) > 0:
        click.echo(click.style(f"  Hubo {len(personas_sin_cuentas)} Personas sin cuentas:", fg="yellow"))
        click.echo(click.style(f"  {', '.join(personas_sin_cuentas)}", fg="yellow"))

    # Mensaje termino
    click.echo(f"  Generar Nominas: {contador} filas en {nombre_archivo}")


@click.command()
@click.argument("quincena_clave", type=str)
def generar_monederos(quincena_clave: str):
    """Generar archivo XLSX con los monederos de una quincena"""

    # Validar quincena
    if re.match(QUINCENA_REGEXP, quincena_clave) is None:
        click.echo("ERROR: Quincena inválida")
        sys.exit(1)

    # Iniciar sesion con la base de datos para que la alimentacion sea rapida
    sesion = database.session

    # Consultar quincena
    quincena = Quincena.query.filter_by(clave=quincena_clave).first()

    # Si no existe la quincena, entonces se termina
    if quincena is None:
        click.echo(f"ERROR: Quincena {quincena_clave} no existe.")
        sys.exit(1)

    # Si existe la quincena, pero no esta ABIERTA, entonces se termina
    if quincena.estado != "ABIERTA":
        click.echo(f"ERROR: Quincena {quincena_clave} no esta ABIERTA.")
        sys.exit(1)

    # Si existe la quincena, pero ha sido eliminada, entonces se termina
    if quincena.estatus != "A":
        click.echo(f"ERROR: Quincena {quincena_clave} ha sido eliminada.")
        sys.exit(1)

    # Cargar solo el banco con la clave 9 que es PREVIVALE
    banco = Banco.query.filter_by(clave="9").first()
    if banco is None:
        click.echo("ERROR: No existe el banco con clave 9")
        sys.exit(1)

    # Igualar el consecutivo_generado al consecutivo
    banco.consecutivo_generado = banco.consecutivo

    # Consultar las nominas de la quincena solo tipo DESPENSA
    nominas = Nomina.query.filter_by(quincena_id=quincena.id).filter_by(tipo="DESPENSA").filter_by(estatus="A").all()

    # Si no hay nominas, entonces se termina
    if len(nominas) == 0:
        click.echo(f"AVISO: No hay nominas de tipo DESPENSA en la quincena {quincena_clave}.")
        sys.exit(0)

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

        # Incrementar contador
        contador += 1
        if contador % 100 == 0:
            click.echo(f"  Van {contador}...")

    # Actualizar los consecutivo_generado de cada banco
    sesion.commit()

    # Determinar el nombre del archivo XLSX, juntando 'monederos' con la quincena y la fecha como YYYY-MM-DD HHMMSS
    nombre_archivo = f"monederos_{quincena_clave}_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.xlsx"

    # Guardar el archivo XLSX
    libro.save(nombre_archivo)

    # Si hubo personas sin cuentas, entonces mostrarlas en pantalla
    if len(personas_sin_cuentas) > 0:
        click.echo(click.style(f"  Hubo {len(personas_sin_cuentas)} Personas sin cuentas:", fg="yellow"))
        click.echo(click.style(f"  {', '.join(personas_sin_cuentas)}", fg="yellow"))

    # Mensaje termino
    click.echo(f"  Generar Monederos: {contador} filas en {nombre_archivo}")


@click.command()
@click.argument("quincena_clave", type=str)
def generar_pensionados(quincena_clave: str):
    """Generar archivo XLSX con los pensionados de una quincena"""

    # Validar quincena
    if re.match(QUINCENA_REGEXP, quincena_clave) is None:
        click.echo("ERROR: Quincena inválida.")
        sys.exit(1)

    # Iniciar sesion con la base de datos para que la alimentacion sea rapida
    sesion = database.session

    # Consultar quincena
    quincena = Quincena.query.filter_by(clave=quincena_clave).first()

    # Si no existe la quincena, entonces se termina
    if quincena is None:
        click.echo(f"ERROR: Quincena {quincena_clave} no existe.")
        sys.exit(1)

    # Si existe la quincena, pero no esta ABIERTA, entonces se termina
    if quincena.estado != "ABIERTA":
        click.echo(f"ERROR: Quincena {quincena_clave} no esta ABIERTA.")
        sys.exit(1)

    # Si existe la quincena, pero ha sido eliminada, entonces se termina
    if quincena.estatus != "A":
        click.echo(f"ERROR: Quincena {quincena_clave} ha sido eliminada.")
        sys.exit(1)

    # Consultar las nominas de la quincena, solo tipo SALARIO
    nominas = Nomina.query.filter_by(quincena_id=quincena.id).filter_by(tipo="SALARIO").filter_by(estatus="A").all()

    # Si no hay nominas, entonces se termina
    if len(nominas) == 0:
        click.echo(f"AVISO: No hay nominas de tipo SALARIO en la quincena {quincena_clave}.")
        sys.exit(0)

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
        # Si el modelo de la persona NO es 3, se omite
        if nomina.persona.modelo != 3:
            continue

        # Tomar las cuentas de la persona
        cuentas = nomina.persona.cuentas

        # Si no tiene cuentas, entonces se le crea una cuenta con el banco 10
        if len(cuentas) == 0:
            personas_sin_cuentas.append(nomina.persona.rfc)
            continue

        # Tomar la cuenta de la persona que no tenga la clave 9, porque esa clave es la de DESPENSA
        su_cuenta = None
        for cuenta in cuentas:
            if cuenta.banco.clave != "9" and cuenta.estatus == "A":
                su_cuenta = cuenta
                break

        # Si no tiene cuenta bancaria, entonces se le crea una cuenta con el banco 10
        if su_cuenta is None:
            personas_sin_cuentas.append(nomina.persona.rfc)
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

        # Incrementar contador
        contador += 1
        if contador % 100 == 0:
            click.echo(f"  Van {contador}...")

    # Actualizar los consecutivos de cada banco
    sesion.commit()

    # Determinar el nombre del archivo XLSX, juntando 'nominas' con la quincena y la fecha como YYYY-MM-DD HHMMSS
    nombre_archivo = f"pensionados_{quincena_clave}_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.xlsx"

    # Guardar el archivo XLSX
    libro.save(nombre_archivo)

    # Si hubo personas sin cuentas, entonces mostrarlas en pantalla
    if len(personas_sin_cuentas) > 0:
        click.echo(click.style(f"  Hubo {len(personas_sin_cuentas)} Personas sin cuentas:", fg="yellow"))
        click.echo(click.style(f"  {', '.join(personas_sin_cuentas)}", fg="yellow"))

    # Mensaje termino
    click.echo(f"  Generar Pensionados: {contador} filas en {nombre_archivo}")


@click.command()
@click.argument("quincena_clave", type=str)
def generar_dispersiones_pensionados(quincena_clave: str):
    """Generar archivo XLSX con las dispersiones pensionados de una quincena"""

    # Validar quincena
    if re.match(QUINCENA_REGEXP, quincena_clave) is None:
        click.echo("ERROR: Quincena inválida.")
        sys.exit(1)

    # Consultar quincena
    quincena = Quincena.query.filter_by(clave=quincena_clave).first()

    # Si no existe la quincena, entonces se termina
    if quincena is None:
        click.echo(f"ERROR: Quincena {quincena_clave} no existe.")
        sys.exit(1)

    # Si existe la quincena, pero no esta ABIERTA, entonces se termina
    if quincena.estado != "ABIERTA":
        click.echo(f"ERROR: Quincena {quincena_clave} no esta ABIERTA.")
        sys.exit(1)

    # Si existe la quincena, pero ha sido eliminada, entonces se termina
    if quincena.estatus != "A":
        click.echo(f"ERROR: Quincena {quincena_clave} ha sido eliminada.")
        sys.exit(1)

    # Consultar las nominas de la quincena, solo tipo SALARIO
    nominas = Nomina.query.filter_by(quincena_id=quincena.id).filter_by(tipo="SALARIO").filter_by(estatus="A").all()

    # Si no hay nominas, entonces se termina
    if len(nominas) == 0:
        click.echo(f"AVISO: No hay nominas de tipo SALARIO en la quincena {quincena_clave}.")
        sys.exit(0)

    # Iniciar el archivo XLSX
    libro = Workbook()

    # Tomar la hoja del libro XLSX
    hoja = libro.active

    # Agregar la fila con las cabeceras de las columnas
    hoja.append(
        [
            "CONSECUTIVO",
            "FORMA DE PAGO",
            "TIPO DE CUENTA",
            "BANCO RECEPTOR",
            "CUENTA ABONO",
            "IMPORTE PAGO",
            "CLAVE BENEFICIARIO",
            "RFC",
            "NOMBRE",
            "REFERENCIA PAGO",
            "CONCEPTO PAGO",
        ]
    )

    # Bucle para crear cada fila del archivo XLSX
    contador = 0
    personas_sin_cuentas = []
    for nomina in nominas:
        # Si el modelo de la persona NO es 3, se omite
        if nomina.persona.modelo != 3:
            continue

        # Tomar las cuentas de la persona
        cuentas = nomina.persona.cuentas

        # Si no tiene cuentas, entonces se le crea una cuenta con el banco 10
        if len(cuentas) == 0:
            personas_sin_cuentas.append(nomina.persona)
            continue

        # Tomar la cuenta de la persona que no tenga la clave 9, porque esa clave es la de DESPENSA
        su_cuenta = None
        for cuenta in cuentas:
            if cuenta.banco.clave != "9" and cuenta.estatus == "A":
                su_cuenta = cuenta
                break

        # Si no tiene cuenta bancaria, entonces se le crea una cuenta con el banco 10
        if su_cuenta is None:
            personas_sin_cuentas.append(nomina.persona)
            continue

        # Definir referencia_pago, se forma con los dos ultimos caracteres y los caracteres tercero y cuarto de la quincena
        referencia_pago = f"{quincena_clave[-2:]}{quincena_clave[2:4]}"

        # Definir concepto_pago, se forma con el texto "QUINCENA {dos digitos} PENSIONADOS"
        concepto_pago = f"QUINCENA {quincena_clave[-2:]} PENSIONADOS"

        # Agregar la fila
        hoja.append(
            [
                contador + 1,
                "04",
                "9",
                su_cuenta.banco.clave_dispersion_pensionados,
                su_cuenta.num_cuenta,
                nomina.importe,
                contador + 1,
                nomina.persona.rfc,
                nomina.persona.nombre_completo,
                referencia_pago,
                concepto_pago,
            ]
        )

        # Incrementar contador
        contador += 1
        if contador % 100 == 0:
            click.echo(f"  Van {contador}...")

    # Determinar el nombre del archivo XLSX, juntando 'nominas' con la quincena y la fecha como YYYY-MM-DD HHMMSS
    nombre_archivo = f"dispersiones_pensionados_{quincena_clave}_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.xlsx"

    # Guardar el archivo XLSX
    libro.save(nombre_archivo)

    # Si hubo personas sin cuentas, entonces mostrarlas en pantalla
    if len(personas_sin_cuentas) > 0:
        click.echo(click.style(f"  Hubo {len(personas_sin_cuentas)} Personas sin cuentas:", fg="yellow"))
        click.echo(click.style(f"  {', '.join(personas_sin_cuentas)}", fg="yellow"))

    # Mensaje termino
    click.echo(f"  Generar Dispersiones Pensionados: {contador} filas en {nombre_archivo}")


@click.command()
@click.argument("quincena_clave", type=str)
@click.argument("tipo", type=str)
def generar_timbrados(quincena_clave: str, tipo: str):
    """Generar archivo XLSX con los timbrados de una quincena"""

    # Validar quincena
    if re.match(QUINCENA_REGEXP, quincena_clave) is None:
        click.echo("ERROR: Quincena inválida.")
        sys.exit(1)

    # Validar tipo
    tipo = safe_string(tipo)
    if tipo not in ["SALARIO", "APOYO ANUAL"]:
        click.echo("ERROR: Tipo inválido.")
        sys.exit(1)

    # Iniciar sesion con la base de datos para que la alimentacion sea rapida
    sesion = database.session

    # Consultar quincena
    quincena = Quincena.query.filter_by(clave=quincena_clave).first()

    # Si no existe la quincena, entonces se termina
    if quincena is None:
        click.echo(f"ERROR: Quincena {quincena_clave} no existe.")
        sys.exit(1)

    # Si existe la quincena, pero no esta ABIERTA, entonces se termina
    if quincena.estado != "ABIERTA":
        click.echo(f"ERROR: Quincena {quincena_clave} no esta ABIERTA.")
        sys.exit(1)

    # Si existe la quincena, pero ha sido eliminada, entonces se termina
    if quincena.estatus != "A":
        click.echo(f"ERROR: Quincena {quincena_clave} esta eliminada.")
        sys.exit(1)

    # Determinar las fechas inicial y final de la quincena
    quincena_fecha_inicial = quincena_to_fecha(quincena_clave, dame_ultimo_dia=False)
    quincena_fecha_final = quincena_to_fecha(quincena_clave, dame_ultimo_dia=True)

    # Si el tipo es SALARIO armar un diccionario con las percepciones y deducciones de Conceptos activos
    if tipo == "SALARIO":
        # Consultar los conceptos activos
        conceptos = Concepto.query.filter_by(estatus="A").order_by(Concepto.clave).all()
        # Inicializar el diccionario de conceptos
        conceptos_dict = {}
        # Ordenar las claves, primero las que empiezan con P
        for concepto in conceptos:
            if concepto.clave.startswith("P"):
                conceptos_dict[concepto.clave] = concepto
        # Ordenar las claves, primero las que empiezan con P
        for concepto in conceptos:
            if concepto.clave.startswith("D"):
                conceptos_dict[concepto.clave] = concepto
        # Al final agregar las claves que no empiezan con P o D
        for concepto in conceptos:
            if not concepto.clave.startswith("P") and not concepto.clave.startswith("D"):
                conceptos_dict[concepto.clave] = concepto
    elif tipo == "APOYO ANUAL":
        # Si el tipo es APOYO ANUAL armar un diccionario con PAZ y DAZ como None
        conceptos_dict = {
            "PAZ": None,  # Percepcion de Apoyo Anual
            "DAZ": None,  # Deduccion ISR Apoyo Anual
            "D62": None,  # Deduccion Pension Alimenticia
        }

    # Consultar las Nominas activas de la quincena, del tipo dado, juntar con personas para ordenar por RFC
    nominas = (
        Nomina.query.join(Persona)
        .filter(Nomina.quincena_id == quincena.id)
        .filter(Nomina.tipo == tipo)
        .filter(Nomina.estatus == "A")
        .order_by(Persona.rfc)
        .all()
    )

    # Si no hay nominas, entonces se termina
    if len(nominas) == 0:
        click.echo(f"AVISO: No hay nominas de tipo {tipo} en la quincena {quincena_clave}.")
        sys.exit(0)

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
    ]

    # Agregar la fila con las cabeceras de las columnas
    hoja.append(encabezados_parte_1 + encabezados_parte_2 + encabezados_parte_3)

    # Bucle para crear cada fila del archivo XLSX
    contador = 0
    personas_sin_cuentas = []
    # personas_sin_fechas_de_ingreso = []
    for nomina in nominas:
        # Incrementar contador
        contador += 1

        # Consultar las cuentas de la persona
        cuentas = nomina.persona.cuentas

        # De las cuentas hay que sacar la que no tenga la clave 9, porque esa clave es la de DESPENSA
        su_cuenta = None
        for cuenta in cuentas:
            if cuenta.banco.clave != "9" and cuenta.estatus == "A":
                su_cuenta = cuenta
                break

        # Si no tiene cuenta bancaria, entonces se agrega a la lista de personas_sin_cuentas y se salta
        if su_cuenta is None:
            personas_sin_cuentas.append(nomina.persona.rfc)
            continue

        # Tomar el banco de la cuenta de la persona
        su_banco = su_cuenta.banco

        # Incrementer el consecutivo_generado del banco
        su_banco.consecutivo_generado += 1

        # Elaborar el numero de cheque, juntando la clave del banco y la consecutivo, siempre de 9 digitos
        num_cheque = f"{su_cuenta.banco.clave.zfill(2)}{su_banco.consecutivo_generado:07}"

        # Si NO tiene fecha de ingreso, se agrega a la lista de personas_sin_fechas_de_ingreso y se salta
        # if nomina.persona.ingreso_pj_fecha is None:
        #     personas_sin_fechas_de_ingreso.append(nomina.persona.rfc)
        #     continue

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
            datetime(year=2023, month=1, day=1).date(),  # FECHA INICIAL PERIODO quincena_fecha_inicial
            datetime(year=2023, month=12, day=31).date(),  # FECHA FINAL PERIODO quincena_fecha_final
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
            # Bucle por los conceptos
            for _, concepto in conceptos_dict.items():
                # Consultar la P-D de la quincena, la persona y el concepto
                percepcion_deduccion = (
                    PercepcionDeduccion.query.filter_by(quincena_id=quincena.id)
                    .filter_by(persona_id=nomina.persona.id)
                    .filter_by(concepto_id=concepto.id)
                    .first()
                )
                if percepcion_deduccion is not None:
                    fila_parte_2.append(percepcion_deduccion.importe)
                else:
                    fila_parte_2.append(0)
        elif tipo == "APOYO ANUAL":
            # Consultar la PercepcionDeduccion con concepto PAZ
            percepcion_deduccion_paz = (
                PercepcionDeduccion.query.join(Concepto)
                .filter(PercepcionDeduccion.quincena_id == quincena.id)
                .filter(PercepcionDeduccion.persona_id == nomina.persona.id)
                .filter(Concepto.clave == "PAZ")
                .first()
            )
            fila_parte_2.append(percepcion_deduccion_paz.importe if percepcion_deduccion_paz is not None else 0)
            # Consultar la PercepcionDeduccion con concepto DAZ
            percepcion_deduccion_daz = (
                PercepcionDeduccion.query.join(Concepto)
                .filter(PercepcionDeduccion.quincena_id == quincena.id)
                .filter(PercepcionDeduccion.persona_id == nomina.persona.id)
                .filter(Concepto.clave == "DAZ")
                .first()
            )
            fila_parte_2.append(percepcion_deduccion_daz.importe if percepcion_deduccion_daz is not None else 0)
            # Consultar la PercepcionDeduccion con concepto D62
            percepcion_deduccion_d62 = (
                PercepcionDeduccion.query.join(Concepto)
                .filter(PercepcionDeduccion.quincena_id == quincena.id)
                .filter(PercepcionDeduccion.persona_id == nomina.persona.id)
                .filter(Concepto.clave == "D62")
                .first()
            )
            fila_parte_2.append(percepcion_deduccion_d62.importe if percepcion_deduccion_d62 is not None else 0)

        # Fila parte 3
        fila_parte_3 = [
            "IP",  # ORIGEN RECURSO
            "100",  # MONTO DEL RECURSO
            nomina.persona.codigo_postal_fiscal,  # CODIGO POSTAL FISCAL
        ]

        # Agregar la fila
        hoja.append(fila_parte_1 + fila_parte_2 + fila_parte_3)

        # Actualizar el registro de la nominas con el numero de cheque
        nomina.num_cheque = num_cheque
        sesion.add(nomina)

        # Mostrar contador
        if contador % 100 == 0:
            click.echo(f"  Van {contador}...")

    # Actualizar los consecutivos de cada banco
    sesion.commit()

    # Determinar el nombre del archivo XLSX, juntando 'timbrados' con la quincena y la fecha como YYYY-MM-DD HHMMSS
    if tipo == "SALARIO":
        nombre_archivo = f"timbrados_salarios_{quincena_clave}_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.xlsx"
    elif tipo == "APOYO ANUAL":
        nombre_archivo = f"timbrados_apoyos_anuales_{quincena_clave}_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.xlsx"

    # Guardar el archivo XLSX
    libro.save(nombre_archivo)

    # Si hubo personas sin cuentas, entonces mostrarlas en pantalla
    if len(personas_sin_cuentas) > 0:
        click.echo(click.style(f"  Hubo {len(personas_sin_cuentas)} Personas sin cuentas:", fg="yellow"))
        click.echo(click.style(f"  {', '.join(personas_sin_cuentas)}", fg="yellow"))

    # Si hubo personas sin fecha de ingreso, entonces mostrarlas en pantalla
    # if len(personas_sin_fechas_de_ingreso) > 0:
    #     click.echo(click.style(f"  Hubo {len(personas_sin_fechas_de_ingreso)} Personas sin fecha de ingreso:", fg="yellow"))
    #     click.echo(click.style(f"  {', '.join(personas_sin_fechas_de_ingreso)}", fg="yellow"))

    # Mensaje termino
    click.echo(f"  Generar Timbrados: {contador} filas en {nombre_archivo}")


cli.add_command(alimentar)
cli.add_command(alimentar_apoyos_anuales)
cli.add_command(generar_nominas)
cli.add_command(generar_monederos)
cli.add_command(generar_pensionados)
cli.add_command(generar_dispersiones_pensionados)
cli.add_command(generar_timbrados)
