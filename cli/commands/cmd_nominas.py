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
from dotenv import load_dotenv
from openpyxl import load_workbook

from lib.exceptions import MyAnyError
from lib.fechas import crear_clave_quincena, quincena_to_fecha, quinquenio_count
from lib.safe_string import QUINCENA_REGEXP, safe_clave, safe_quincena, safe_rfc, safe_string
from perseo.app import create_app
from perseo.blueprints.centros_trabajos.models import CentroTrabajo
from perseo.blueprints.conceptos.models import Concepto
from perseo.blueprints.nominas.generators.dispersiones_pensionados import (
    crear_dispersiones_pensionados as task_crear_dispersiones_pensionados,
)
from perseo.blueprints.nominas.generators.monederos import crear_monederos as task_crear_monederos
from perseo.blueprints.nominas.generators.nominas import crear_nominas as task_crear_nominas
from perseo.blueprints.nominas.generators.pensionados import crear_pensionados as task_crear_pensionados
from perseo.blueprints.nominas.generators.timbrados import crear_timbrados as task_crear_timbrados
from perseo.blueprints.nominas.models import Nomina
from perseo.blueprints.percepciones_deducciones.models import PercepcionDeduccion
from perseo.blueprints.personas.models import Persona
from perseo.blueprints.plazas.models import Plaza
from perseo.blueprints.puestos.models import Puesto
from perseo.blueprints.quincenas.models import Quincena
from perseo.blueprints.quincenas_productos.models import QuincenaProducto
from perseo.blueprints.tabuladores.models import Tabulador
from perseo.blueprints.timbrados.models import Timbrado
from perseo.extensions import database

load_dotenv()

AGUINALDOS_FILENAME_XLS = "Aguinaldos.XLS"
APOYOS_FILENAME_XLS = "Apoyos.XLS"
BONOS_FILENAME_XLS = "Bonos.XLS"
COMPANIA_NOMBRE = "PODER JUDICIAL DEL ESTADO DE COAHUILA DE ZARAGOZA"
COMPANIA_RFC = "PJE901211TI9"
COMPANIA_CP = "25000"
EXPLOTACION_BASE_DIR = os.getenv("EXPLOTACION_BASE_DIR", "")
EXTRAORDINARIOS_BASE_DIR = os.getenv("EXTRAORDINARIOS_BASE_DIR", "")
NOMINAS_FILENAME_XLS = "NominaFmt2.XLS"
PATRON_RFC = "PJE901211TI9"
SERICA_FILENAME_XLSX = "SERICA.xlsx"

app = create_app()
app.app_context().push()
database.app = app


@click.group()
def cli():
    """Nominas"""


@cli.command()
@click.argument("quincena_clave", type=str)
def actualizar_timbrados(quincena_clave: str):
    """Actualizar los timbrados_ids (cambiar a cero si esta eliminado o no existe) de las nominas de una quincena"""

    # Validar quincena
    if re.match(QUINCENA_REGEXP, quincena_clave) is None:
        click.echo("ERROR: Quincena inválida.")
        sys.exit(1)

    # Consultar quincena
    quincena = Quincena.query.filter_by(clave=quincena_clave).first()

    # Si no existe la quincena, se termina
    if quincena is None:
        click.echo(f"ERROR: Quincena {quincena_clave} no existe.")
        sys.exit(1)

    # Inicializar contadores
    revisados_contador = 0
    actualizados_contador = 0
    puestos_en_cero_contador = 0

    # Bucle por cada nomina de la quincena
    click.echo(f"Actualizando los timbrados_ids de la quincena {quincena_clave}: ", nl=False)
    for nomina in quincena.nominas:
        # Si el estatus NO es 'A', se omite
        if nomina.estatus != "A":
            continue

        # Si el tipo es 'DESPENSA', se omite
        if nomina.tipo == "DESPENSA":
            continue

        # Incrementar revisados_contador
        revisados_contador += 1

        # De forma inicial, se define timbrado_id en None
        timbrado_id = None

        # Consultar el ultimo timbrado de la Nomina con estatus 'A' y ordenados por id descendente
        timbrado_ultimo = (
            Timbrado.query.filter_by(nomina_id=nomina.id).filter_by(estatus="A").order_by(Timbrado.id.desc()).first()
        )

        # Si existe el timbrado_ultimo, se toma su id
        if timbrado_ultimo is not None:
            timbrado_id = timbrado_ultimo.id

        # Si el timbrado_id es diferente al timbrado_id de la nomina, se actualiza
        if nomina.timbrado_id != timbrado_id:
            nomina.timbrado_id = timbrado_id
            nomina.save()
            actualizados_contador += 1
            # Si NO hay timbrado entonces timbrado_id es cero, se incrementa el contador
            if timbrado_id is None:
                puestos_en_cero_contador += 1
                click.echo(click.style("0", fg="yellow"), nl=False)
            else:
                click.echo(click.style("u", fg="green"), nl=False)
        else:
            click.echo(click.style(".", fg="cyan"), nl=False)

    # Poner avance de linea en la terminal
    click.echo("")

    # Si revisados_contador es cero, mostrar mensaje de error y terminar
    if revisados_contador == 0:
        click.echo(click.style("  No hubo registros de Nominas que revisar", fg="red"))
        sys.exit(1)

    # Si hubo nominas actualizadas, mostrar contador
    if actualizados_contador > 0:
        click.echo(click.style(f"  Se ACTUALIZARON {actualizados_contador} Nominas", fg="green"))

    # Si hubo puestos_en_cero_contador en cero, mostrar contador
    if puestos_en_cero_contador > 0:
        click.echo(click.style(f"  De la cuales {puestos_en_cero_contador} Nominas cambiaron timbrado_id a cero", fg="yellow"))

    # Mensaje termino
    click.echo(click.style(f"  Se revisaron {revisados_contador} Nominas", fg="green"))


@click.command()
@click.argument("quincena_clave", type=str)
@click.argument("fecha_pago_str", type=str)
def alimentar(quincena_clave: str, fecha_pago_str: str):
    """Alimentar nominas"""

    # Iniciar sesion con la base de datos para que la alimentacion sea rapida
    sesion = database.session

    # Validar quincena
    if re.match(QUINCENA_REGEXP, quincena_clave) is None:
        click.echo("ERROR: Quincena inválida.")
        sys.exit(1)

    # Definir la fecha_final en base a la clave de la quincena
    try:
        fecha_final = quincena_to_fecha(quincena_clave, dame_ultimo_dia=True)
    except ValueError:
        click.echo("ERROR: Quincena inválida.")
        sys.exit(1)

    # Validar fecha_pago
    try:
        fecha_pago = datetime.strptime(fecha_pago_str, "%Y-%m-%d")
    except ValueError:
        click.echo("ERROR: Fecha de pago inválida")
        sys.exit(1)

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

    # Definir el puesto generico al que se van a relacionar las personas que no tengan su puesto
    puesto_generico = Puesto.query.filter_by(clave="ND").first()
    if puesto_generico is None:
        click.echo("ERROR: Falta el puesto con clave ND.")
        sys.exit(1)

    # Definir el tabulador generico al que se van a relacionar los puestos que no tengan su tabulador
    tabulador_generico = Tabulador.query.filter_by(puesto_id=puesto_generico.id).first()
    if tabulador_generico is None:
        click.echo("ERROR: Falta el tabulador del puesto con clave ND.")
        sys.exit(1)

    # Inicializar los listados con las anomalias
    personas_actualizadas_del_tabulador = []
    personas_actualizadas_del_modelo = []
    personas_actualizadas_del_num_empleado = []
    personas_sin_puestos = []
    personas_sin_tabulador = []

    # Iniciar contadores
    contador = 0
    centros_trabajos_insertados_contador = 0
    personas_actualizadas_contador = 0
    personas_insertadas_contador = 0
    plazas_insertadas_contador = 0

    # Bucle por cada fila
    click.echo(f"Alimentar Nominas a la quincena {quincena.clave}: ", nl=False)
    for fila in range(1, hoja.nrows):
        # Tomar las columnas
        centro_trabajo_clave = hoja.cell_value(fila, 1)
        plaza_clave = hoja.cell_value(fila, 8)
        percepcion = int(hoja.cell_value(fila, 12)) / 100.0
        deduccion = int(hoja.cell_value(fila, 13)) / 100.0
        impte = int(hoja.cell_value(fila, 14)) / 100.0
        desde_s = str(int(hoja.cell_value(fila, 16)))
        hasta_s = str(int(hoja.cell_value(fila, 17)))

        # Tomar las columnas con datos de la Persona
        rfc = hoja.cell_value(fila, 2)
        modelo = int(hoja.cell_value(fila, 236))
        nombre_completo = hoja.cell_value(fila, 3)
        num_empleado = int(hoja.cell_value(fila, 240))

        # Tomar las columnas necesarias para el timbrado
        puesto_clave = safe_clave(hoja.cell_value(fila, 20))
        nivel = int(hoja.cell_value(fila, 9))
        quincena_ingreso = str(int(hoja.cell_value(fila, 19)))

        # Validar desde y hasta
        try:
            desde_clave = safe_quincena(desde_s)
            desde = quincena_to_fecha(desde_clave, dame_ultimo_dia=False)
            hasta_clave = safe_quincena(hasta_s)
            hasta = quincena_to_fecha(hasta_clave, dame_ultimo_dia=True)
        except ValueError:
            click.echo(click.style(f"ERROR: Quincena inválida en '{desde_s}' o '{hasta_s}'", fg="red"))
            sys.exit(1)

        # Consultar el Centro de Trabajo, si no existe se agrega
        centro_trabajo = CentroTrabajo.query.filter_by(clave=centro_trabajo_clave).first()
        if centro_trabajo is None:
            centro_trabajo = CentroTrabajo(clave=centro_trabajo_clave, descripcion="ND")
            sesion.add(centro_trabajo)
            sesion.commit()
            centros_trabajos_insertados_contador += 1

        # Consultar la Plaza, si no existe se agrega
        plaza = Plaza.query.filter_by(clave=plaza_clave).first()
        if plaza is None:
            plaza = Plaza(clave=plaza_clave, descripcion="ND")
            sesion.add(plaza)
            sesion.commit()
            plazas_insertadas_contador += 1

        # Si el modelo es 2, entonces en SINDICALIZADO, se toman 4 caracteres del puesto y se busca quinquenios
        quinquenios = None
        if modelo == 2:
            puesto_clave = puesto_clave[:4]

            # Inicializar la bandera para saltar la fila si el concepto es PME
            es_concepto_pme = False

            # Bucle entre las columnas de los conceptos para encontrar PQ1, PQ2, PQ3, PQ4, PQ5, PQ6
            col_num = 26
            while True:
                # Tomar el p_o_d
                p_o_d = safe_string(hoja.cell_value(fila, col_num))
                # Tomar el conc
                conc = safe_string(hoja.cell_value(fila, col_num + 1))
                # Si 'P' o 'D' es un texto vacio, se rompe el ciclo
                if p_o_d == "":
                    break
                # Si NO es P, se salta
                if p_o_d != "P":
                    col_num += 6
                    continue
                # Si conc es ME es monedero, se rompe el ciclo porque aqui no hay quinquenios
                if conc == "ME":
                    es_concepto_pme = True
                    break
                # Si el concepto no es PQ1, PQ2, PQ3, PQ4, PQ5, PQ6, se salta
                if conc not in ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6"]:
                    col_num += 6
                    continue
                # Tomar el tercer caracter del concepto y convertirlo a entero porque es la cantidad de quinquenios
                quinquenios = int(conc[1])
                break

            # Si es PME, entonces en esta fila NO esta el quinquenio, se mantiene en None
            if es_concepto_pme:
                quinquenios = None

        else:
            # Entonces NO es SINDICALIZADO, se define quinquenios en cero
            quinquenios = 0

        # Consultar el Puesto, si no existe se agrega a personas_sin_puestos y se le asigna el puesto_generico
        puesto = Puesto.query.filter_by(clave=puesto_clave).first()
        if puesto is None:
            personas_sin_puestos.append(rfc)
            puesto = puesto_generico

        # Consultar la Persona
        persona = Persona.query.filter_by(rfc=rfc).first()

        # Si NO existe la Persona, se agrega
        if persona is None:
            # Separar nombre_completo, en apellido_primero, apellido_segundo y nombres
            separado = safe_string(nombre_completo, save_enie=True).split(" ")
            apellido_primero = separado[0]
            apellido_segundo = separado[1]
            nombres = " ".join(separado[2:])

            # Si el modelo es 2 y quinquenios es None, entonces es SINDICALIZADO y se calculan los quinquenios
            if modelo == 2 and quinquenios is None:
                # Calcular la cantidad de quinquenios
                fecha_ingreso = quincena_to_fecha(quincena_ingreso, dame_ultimo_dia=False)
                quinquenios = quinquenio_count(fecha_ingreso, fecha_final)

            # Consultar el tabulador que coincida con puesto_clave, modelo, nivel y quinquenios
            tabulador = (
                Tabulador.query.filter_by(puesto_id=puesto.id)
                .filter_by(modelo=modelo)
                .filter_by(nivel=nivel)
                .filter_by(quinquenio=quinquenios)
                .first()
            )

            # Si no existe el tabulador, se agrega a personas_sin_tabulador y se le asigna tabulador_generico
            if tabulador is None:
                personas_sin_tabulador.append(rfc)
                tabulador = tabulador_generico

            # Insertar a la Persona
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
            sesion.commit()
            personas_insertadas_contador += 1

        # De lo contrario, se revisa si cambia la Persona de tabulador, modelo o num_empleado
        else:
            # Inicializar hay_cambios
            hay_cambios = False

            # Si la fila es concepto PME NO va tener los quinquenios, entonces se define con la Persona
            if quinquenios is None:
                quinquenios = persona.tabulador.quinquenio

            # Consultar el tabulador que coincida con puesto_clave, modelo, nivel y quinquenios
            tabulador = (
                Tabulador.query.filter_by(puesto_id=puesto.id)
                .filter_by(modelo=modelo)
                .filter_by(nivel=nivel)
                .filter_by(quinquenio=quinquenios)
                .first()
            )

            # Si NO existe el tabulador, se agrega a personas_sin_tabulador y se le asigna tabulador_generico
            if tabulador is None:
                personas_sin_tabulador.append(rfc)
                tabulador = tabulador_generico

            # Revisar si hay que actualizar el tabulador a la Persona
            if persona.tabulador_id != tabulador.id:
                personas_actualizadas_del_tabulador.append(
                    f"{rfc} {persona.nombre_completo}: Tabulador: {persona.tabulador_id} -> {tabulador.id}"
                )
                persona.tabulador_id = tabulador.id
                hay_cambios = True

            # Revisar si hay que actualizar el modelo a la Persona
            if persona.modelo != modelo:
                personas_actualizadas_del_modelo.append(
                    f"{rfc} {persona.nombre_completo}: Modelo: {persona.modelo} -> {modelo}"
                )
                persona.modelo = modelo
                hay_cambios = True

            # Revisar si hay que actualizar el numero de empleado a la Persona
            if persona.num_empleado != num_empleado:
                personas_actualizadas_del_num_empleado.append(
                    f"{rfc} {persona.nombre_completo}: Num. Emp. {persona.num_empleado} -> {num_empleado}"
                )
                persona.num_empleado = num_empleado
                hay_cambios = True

            # Si hay cambios, guardar la Persona
            if hay_cambios:
                persona.save()
                personas_actualizadas_contador += 1

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
            desde=desde,
            desde_clave=desde_clave,
            hasta=hasta,
            hasta_clave=hasta_clave,
            percepcion=percepcion,
            deduccion=deduccion,
            importe=impte,
            tipo=nomina_tipo,
            fecha_pago=fecha_pago,
        )
        sesion.add(nomina)

        # Incrementar contador
        contador += 1

        # Mostrar el avance con el modelo
        click.echo(click.style(modelo, fg="cyan"), nl=False)

    # Poner avance de linea
    click.echo("")

    # Si contador es cero, mostrar mensaje de error y terminar
    if contador == 0:
        click.echo(click.style("ERROR: No se alimentaron registros en nominas.", fg="red"))
        sys.exit(1)

    # Cerrar la sesion para que se guarden todos los datos en la base de datos
    sesion.commit()
    sesion.close()

    # Si hubo centros_trabajos_insertados, mostrar contador
    if centros_trabajos_insertados_contador > 0:
        click.echo(click.style(f"  Se insertaron {centros_trabajos_insertados_contador} Centros de Trabajo", fg="green"))

    # Si hubo personas actualizadas, mostrar contador
    if personas_actualizadas_contador > 0:
        click.echo(click.style(f"  Se actualizaron {personas_actualizadas_contador} Personas", fg="green"))
        for item in personas_actualizadas_del_tabulador:
            click.echo(click.style(f"  {item}", fg="yellow"))
        for item in personas_actualizadas_del_modelo:
            click.echo(click.style(f"  {item}", fg="yellow"))
        for item in personas_actualizadas_del_num_empleado:
            click.echo(click.style(f"  {item}", fg="yellow"))

    # Si hubo personas insertadas, mostrar contador
    if personas_insertadas_contador > 0:
        click.echo(click.style(f"  Se insertaron {personas_insertadas_contador} Personas", fg="green"))

    # Si hubo plazas insertadas, mostrar contador
    if plazas_insertadas_contador > 0:
        click.echo(click.style(f"  Se insertaron {plazas_insertadas_contador} Plazas", fg="green"))

    # Si hubo personas_sin_puestos, mostrarlas en pantalla
    if len(personas_sin_puestos) > 0:
        click.echo(click.style(f"  Hubo {len(personas_sin_puestos)} Personas sin puestos.", fg="yellow"))
        click.echo(click.style(f"  {', '.join(personas_sin_puestos)}", fg="yellow"))

    # Si hubo personas_sin_tabulador, mostrarlas en pantalla
    if len(personas_sin_tabulador) > 0:
        click.echo(click.style(f"  Hubo {len(personas_sin_tabulador)} Personas sin tabulador.", fg="yellow"))
        click.echo(click.style(f"  {', '.join(personas_sin_tabulador)}", fg="yellow"))

    # Mensaje termino
    click.echo(click.style(f"  Alimentar Nominas: {contador} insertadas.", fg="green"))


@click.command()
@click.argument("quincena_clave", type=str)
@click.argument("fecha_pago_str", type=str)
def alimentar_aguinaldos(quincena_clave: str, fecha_pago_str: str):
    """Alimentar aguinaldos"""

    # Validar quincena
    if re.match(QUINCENA_REGEXP, quincena_clave) is None:
        click.echo("ERROR: Quincena inválida.")
        sys.exit(1)

    # Definir la fecha_final en base a la clave de la quincena
    # Va a tomar el año de la quincena, el mes 12 y el dia 31
    try:
        fecha = quincena_to_fecha(quincena_clave, dame_ultimo_dia=True)
        fecha_final = datetime(fecha.year, 12, 31)
    except ValueError:
        click.echo("ERROR: Quincena inválida.")
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
    ruta = Path(EXPLOTACION_BASE_DIR, quincena_clave, AGUINALDOS_FILENAME_XLS)
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
    centros_trabajos_inexistentes = []
    personas_inexistentes = []
    plazas_insertadas_contador = 0

    # Bucle por cada fila
    click.echo(f"Alimentando Aguinaldos a la quincena {quincena.clave}: ", nl=False)
    for fila in range(1, hoja.nrows):
        # Tomar las columnas
        centro_trabajo_clave = hoja.cell_value(fila, 1)
        rfc = hoja.cell_value(fila, 2)
        # nombre_completo = hoja.cell_value(fila, 3)
        plaza_clave = hoja.cell_value(fila, 8)
        percepcion = int(hoja.cell_value(fila, 12)) / 100.0
        deduccion = int(hoja.cell_value(fila, 13)) / 100.0
        impte = int(hoja.cell_value(fila, 14)) / 100.0
        desde_s = str(int(hoja.cell_value(fila, 16)))
        hasta_s = str(int(hoja.cell_value(fila, 17)))
        # modelo = int(hoja.cell_value(fila, 236))
        # num_empleado = int(hoja.cell_value(fila, 240))

        # Validar desde y hasta
        try:
            desde_clave = safe_quincena(desde_s)
            desde = quincena_to_fecha(desde_clave, dame_ultimo_dia=False)
            hasta_clave = safe_quincena(hasta_s)
            hasta = quincena_to_fecha(hasta_clave, dame_ultimo_dia=True)
        except ValueError:
            click.echo(click.style(f"ERROR: Quincena inválida en '{desde_s}' o '{hasta_s}'", fg="red"))
            sys.exit(1)

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

        # Revisar si la Plaza existe, de lo contrario insertarla
        plaza = Plaza.query.filter_by(clave=plaza_clave).first()
        if plaza is None:
            plaza = Plaza(clave=plaza_clave, descripcion="ND")
            sesion.add(plaza)
            plazas_insertadas_contador += 1

        # Alimentar registro en Nomina
        nomina = Nomina(
            centro_trabajo=centro_trabajo,
            persona=persona,
            plaza=plaza,
            quincena=quincena,
            desde=desde,
            desde_clave=desde_clave,
            hasta=hasta,
            hasta_clave=hasta_clave,
            percepcion=percepcion,
            deduccion=deduccion,
            importe=impte,
            tipo="AGUINALDO",
            fecha_pago=fecha_pago,
        )
        sesion.add(nomina)

        # Incrementar contador
        contador += 1
        if contador % 100 == 0:
            click.echo(click.style(".", fg="cyan"), nl=False)

    # Poner avance de linea
    click.echo("")

    # Si contador es cero, mostrar mensaje de error y terminar
    if contador == 0:
        click.echo(click.style("ERROR: No se alimentaron registros en nominas.", fg="red"))
        sys.exit(1)

    # Cerrar la sesion para que se guarden todos los datos en la base de datos
    sesion.commit()
    sesion.close()

    # Actualizar la quincena para poner en verdadero el campo tiene_aguinaldos
    quincena.tiene_aguinaldos = True
    quincena.save()

    # Si hubo centros trabajos inexistentes, mostrarlos
    if len(centros_trabajos_inexistentes) > 0:
        click.echo(click.style(f"  Hubo {len(centros_trabajos_inexistentes)} C. de T. que no existen. Se omiten:", fg="yellow"))
        click.echo(click.style(f"  {', '.join(centros_trabajos_inexistentes)}", fg="yellow"))

    # Si hubo plazas insertadas, mostrar contador
    if plazas_insertadas_contador > 0:
        click.echo(click.style(f"  Se insertaron {plazas_insertadas_contador} Plazas", fg="green"))

    # Si hubo personas inexistentes, mostrar contador
    if len(personas_inexistentes) > 0:
        click.echo(click.style(f"  Hubo {len(personas_inexistentes)} Personas que no existen. Se omiten:", fg="yellow"))
        click.echo(click.style(f"  {', '.join(personas_inexistentes)}", fg="yellow"))

    # Mensaje termino
    click.echo(click.style(f"  Alimentar Aguinaldos: {contador} insertadas en la quincena {quincena_clave}.", fg="green"))


@click.command()
@click.argument("quincena_clave", type=str)
@click.argument("fecha_pago_str", type=str)
def alimentar_apoyos_anuales(quincena_clave: str, fecha_pago_str: str):
    """Alimentar apoyos anuales"""

    # Validar quincena
    if re.match(QUINCENA_REGEXP, quincena_clave) is None:
        click.echo("ERROR: Quincena inválida.")
        sys.exit(1)

    # Definir la fecha_final en base a la clave de la quincena
    try:
        fecha_final = quincena_to_fecha(quincena_clave, dame_ultimo_dia=True)
    except ValueError:
        click.echo("ERROR: Quincena inválida.")
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
    click.echo("Alimentando Nominas de Apoyos Anuales: ", nl=False)
    for fila in range(1, hoja.nrows):
        # Tomar las columnas
        rfc = hoja.cell_value(fila, 0).strip().upper()
        centro_trabajo_clave = hoja.cell_value(fila, 1).strip().upper()
        plaza_clave = hoja.cell_value(fila, 2).strip().upper()
        percepcion = float(hoja.cell_value(fila, 4))
        deduccion = float(hoja.cell_value(fila, 5))
        impte = float(hoja.cell_value(fila, 6))
        desde_s = str(int(hoja.cell_value(fila, 8)))
        hasta_s = str(int(hoja.cell_value(fila, 9)))

        # Validar desde y hasta
        try:
            desde_clave = safe_quincena(desde_s)
            desde = quincena_to_fecha(desde_clave, dame_ultimo_dia=False)
            hasta_clave = safe_quincena(hasta_s)
            hasta = quincena_to_fecha(hasta_clave, dame_ultimo_dia=True)
        except ValueError:
            click.echo(click.style(f"ERROR: Quincena inválida en '{desde_s}' o '{hasta_s}'", fg="red"))
            sys.exit(1)

        # Tomar el importe del concepto D62, si no esta presente sera cero
        try:
            impte_concepto_d62 = float(hoja.cell_value(fila, 10))
        except ValueError:
            impte_concepto_d62 = 0.0

        # Consultar la persona
        persona = Persona.query.filter_by(rfc=rfc).first()

        # Si NO existe, se agrega a la lista de personas_inexistentes y se salta
        if persona is None:
            personas_inexistentes.append(rfc)
            continue

        # Consultar el Centro de Trabajo
        centro_trabajo = CentroTrabajo.query.filter_by(clave=centro_trabajo_clave).first()

        # Si NO existe se agrega a la lista de centros_trabajos_inexistentes y se salta
        if centro_trabajo is None:
            centros_trabajos_inexistentes.append(centro_trabajo_clave)
            continue

        # Consultar la Plaza
        plaza = Plaza.query.filter_by(clave=plaza_clave).first()

        # Si NO existe se agrega a la lista de plazas_inexistentes y se salta
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
            tipo="APOYO ANUAL",
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
            tipo="APOYO ANUAL",
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
                tipo="APOYO ANUAL",
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
            desde=desde,
            desde_clave=desde_clave,
            hasta=hasta,
            hasta_clave=hasta_clave,
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

    # Si contador es cero, mostrar mensaje de error y terminar
    if contador == 0:
        click.echo(click.style("ERROR: No se alimentaron registros en nominas.", fg="red"))
        sys.exit(1)

    # Cerrar la sesion para que se guarden todos los datos en la base de datos
    sesion.commit()
    sesion.close()

    # Actualizar la quincena para poner en verdadero el campo tiene_apoyos_anuales
    quincena.tiene_apoyos_anuales = True
    quincena.save()

    # Si hubo centros_trabajos_inexistentes, mostrarlos
    if len(centros_trabajos_inexistentes) > 0:
        click.echo(click.style(f"  Hubo {len(centros_trabajos_inexistentes)} C. de T. que no existen. Se omiten:", fg="yellow"))
        click.echo(click.style(f"  {', '.join(centros_trabajos_inexistentes)}", fg="yellow"))

    # Si hubo plazas_inexistentes, mostrarlos
    if len(plazas_inexistentes) > 0:
        click.echo(click.style(f"  Hubo {len(plazas_inexistentes)} Plazas que no existen. Se omiten:", fg="yellow"))
        click.echo(click.style(f"  {', '.join(plazas_inexistentes)}", fg="yellow"))

    # Si hubo personas_inexistentes, mostrar contador
    if len(personas_inexistentes) > 0:
        click.echo(click.style(f"  Hubo {len(personas_inexistentes)} Personas que no existen. Se omiten:", fg="yellow"))
        click.echo(click.style(f"  {', '.join(personas_inexistentes)}", fg="yellow"))

    # Si hubo nominas_existentes, mostrarlos
    if len(nominas_existentes) > 0:
        click.echo(click.style(f"  Hubo {len(nominas_existentes)} Apoyos Anuales que ya existen. Se omiten:", fg="yellow"))
        click.echo(click.style(f"  {', '.join(nominas_existentes)}", fg="yellow"))

    # Mensaje termino
    click.echo(click.style(f"  Alimentar Apoyos Anuales: {contador} insertadas en la quincena {quincena_clave}.", fg="green"))


@click.command()
@click.argument("archivo_xlsx", type=str)
@click.option("--probar", is_flag=True, help="Solo probar la lectura del archivo.")
def alimentar_extraordinarios(archivo_xlsx: str, probar: bool = False):
    """Alimentar extraordinarios"""

    # Iniciar sesion con la base de datos para que la alimentacion sea rapida
    sesion = database.session

    # Validar el directorio donde espera encontrar los archivos
    if EXTRAORDINARIOS_BASE_DIR is None:
        click.echo("ERROR: Variable de entorno EXTRAORDINARIOS_BASE_DIR no definida.")
        sys.exit(1)

    # Validar si existe el archivo
    ruta = Path(EXTRAORDINARIOS_BASE_DIR, archivo_xlsx)
    if not ruta.exists():
        click.echo(f"ERROR: {str(ruta)} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        click.echo(f"ERROR: {str(ruta)} no es un archivo.")
        sys.exit(1)

    # El archivo debe tener los siguientes encabezados
    # RFC
    # QUINCENA
    # CLAVE CENTRO TRABAJO
    # PLAZA	DESDE
    # HASTA
    # TIPO NOMINA
    # PERCEPCION
    # DEDUCCION
    # IMPORTE
    # NUM CHEQUE
    # FECHA DE PAGO
    # TIPO DE EXTRAORDINARIA
    # P30
    # PGN
    # PGA
    # P22
    # PVD
    # PGP
    # P20
    # PAM
    # PS3
    # D01
    # D1A
    # P07
    # P7G
    # PHR
    # PFB

    # Leer archivo_xlsx con openpyxl
    workbook = load_workbook(filename=ruta, read_only=True, data_only=True)

    # Inicializar listado de personas NO encontradas
    personas_no_encontradas = []

    # Inicializar listado de quincenas NO encontradas
    quincenas_no_encontradas = []

    # Inicializar desde no validos
    desde_no_validos = []

    # Inicializar hasta no validos
    hasta_no_validos = []

    # Bucle por los renglones de la hoja
    contador = 0
    click.echo("Alimentando Extraordinarios: ", nl=False)
    for row in workbook.active.iter_rows(min_row=2, max_col=26, max_row=3000):
        # Juntar todas las celdas de la fila en una lista
        fila = [celda.value for celda in row]

        # Si el primer elemento de la fila es vacio, se rompe el ciclo
        if str(fila[0]).strip() == "" or fila[0] is None or fila[0] == "None":
            break

        # Asegurarse de que cada valor sea un string ascii
        # for i, valor in enumerate(fila):
        #     # Si el valor es "0", cambiarlo por "", de lo contrario, convertirlo a ascii
        #     if valor == "0":
        #         fila[i] = ""
        #     else:
        #         fila[i] = valor.encode("ascii", "ignore").decode("ascii")

        # Tomar los valores de la fila
        rfc = safe_rfc(fila[0])
        quincena_clave = safe_quincena(str(fila[1]))
        centro_trabajo_clave = safe_clave(fila[2], max_len=10)
        plaza_clave = safe_clave(fila[3], max_len=24)
        desde_dt = fila[4]
        hasta_dt = fila[5]
        # tipo_nomina = fila[6]
        percepcion = fila[7]
        deduccion = fila[8]
        importe = fila[9]
        # num_cheque = fila[10]
        fecha_pago = fila[11]
        # tipo_extraordinaria = fila[12]
        # p30 = fila[13]
        # pgn = fila[14]
        # pga = fila[15]
        # p22 = fila[16]
        # pvd = fila[17]
        # pgp = fila[18]
        # p20 = fila[19]
        # pam = fila[20]
        # ps3 = fila[21]
        # d01 = fila[22]
        # d1a = fila[23]
        # p07 = fila[24]
        # p7g = fila[25]
        # phr = fila[26]
        # pfb = fila[27]

        # Consultar el centro de trabajo a partir de la clave, si no se encuentra, se usa el ND
        centro_trabajo = CentroTrabajo.query.filter_by(clave=centro_trabajo_clave).first()
        if centro_trabajo is None:
            centro_trabajo = CentroTrabajo.query.filter_by(clave="ND").first()

        # Consultar la persona a partir del rfc, si no se encuentra, se omite
        persona = Persona.query.filter_by(rfc=rfc).first()
        if persona is None:
            personas_no_encontradas.append(rfc)
            click.echo(click.style("X", fg="red"), nl=False)
            continue

        # Consultar la plaza a partir de la clave, si no se encuentra, se usa el ND
        plaza = Plaza.query.filter_by(clave=plaza_clave).first()
        if plaza is None:
            plaza = Plaza.query.filter_by(clave="ND").first()

        # Validar quincena
        if re.match(QUINCENA_REGEXP, quincena_clave) is None:
            quincenas_no_encontradas.append(quincena_clave)
            click.echo(click.style("X", fg="red"), nl=False)
            continue

        # Consultar la quincena a partir de la clave, si no se encuentra, se omite
        quincena = Quincena.query.filter_by(clave=quincena_clave).first()
        if quincena is None:
            quincenas_no_encontradas.append(quincena_clave)
            click.echo(click.style("X", fg="red"), nl=False)
            continue

        # Validar desde
        try:
            desde_clave = crear_clave_quincena(desde_dt.date())
            desde_dt = quincena_to_fecha(desde_clave, dame_ultimo_dia=False)
        except ValueError:
            desde_no_validos.append(desde_dt)
            click.echo(click.style("X", fg="red"), nl=False)
            continue

        # Validar desde y hasta
        try:
            hasta_clave = crear_clave_quincena(hasta_dt.date())
            hasta_dt = quincena_to_fecha(hasta_clave, dame_ultimo_dia=True)
        except ValueError:
            hasta_no_validos.append(hasta_dt)
            click.echo(click.style("X", fg="red"), nl=False)
            continue

        # Alimentar nomina
        if probar is False:
            nomina = Nomina(
                centro_trabajo=centro_trabajo,
                persona=persona,
                plaza=plaza,
                quincena=quincena,
                desde=desde_dt,
                desde_clave=desde_clave,
                hasta=hasta_dt,
                hasta_clave=hasta_clave,
                percepcion=percepcion,
                deduccion=deduccion,
                importe=importe,
                tipo="EXTRAORDINARIO",
                fecha_pago=fecha_pago,
            )
            sesion.add(nomina)

        # Incrementar contador
        contador += 1
        click.echo(click.style(".", fg="cyan"), nl=False)

    # Poner avance de linea
    click.echo("")

    # Cerrar la sesion para que se guarden todos los datos en la base de datos
    sesion.commit()
    sesion.close()

    # Si hubo personas_no_encontradas, mostrarlos
    if len(personas_no_encontradas) > 0:
        click.echo(click.style(f"  Hubo {len(personas_no_encontradas)} Personas no encontradas.", fg="yellow"))
        click.echo(click.style(f"  {', '.join(personas_no_encontradas)}", fg="yellow"))

    # Si hubo quincenas_no_encontradas, mostrarlos
    if len(quincenas_no_encontradas) > 0:
        click.echo(click.style(f"  Hubo {len(quincenas_no_encontradas)} Quincenas no encontradas.", fg="yellow"))
        click.echo(click.style(f"  {', '.join(quincenas_no_encontradas)}", fg="yellow"))

    # Si hubo desde_no_validos, mostrarlos
    if len(desde_no_validos) > 0:
        click.echo(click.style(f"  Hubo {len(desde_no_validos)} Desde no validos.", fg="yellow"))
        click.echo(click.style(f"  {', '.join(desde_no_validos)}", fg="yellow"))

    # Si hubo hasta_no_validos, mostrarlos
    if len(hasta_no_validos) > 0:
        click.echo(click.style(f"  Hubo {len(hasta_no_validos)} Hasta no validos.", fg="yellow"))
        click.echo(click.style(f"  {', '.join(hasta_no_validos)}", fg="yellow"))

    # Mensaje termino
    if probar:
        click.echo(click.style(f"  Alimentar Extraordinarios: modo PROBAR {contador} pueden insertarse.", fg="green"))
    else:
        click.echo(click.style(f"  Alimentar Extraordinarios: {contador} insertados.", fg="green"))


@click.command()
@click.argument("quincena_clave", type=str)
@click.option("--serica-xlsx", default=SERICA_FILENAME_XLSX, help="Archivo XLSX con los datos")
@click.option("--output-txt", default="SERICA.txt", help="Archivo TXT de salida")
def generar_issste(quincena_clave, serica_xlsx, output_txt):
    """Generar archivo XLSX con los datos para el ISSSTE"""

    # Validar si existe el archivo
    ruta = Path(EXPLOTACION_BASE_DIR, quincena_clave, serica_xlsx)
    if not ruta.exists():
        click.echo(f"ERROR: {str(ruta)} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        click.echo(f"ERROR: {str(ruta)} no es un archivo.")
        sys.exit(1)

    # Abrir el archivo XLSX con openpyxl para leer sus datos
    workbook = load_workbook(filename=ruta, read_only=True, data_only=True)

    # Elegir la region DETALLE
    detalle = workbook["DETALLE"]

    # Crear archivo TXT con los datos de la fila
    click.echo("Generando ISSSTE: ", nl=False)
    with open(output_txt, "w", encoding="ascii") as f:
        # Bucle por las filas
        for row in detalle.iter_rows(min_row=5, max_col=81, max_row=3000):
            # Juntar todas las celdas de la fila en una lista
            # fila = [str(celda.value).strip() for celda in row]
            fila = [str(celda.value).strip() for celda in row]

            # Si el primer elemento de la fila es vacio, se rompe el ciclo
            if fila[0] == "" or fila[0] is None or fila[0] == "None":
                break

            # Asegurarse de que cada valor sea un string ascii
            for i, valor in enumerate(fila):
                # Si el valor es "0", cambiarlo por "", de lo contrario, convertirlo a ascii
                if valor == "0":
                    fila[i] = ""
                else:
                    fila[i] = valor.encode("ascii", "ignore").decode("ascii")

            # Escribir la fila en el archivo TXT y agregar un salto de linea
            f.write("|".join(fila) + "\r")
            click.echo(click.style(".", fg="cyan"), nl=False)

    # Poner avance de linea
    click.echo("")

    # Mensaje termino
    click.echo(click.style(f"  Generar ISSSTE: {output_txt} generado.", fg="green"))


@click.command()
@click.argument("quincena_clave", type=str)
def crear_dispersiones_pensionados(quincena_clave):
    """Crear archivo XLSX con las dispersiones para pensionados"""

    # Validar quincena_clave
    if re.match(QUINCENA_REGEXP, quincena_clave) is None:
        click.echo(click.style("ERROR: Clave de la quincena inválida.", fg="red"))
        sys.exit(1)

    # Consultar quincena
    quincena = Quincena.query.filter_by(clave=quincena_clave).first()

    # Si no existe la quincena o ha sido eliminada, causa error
    if quincena is None or quincena.estatus != "A":
        click.echo(click.style("ERROR: No existe o ha sido eliminada la quincena.", fg="red"))
        sys.exit(1)

    # Crear un producto para la quincena
    quincena_producto = QuincenaProducto(
        quincena=quincena,
        fuente="DISPERSIONES PENSIONADOS",
        mensajes="Crear archivo XLSX con las dispersiones para pensionados",
    )
    quincena_producto.save()

    # Ejecutar crear_dispersiones_pensionados
    try:
        mensaje_termino = task_crear_dispersiones_pensionados(quincena_clave, quincena_producto.id)
    except MyAnyError as error:
        click.echo(click.style(f"ERROR: {str(error)}", fg="red"))
        sys.exit(1)

    # Mensaje termino
    click.echo(click.style(mensaje_termino, fg="green"))


@click.command()
@click.argument("quincena_clave", type=str)
def crear_monederos(quincena_clave):
    """Crear archivo XLSX con los monederos de una quincena"""

    # Validar quincena_clave
    if re.match(QUINCENA_REGEXP, quincena_clave) is None:
        click.echo(click.style("ERROR: Clave de la quincena inválida.", fg="red"))
        sys.exit(1)

    # Consultar quincena
    quincena = Quincena.query.filter_by(clave=quincena_clave).first()

    # Si no existe la quincena o ha sido eliminada, causa error
    if quincena is None or quincena.estatus != "A":
        click.echo(click.style("ERROR: No existe o ha sido eliminada la quincena.", fg="red"))
        sys.exit(1)

    # Crear un producto para la quincena
    quincena_producto = QuincenaProducto(
        quincena=quincena,
        fuente="MONEDEROS",
        mensajes="Crear archivo XLSX con los monederos de una quincena",
    )
    quincena_producto.save()

    # Ejecutar crear_monederos
    try:
        mensaje_termino = task_crear_monederos(quincena_clave, quincena_producto.id)
    except MyAnyError as error:
        click.echo(click.style(f"ERROR: {str(error)}", fg="red"))
        sys.exit(1)

    # Mensaje termino
    click.echo(click.style(mensaje_termino, fg="green"))


@click.command()
@click.argument("quincena_clave", type=str)
def crear_nominas(quincena_clave):
    """Crear archivo XLSX con las nominas de una quincena"""

    # Validar quincena_clave
    if re.match(QUINCENA_REGEXP, quincena_clave) is None:
        click.echo(click.style("ERROR: Clave de la quincena inválida.", fg="red"))
        sys.exit(1)

    # Consultar quincena
    quincena = Quincena.query.filter_by(clave=quincena_clave).first()

    # Si no existe la quincena o ha sido eliminada, causa error
    if quincena is None or quincena.estatus != "A":
        click.echo(click.style("ERROR: No existe o ha sido eliminada la quincena.", fg="red"))
        sys.exit(1)

    # Crear un producto para la quincena
    quincena_producto = QuincenaProducto(
        quincena=quincena,
        fuente="MONEDEROS",
        mensajes="Crear archivo XLSX con las nominas de una quincena",
    )
    quincena_producto.save()

    # Ejecutar crear_nominas
    try:
        mensaje_termino = task_crear_nominas(quincena_clave, quincena_producto.id)
    except MyAnyError as error:
        click.echo(click.style(f"ERROR: {str(error)}", fg="red"))
        sys.exit(1)

    # Terminar la tarea en el fondo y entregar el mensaje de termino
    click.echo(click.style(mensaje_termino, fg="green"))


@click.command()
@click.argument("quincena_clave", type=str)
def crear_pensionados(quincena_clave):
    """Crear archivo XLSX con los pensionados de una quincena"""

    # Validar quincena_clave
    if re.match(QUINCENA_REGEXP, quincena_clave) is None:
        click.echo(click.style("ERROR: Clave de la quincena inválida.", fg="red"))
        sys.exit(1)

    # Consultar quincena
    quincena = Quincena.query.filter_by(clave=quincena_clave).first()

    # Si no existe la quincena o ha sido eliminada, causa error
    if quincena is None or quincena.estatus != "A":
        click.echo(click.style("ERROR: No existe o ha sido eliminada la quincena.", fg="red"))
        sys.exit(1)

    # Crear un producto para la quincena
    quincena_producto = QuincenaProducto(
        quincena=quincena,
        fuente="PENSIONADOS",
        mensajes="Crear archivo XLSX con los pensionados de una quincena",
    )
    quincena_producto.save()

    # Ejecutar crear_pensionados
    try:
        mensaje_termino = task_crear_pensionados(quincena_clave, quincena_producto.id)
    except MyAnyError as error:
        click.echo(click.style(f"ERROR: {str(error)}", fg="red"))
        sys.exit(1)

    # Terminar la tarea en el fondo y entregar el mensaje de termino
    click.echo(click.style(mensaje_termino, fg="green"))


@click.command()
@click.argument("quincena_clave", type=str)
def crear_timbrados_empleados_activos(quincena_clave):
    """Crear archivo XLSX con los timbrados de los empleados activos"""

    # Validar quincena_clave
    if re.match(QUINCENA_REGEXP, quincena_clave) is None:
        click.echo(click.style("ERROR: Clave de la quincena inválida.", fg="red"))
        sys.exit(1)

    # Consultar quincena
    quincena = Quincena.query.filter_by(clave=quincena_clave).first()

    # Si no existe la quincena o ha sido eliminada, causa error
    if quincena is None or quincena.estatus != "A":
        click.echo(click.style("ERROR: No existe o ha sido eliminada la quincena.", fg="red"))
        sys.exit(1)

    # Crear un producto para la quincena
    quincena_producto = QuincenaProducto(
        quincena=quincena,
        fuente="TIMBRADOS EMPLEADOS ACTIVOS",
        mensajes="Crear archivo XLSX con los timbrados de los empleados activos...",
    )
    quincena_producto.save()

    # Ejecutar crear_timbrados con Personas con modelos 1: "CONFIANZA" y 2: "SINDICALIZADO"
    try:
        mensaje_termino = task_crear_timbrados(
            quincena_clave=quincena_clave,
            quincena_producto_id=quincena_producto.id,
            modelos=[1, 2],
        )
    except MyAnyError as error:
        click.echo(click.style(f"ERROR: {str(error)}", fg="red"))
        sys.exit(1)

    # Terminar la tarea en el fondo y entregar el mensaje de termino
    click.echo(click.style(mensaje_termino, fg="green"))


@click.command()
@click.argument("quincena_clave", type=str)
def crear_timbrados_pensionados(quincena_clave):
    """Crear archivo XLSX con los timbrados de los pensionados"""

    # Validar quincena_clave
    if re.match(QUINCENA_REGEXP, quincena_clave) is None:
        click.echo(click.style("ERROR: Clave de la quincena inválida.", fg="red"))
        sys.exit(1)

    # Consultar quincena
    quincena = Quincena.query.filter_by(clave=quincena_clave).first()

    # Si no existe la quincena o ha sido eliminada, causa error
    if quincena is None or quincena.estatus != "A":
        click.echo(click.style("ERROR: No existe o ha sido eliminada la quincena.", fg="red"))
        sys.exit(1)

    # Crear un producto para la quincena
    quincena_producto = QuincenaProducto(
        quincena=quincena,
        fuente="TIMBRADOS PENSIONADOS",
        mensajes="Crear archivo XLSX con los timbrados de los pensionados",
    )
    quincena_producto.save()

    # Ejecutar crear_timbrados con Personas con modelo 3: "PENSIONADO"
    try:
        mensaje_termino = task_crear_timbrados(
            quincena_clave=quincena_clave,
            quincena_producto_id=quincena_producto.id,
            modelos=[3],
        )
    except MyAnyError as error:
        click.echo(click.style(f"ERROR: {str(error)}", fg="red"))
        sys.exit(1)

    # Terminar la tarea en el fondo y entregar el mensaje de termino
    click.echo(click.style(mensaje_termino, fg="green"))


cli.add_command(actualizar_timbrados)
cli.add_command(alimentar)
cli.add_command(alimentar_aguinaldos)
cli.add_command(alimentar_apoyos_anuales)
cli.add_command(alimentar_extraordinarios)
cli.add_command(generar_issste)
cli.add_command(crear_dispersiones_pensionados)
cli.add_command(crear_monederos)
cli.add_command(crear_nominas)
cli.add_command(crear_pensionados)
cli.add_command(crear_timbrados_empleados_activos)
cli.add_command(crear_timbrados_pensionados)
