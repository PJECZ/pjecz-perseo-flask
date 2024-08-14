"""
CLI Personas
"""

import csv
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import click
import requests
import xlrd
from dotenv import load_dotenv

from lib.exceptions import MyAnyError
from lib.fechas import quincena_to_fecha
from lib.safe_string import QUINCENA_REGEXP, safe_clave, safe_curp, safe_rfc, safe_string
from perseo.app import create_app
from perseo.blueprints.nominas.models import Nomina
from perseo.blueprints.percepciones_deducciones.models import PercepcionDeduccion
from perseo.blueprints.personas.models import Persona
from perseo.blueprints.personas.tasks import actualizar_ultimos as task_actualizar_ultimos
from perseo.blueprints.personas.tasks import exportar_xlsx as task_exportar_xlsx
from perseo.blueprints.plazas.models import Plaza
from perseo.blueprints.puestos.models import Puesto
from perseo.blueprints.quincenas.models import Quincena
from perseo.blueprints.tabuladores.models import Tabulador
from perseo.extensions import database

load_dotenv()

EMPLEADOS_ALFABETICO_FILENAME_XLS = "EmpleadosAlfabetico.XLS"
EXPLOTACION_BASE_DIR = os.getenv("EXPLOTACION_BASE_DIR", "")
NOMINAS_FILENAME_XLS = "NominaFmt2.XLS"
PERSONAS_CSV = "seed/personas.csv"
RRHH_PERSONAL_URL = os.getenv("RRHH_PERSONAL_URL", "")
RRHH_PERSONAL_API_KEY = os.getenv("RRHH_PERSONAL_API_KEY", "")
TIMEOUT = 12

app = create_app()
app.app_context().push()
database.app = app


@click.group()
def cli():
    """Personas"""


@click.command()
@click.argument("quincena_clave", type=str)
def actualizar_datos_fiscales(quincena_clave: str):
    """Actualizar los CURPs, CP fiscal y las fechas de ingreso de las personas a partir de los archivos de explotacion de una quincena"""

    # Validar quincena
    if re.match(QUINCENA_REGEXP, quincena_clave) is None:
        click.echo("ERROR: Quincena inválida")
        sys.exit(1)

    # Validar el directorio donde espera encontrar los archivos de explotacion
    if EXPLOTACION_BASE_DIR is None:
        click.echo("ERROR: Variable de entorno EXPLOTACION_BASE_DIR no definida.")
        sys.exit(1)

    # Validar si existe el archivo
    ruta = Path(EXPLOTACION_BASE_DIR, quincena_clave, EMPLEADOS_ALFABETICO_FILENAME_XLS)
    if not ruta.exists():
        click.echo(f"ERROR: {str(ruta)} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        click.echo(f"ERROR: {str(ruta)} no es un archivo.")
        sys.exit(1)

    # Abrir el archivo XLS con xlrd
    libro = xlrd.open_workbook(str(ruta))

    # Obtener la primera hoja
    hoja = libro.sheet_by_index(0)

    # Inicializar los listados con las anomalias
    personas_no_encontradas = []

    # Inicializar contador de personas actualizadas
    personas_actualizadas_contador = 0

    # Bucle por cada fila
    click.echo("Actualizando las Personas: ", nl=False)
    for fila in range(1, hoja.nrows):
        # Tomar las columnas
        rfc = hoja.cell_value(fila, 0)
        quincena_ingreso_pj_fecha_str = str(int(hoja.cell_value(fila, 7)))
        quincena_ingreso_gobierno_fecha_str = str(int(hoja.cell_value(fila, 8)))

        # Validar el CURP
        try:
            curp = safe_curp(hoja.cell_value(fila, 17))
        except ValueError:
            click.echo(f"ERROR: {hoja.cell_value(fila, 17)} no es CURP VALIDO.")
            continue

        # Si la celda de CP fiscal es vacia, tomar el valor 0
        if hoja.cell_value(fila, 21) == "":
            cp_fiscal = 0
        else:
            cp_fiscal = int(hoja.cell_value(fila, 21))

        # Convertir la quincena_ingreso_pj_fecha_str a fecha
        try:
            ingreso_pj_fecha = quincena_to_fecha(quincena_ingreso_pj_fecha_str)
        except ValueError:
            # ingreso_pj_fecha = None
            click.echo(f"ERROR: {quincena_ingreso_pj_fecha_str} no es VALIDO.")
            sys.exit(1)

        # Convertir la quincena_entro_gob_str a fecha
        try:
            ingreso_gobierno_fecha = quincena_to_fecha(quincena_ingreso_gobierno_fecha_str)
        except ValueError:
            # ingreso_gobierno_fecha = None
            click.echo(f"ERROR: {quincena_ingreso_gobierno_fecha_str} no es VALIDO.")
            sys.exit(1)

        # Consultar a la persona
        persona = Persona.query.filter_by(rfc=rfc).first()

        # Si no se encuentra, agregar a la lista de anomalias y saltar
        if persona is None:
            personas_no_encontradas.append(rfc)
            continue

        # Inicializar la bandera de cambios
        hay_cambios = False

        # Si persona.ingreso_pj_fecha es diferente, actualizar
        if persona.ingreso_pj_fecha != ingreso_pj_fecha:
            persona.ingreso_pj_fecha = ingreso_pj_fecha
            hay_cambios = True

        # Si persona.ingreso_gobierno_fecha es diferente, actualizar
        if persona.ingreso_gobierno_fecha != ingreso_gobierno_fecha:
            persona.ingreso_gobierno_fecha = ingreso_gobierno_fecha
            hay_cambios = True

        # Si la persona NO tiene CURP, actualizar
        if persona.curp == "":
            persona.curp = curp
            hay_cambios = True

        # Si la persona NO tiene CP fiscal, actualizar
        if persona.codigo_postal_fiscal == 0 and cp_fiscal > 0:
            persona.codigo_postal_fiscal = cp_fiscal
            hay_cambios = True

        # Si hay cambios, agregar a la sesion e incrementar el contador
        if hay_cambios is True:
            persona.save()
            personas_actualizadas_contador += 1
            click.echo(click.style("u", fg="green"), nl=False)

    # Poner avance de linea
    click.echo("")

    # Si hubo personas_no_encontradas, mostrarlas
    if len(personas_no_encontradas) > 0:
        click.echo(click.style(f"  Hubo {len(personas_no_encontradas)} personas que no se encontraron:", fg="yellow"))
        click.echo(click.style(f"  {','.join(personas_no_encontradas)}", fg="yellow"))

    # Mensaje termino
    click.echo(click.style(f"  Actualizar fechas de ingreso de las personas: {personas_actualizadas_contador}", fg="green"))


@click.command()
@click.option("--personas-csv", default=PERSONAS_CSV, help="Archivo CSV con los datos de las Personas")
def actualizar_datos_personales(personas_csv: str):
    """Actualizar los Nombres, Apellido Primero, Apellido Segundo, CP, CURP y/o NSS de las Personas en base a su RFC a partir de un archivo CSV"""

    # Validar archivo
    ruta = Path(personas_csv)
    if not ruta.exists():
        click.echo(f"ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        click.echo(f"ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)

    # Iniciar sesión con la base de datos para que la alimentación sea rápida
    sesion = database.session

    # Inicializar contadores y mensajes
    contador = 0
    errores = []

    # Leer el archivo CSV
    click.echo("Actualizar Personas: ", nl=False)
    with open(ruta, newline="", encoding="utf8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Consultar la persona
            persona = Persona.query.filter_by(rfc=row["rfc"]).first()

            # Si no existe, saltar
            if persona is None:
                continue

            # Bandera si hubo cambios
            hay_cambios = False

            # Validar nombres
            nombres = None
            if "nombres" in row:
                nombres = safe_string(row["nombres"], save_enie=True)
                if persona.nombres != nombres:
                    persona.nombres = nombres
                    hay_cambios = True

            # Validar apellido_primero
            apellido_primero = None
            if "apellido primero" in row:
                apellido_primero = safe_string(row["apellido primero"], save_enie=True)
                if persona.apellido_primero != apellido_primero:
                    persona.apellido_primero = apellido_primero
                    hay_cambios = True

            # Validar apellido_segundo
            apellido_segundo = None
            if "apellido segundo" in row:
                apellido_segundo = safe_string(row["apellido segundo"], save_enie=True)
                if persona.apellido_segundo != apellido_segundo:
                    persona.apellido_segundo = apellido_segundo
                    hay_cambios = True

            # Validar el CP
            codigo_postal_fiscal = None
            if "cp" in row and row["cp"] != "":
                try:
                    codigo_postal_fiscal = int(row["cp"])
                except ValueError:
                    errores.append(f"{row['rfc']}: CP inválido: {row['cp']}")
                if persona.codigo_postal_fiscal != codigo_postal_fiscal:
                    persona.codigo_postal_fiscal = codigo_postal_fiscal
                    hay_cambios = True

            # Validar la CURP
            curp = None
            if "curp" in row and row["curp"] != "":
                try:
                    curp = safe_curp(row["curp"])
                except ValueError:
                    errores.append(f"{row['rfc']}: CURP inválido: {row['curp']}")
                if persona.curp != curp:
                    persona.curp = curp
                    hay_cambios = True

            # Validar el numero de seguridad social
            seguridad_social = None
            if "nss" in row and row["nss"] != "":
                if re.match(r"^\d{1,24}$", row["nss"]):
                    seguridad_social = row["nss"]
                else:
                    errores.append(f"{row['rfc']}: NSS inválido: {row['seguridad_social']}")
                if persona.seguridad_social != seguridad_social:
                    persona.seguridad_social = seguridad_social
                    hay_cambios = True

            # Si hubo cambios, agregar a la sesión e incrementar el contador
            if hay_cambios:
                sesion.add(persona)
                contador += 1
                click.echo(click.style("u", fg="cyan"), nl=False)

    # Poner avance de linea
    click.echo("")

    # Si no hubo cambios, mostrar mensaje y terminar
    if contador == 0:
        click.echo("  AVISO: No hubo cambios.")
        sys.exit(0)

    # Guardar cambios
    sesion.commit()
    sesion.close()

    # Si hubo errores, mostrarlos
    if len(errores) > 0:
        click.echo(click.style(f"  Hubo {len(errores)} errores:", fg="red"))
        click.echo(click.style(f"  {', '.join(errores)}", fg="red"))

    # Mensaje de termino
    click.echo(f"  Personas: {contador} actualizadas.")


@click.command()
@click.option("--personas-csv", default=PERSONAS_CSV, help="Archivo CSV con los datos de las Personas")
def actualizar_nuevas_columnas(personas_csv: str):
    """Actualizar nuevas columnas de las Personas en base a su RFC a partir de un archivo CSV"""

    # Validar archivo
    ruta = Path(personas_csv)
    if not ruta.exists():
        click.echo(f"ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        click.echo(f"ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)

    # Iniciar sesión con la base de datos para que la alimentación sea rápida
    sesion = database.session

    # Inicializar contadores y mensajes
    contador = 0
    errores = []

    # Leer el archivo CSV
    click.echo("Actualizar Personas: ", nl=False)
    with open(ruta, newline="", encoding="utf8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Consultar la persona
            persona = Persona.query.filter_by(rfc=safe_rfc(row["RFC"])).first()
            if persona is None:
                errores.append(f"RFC {row['RFC']}: Persona no encontrada")
                continue

            # Consultar la plaza
            plaza = Plaza.query.filter_by(clave=safe_clave(row["PLAZA"], max_len=24)).first()
            if plaza is None:
                errores.append(f"Plaza {row['PLAZA']}: Plaza no encontrada")
                continue

            # Tomar Sub Sis
            try:
                sub_sis = int(row["SUB_SIS"])
            except ValueError:
                errores.append(f"Sub Sis {row['SUB_SIS']}: Sub Sis inválido")
                continue

            # Consultar el Puesto
            puesto = Puesto.query.filter_by(clave=safe_clave(row["PUESTO"], max_len=24)).first()
            if puesto is None:
                errores.append(f"Puesto {row['PUESTO']}: Puesto no encontrado")
                continue

            # Tomar nivel
            try:
                nivel = int(row["NIVEL"])
            except ValueError:
                errores.append(f"Nivel {row['NIVEL']}: Nivel inválido")
                continue

            # Tomar el puesto equivalente
            puesto_equivalente = safe_clave(row["PUESTO EQUIVALENTE"])

            # Bandera si hubo cambios
            hay_cambios = False

            # Si es diferente la plaza, actualizar
            if persona.ultimo_plaza_id != plaza.id:
                persona.ultimo_plaza_id = plaza.id
                hay_cambios = True

            # Si es diferente el sub_sis, actualizar
            if persona.sub_sis != sub_sis:
                persona.sub_sis = sub_sis
                hay_cambios = True

            # Si es diferente el puesto, actualizar
            if persona.ultimo_puesto_id != puesto.id:
                persona.ultimo_puesto_id = puesto.id
                hay_cambios = True

            # Si es diferente el nivel, actualizar
            if persona.nivel != nivel:
                persona.nivel = nivel
                hay_cambios = True

            # Si es diferente el puesto_equivalente, actualizar
            if persona.puesto_equivalente != puesto_equivalente:
                persona.puesto_equivalente = puesto_equivalente
                hay_cambios = True

            # Si hay cambios, agregar a la sesión e incrementar el contador
            if hay_cambios:
                sesion.add(persona)
                contador += 1
                click.echo(click.style("u", fg="cyan"), nl=False)

    # Poner avance de linea
    click.echo("")

    # Si no hubo cambios, mostrar mensaje y terminar
    if contador == 0:
        click.echo("  AVISO: No hubo cambios.")
        sys.exit(0)

    # Guardar cambios
    sesion.commit()
    sesion.close()

    # Si hubo errores, mostrarlos
    if len(errores) > 0:
        click.echo(click.style(f"  Hubo {len(errores)} errores:", fg="red"))
        click.echo(click.style(f"  {', '.join(errores)}", fg="red"))

    # Mensaje de termino
    click.echo(f"  Personas: {contador} actualizadas.")


@click.command()
@click.argument("quincena_clave", type=str)
def actualizar_tabuladores(quincena_clave: str):
    """Actualizar los tabuladores de las personas a partir de los archivos de explotacion de una quincena"""

    # Validar quincena
    if re.match(QUINCENA_REGEXP, quincena_clave) is None:
        click.echo("ERROR: Quincena inválida")
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

    # Abrir el archivo XLS con xlrd
    libro = xlrd.open_workbook(str(ruta))

    # Obtener la primera hoja
    hoja = libro.sheet_by_index(0)

    # Definir el puesto generico
    puesto_generico = Puesto.query.filter_by(clave="ND").first()
    if puesto_generico is None:
        click.echo("ERROR: Falta el puesto con clave ND.")
        sys.exit(1)

    # Definir el tabulador generico
    tabulador_generico = Tabulador.query.filter_by(puesto_id=puesto_generico.id).first()
    if tabulador_generico is None:
        click.echo("ERROR: Falta el tabulador del puesto con clave ND.")
        sys.exit(1)

    # Inicializar los listados con las anomalias
    personas_actualizadas_del_tabulador = []
    personas_actualizadas_del_modelo = []
    personas_actualizadas_del_num_empleado = []
    personas_no_encontradas = []
    puestos_claves_no_encontrados = []
    tabuladores_no_encontrados = []

    # Inicializar contadores
    modelos_no_validos_contador = 0
    niveles_no_validos_contador = 0
    personas_actualizadas_contador = 0

    # Bucle por cada fila
    click.echo(f"Actualizando Tabuladores de las Personas con {quincena_clave}: ", nl=False)
    for fila in range(1, hoja.nrows):
        # Tomar las columnas
        rfc = hoja.cell_value(fila, 2)
        modelo = int(hoja.cell_value(fila, 236))
        puesto_clave = safe_clave(hoja.cell_value(fila, 20))
        nivel = int(hoja.cell_value(fila, 9))
        num_empleado = int(hoja.cell_value(fila, 240))

        # Consultar a la persona
        persona = Persona.query.filter_by(rfc=rfc).first()

        # Si no se encuentra, agregar a personas_no_encontradas y saltar
        if persona is None:
            personas_no_encontradas.append(rfc)
            continue

        # Inicializar la bandera para saltar la fila si el concepto es PME
        es_concepto_pme = False

        # Si el modelo es 2, entonces en SINDICALIZADO, se toman 4 caracteres del puesto
        if modelo == 2:
            puesto_clave = puesto_clave[:4]

        # Bucle entre las columnas de los conceptos para encontrar PQ1, PQ2, PQ3, PQ4, PQ5, PQ6 o PME
        quinquenios = 0
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

        # Si el concepto es PME, entonces en esta fila se salta
        if es_concepto_pme:
            continue

        # Consultar el puesto
        puesto = Puesto.query.filter_by(clave=puesto_clave).first()

        # Si no se encuentra, agregar a puestos_claves_no_encontrados y saltar
        if puesto is None:
            puestos_claves_no_encontrados.append(puesto_clave)
            continue

        # Si el modelo NO es 1, 2 o 3, agregar a modelos_no_validos y saltar
        if modelo not in [1, 2, 3]:
            modelos_no_validos_contador += 1
            continue

        # Si el nivel NO esta entre 1 y 9, agregar a niveles_no_validos y saltar
        if nivel not in range(1, 10):
            niveles_no_validos_contador += 1
            continue

        # Consultar el tabulador
        tabulador = Tabulador.query.filter(
            Tabulador.puesto_id == puesto.id,
            Tabulador.modelo == modelo,
            Tabulador.nivel == nivel,
            Tabulador.quinquenio == quinquenios,
        ).first()

        # Si no se encuentra, agregar a la lista de anomalias y saltar
        if tabulador is None:
            tabuladores_no_encontrados.append(f"Puesto: {puesto_clave} Modelo: {modelo} Nivel: {nivel} Quin: {quinquenios}")
            continue

        # Inicializar hay_cambios
        hay_cambios = False

        # Revisar si hay que actualizar el tabulador a la Persona
        if persona.tabulador_id != tabulador.id:
            personas_actualizadas_del_tabulador.append(
                f"{rfc} {persona.nombre_completo}: Tabulador: {persona.tabulador_id} -> {tabulador.id}"
            )
            persona.tabulador_id = tabulador.id
            hay_cambios = True

        # Revisar si hay que actualizar el modelo a la Persona
        if persona.modelo != modelo:
            personas_actualizadas_del_modelo.append(f"{rfc} {persona.nombre_completo}: Modelo: {persona.modelo} -> {modelo}")
            persona.modelo = modelo
            hay_cambios = True

        # Revisar si hay que actualizar el numero de empleado a la Persona
        if persona.num_empleado != num_empleado:
            personas_actualizadas_del_num_empleado.append(
                f"{rfc} {persona.nombre_completo}: No. Emp. {persona.num_empleado} -> {num_empleado}"
            )
            persona.num_empleado = num_empleado
            hay_cambios = True

        # Si hay cambios, guardar la Persona
        if hay_cambios:
            persona.save()
            personas_actualizadas_contador += 1
            click.echo(click.style("u", fg="green"), nl=False)

    # Poner avance de linea
    click.echo("")

    # Si hubo modelos_no_validos, mostrar contador
    if modelos_no_validos_contador > 0:
        click.echo(click.style(f"  Hubo {modelos_no_validos_contador} filas con modelos NO validos, se omiten", fg="yellow"))

    # Si hubo niveles_no_validos, mostrar contador
    if niveles_no_validos_contador > 0:
        click.echo(click.style(f"  Hubo {niveles_no_validos_contador} filas con niveles NO validos, se omiten", fg="yellow"))

    # Si hubo personas_no_encontradas, mostrarlas
    if len(personas_no_encontradas) > 0:
        click.echo(click.style(f"  Hubo {len(personas_no_encontradas)} personas que no se encontraron:", fg="yellow"))
        click.echo(click.style(f"  {', '.join(personas_no_encontradas)}", fg="yellow"))

    # Si hubo puestos_claves_no_encontrados, mostrarlas
    if len(puestos_claves_no_encontrados) > 0:
        click.echo(click.style(f"  Hubo {len(puestos_claves_no_encontrados)} puestos que no se encontraron:", fg="yellow"))
        click.echo(click.style(f"  {', '.join(puestos_claves_no_encontrados)}", fg="yellow"))

    # Si hubo tabuladores_no_encontrados, mostrarlas
    if len(tabuladores_no_encontrados) > 0:
        click.echo(click.style(f"  Hubo {len(tabuladores_no_encontrados)} tabuladores que no se encontraron:", fg="yellow"))
        click.echo(click.style(f"  {', '.join(tabuladores_no_encontrados)}", fg="yellow"))

    # Mensaje termino
    click.echo(click.style(f"  Actualizar tabuladores de las personas: {personas_actualizadas_contador}", fg="green"))


@click.command()
def actualizar_ultimos():
    """Actualizar el último centro de trabajo, plaza y puesto de las Personas a partir de la última nomina"""

    # Ejecutar la tarea
    try:
        mensaje_termino, _, _ = task_actualizar_ultimos()
    except MyAnyError as error:
        click.echo(click.style(str(error), fg="red"))
        sys.exit(1)

    # Mensaje de termino
    click.echo(click.style(mensaje_termino, fg="green"))


@click.command()
@click.argument("rfc", type=str)
@click.argument("tabulador_id", type=int)
def cambiar_tabulador(rfc: str, tabulador_id: int):
    """Cambiar el Tabulador de una Persona"""

    # Validar el RFC
    try:
        rfc = safe_rfc(rfc)
    except ValueError:
        click.echo(f"ERROR: RFC de origen inválido: {rfc}")
        sys.exit(1)

    # Consultar a la persona con el RFC
    persona = Persona.query.filter_by(rfc=rfc).first()
    if persona is None:
        click.echo(f"ERROR: RFC de origen no encontrado: {rfc}")
        sys.exit(1)
    if persona.estatus != "A":
        click.echo(f"ERROR: RFC de origen no activo: {rfc}")
        sys.exit(1)

    # Consultar el tabulador
    tabulador = Tabulador.query.get(tabulador_id)
    if tabulador is None:
        click.echo(f"ERROR: Tabulador no encontrado: {tabulador_id}")
        sys.exit(1)
    if tabulador.estatus != "A":
        click.echo(f"ERROR: Tabulador no activo: {tabulador_id}")
        sys.exit(1)

    # Si el tabulador de la persona es el mismo, mostrar mensaje y terminar
    if persona.tabulador_id == tabulador.id:
        click.echo(f"AVISO: El tabulador de {rfc} ya es {tabulador_id}.")
        sys.exit(0)

    # Actualizar la persona con el tabulador proporcionado
    persona.tabulador_id = tabulador.id
    persona.save()

    # Mensaje de termino
    click.echo(f"AVISO: El tabulador de {rfc} se cambió a {tabulador_id}.")


@click.command()
@click.argument("tabulador_id", type=int)
def cambiar_tabulador_a_todos(tabulador_id: int):
    """Cambiar el Tabulador a TODOS"""

    # Consultar el tabulador
    tabulador = Tabulador.query.get(tabulador_id)
    if tabulador is None:
        click.echo(f"ERROR: Tabulador no encontrado: {tabulador_id}")
        sys.exit(1)
    if tabulador.estatus != "A":
        click.echo(f"ERROR: Tabulador no activo: {tabulador_id}")
        sys.exit(1)

    # Iniciar sesión con la base de datos para que la alimentación sea rápida
    sesion = database.session

    # Inicializar contador
    contador = 0

    # Bucle por las personas activas
    click.echo(f"Cambiar el Tabulador de TODAS las Personas activas a {tabulador_id}: ", nl=False)
    for persona in Persona.query.filter_by(estatus="A").all():
        # Si el tabulador de la persona es el mismo, saltar
        if persona.tabulador_id == tabulador.id:
            continue

        # Actualizar la persona con el tabulador proporcionado
        persona.tabulador_id = tabulador.id
        sesion.add(persona)
        contador += 1
        click.echo(click.style("u", fg="green"), nl=False)

    # Poner avance de linea
    click.echo("")

    # Guardar cambios
    sesion.commit()
    sesion.close()

    # Mensaje termino
    click.echo(click.style(f"  Se cambio el Tabulador a {contador} Personas a {tabulador_id}", fg="green"))


@click.command()
def exportar_xlsx():
    """Exportar Personas a un archivo XLSX"""

    # Ejecutar la tarea
    try:
        mensaje_termino, _, _ = task_exportar_xlsx()
    except MyAnyError as error:
        click.echo(click.style(str(error), fg="red"))
        sys.exit(1)

    # Mensaje de termino
    click.echo(click.style(mensaje_termino, fg="green"))


@click.command()
@click.argument("rfc-origen", type=str)
@click.argument("rfc-destino", type=str)
@click.option("--eliminar", is_flag=True, help="Eliminar el RFC de origen")
def migrar_eliminar_rfc(rfc_origen: str, rfc_destino: str, eliminar: bool):
    """Migrar las nominas y las percepciones_deducciones de una persona a otra y eliminar la persona de origen"""

    # Validar el RFC de origen
    try:
        rfc_origen = safe_rfc(rfc_origen)
    except ValueError:
        click.echo(f"ERROR: RFC de origen inválido: {rfc_origen}")
        sys.exit(1)

    # Validar el RFC de destino
    try:
        rfc_destino = safe_rfc(rfc_destino)
    except ValueError:
        click.echo(f"ERROR: RFC de destino inválido: {rfc_destino}")
        sys.exit(1)

    # Consultar a la persona con el RFC de origen
    persona_origen = Persona.query.filter_by(rfc=rfc_origen).first()
    if persona_origen is None:
        click.echo(f"ERROR: RFC de origen no encontrado: {rfc_origen}")
        sys.exit(1)
    if persona_origen.estatus != "A":
        click.echo(f"ERROR: RFC de origen no activo: {rfc_origen}")
        sys.exit(1)

    # Consultar a la persona con el RFC de destino
    persona_destino = Persona.query.filter_by(rfc=rfc_destino).first()
    if persona_destino is None:
        click.echo(f"ERROR: RFC de destino no encontrado: {rfc_destino}")
        sys.exit(1)
    if persona_destino.estatus != "A":
        click.echo(f"ERROR: RFC de destino no activo: {rfc_destino}")
        sys.exit(1)

    # Iniciar sesión con la base de datos para que la alimentación sea rápida
    sesion = database.session

    # Actualizar las percepciones_deducciones de la persona de origen con la persona de destino
    click.echo(f"Actualizando las percepciones_deducciones de {rfc_origen} a {rfc_destino}...")
    contador_percepciones_deducciones_actualizados = 0
    for percepcion_deduccion in PercepcionDeduccion.query.filter_by(persona_id=persona_origen.id).all():
        percepcion_deduccion.persona_id = persona_destino.id
        sesion.add(percepcion_deduccion)
        contador_percepciones_deducciones_actualizados += 1

    # Actualizar las nominas de la persona de origen con la persona de destino
    click.echo(f"Actualizando las nominas de {rfc_origen} a {rfc_destino}...")
    contador_nominas_actualizados = 0
    for nomina in Nomina.query.filter_by(persona_id=persona_origen.id).all():
        nomina.persona_id = persona_destino.id
        sesion.add(nomina)
        contador_nominas_actualizados += 1

    # Eliminar las cuentas de la persona de origen
    click.echo(f"Eliminando las cuentas de {rfc_origen}...")
    contador_cuentas_eliminadas = 0
    for cuenta in persona_origen.cuentas:
        cuenta.estatus = "B"
        sesion.add(cuenta)
        contador_cuentas_eliminadas += 1

    # Eliminar la persona de origen
    if eliminar:
        persona_origen.estatus = "B"
        sesion.add(persona_origen)

    # Guardar cambios
    sesion.commit()
    sesion.close()

    # Si hubo actulizaciones en percepciones_deducciones, mostrar mensaje
    if contador_percepciones_deducciones_actualizados > 0:
        click.echo(f"Percepciones/Deducciones: {contador_percepciones_deducciones_actualizados} actualizados.")

    # Si hubo actulizaciones en nominas, mostrar mensaje
    if contador_nominas_actualizados > 0:
        click.echo(f"Nominas: {contador_nominas_actualizados} actualizadas.")

    # Si hubo eliminaciones en cuentas, mostrar mensaje
    if contador_cuentas_eliminadas > 0:
        click.echo(f"Cuentas: {contador_cuentas_eliminadas} eliminadas.")

    # Si se elimino la persona de origen, mostrar mensaje
    if eliminar:
        click.echo(f"Persona {rfc_origen} eliminada.")

    # Mensaje de termino
    click.echo(f"Ya se migró {rfc_origen} a {rfc_destino}.")


@click.command()
def sincronizar_con_rrhh_personal():
    """Sincronizar las Personas consultando la API de RRHH Personal"""
    click.echo("Sincronizando Personas...")

    # Validar que se haya definido RRHH_PERSONAL_URL
    if RRHH_PERSONAL_URL is None:
        click.echo("ERROR: No se ha definido RRHH_PERSONAL_URL.")
        sys.exit(1)

    # Validar que se haya definido RRHH_PERSONAL_API_KEY
    if RRHH_PERSONAL_API_KEY is None:
        click.echo("ERROR: No se ha definido RRHH_PERSONAL_API_KEY.")
        sys.exit(1)

    # Iniciar sesión con la base de datos para que la alimentación sea rápida
    sesion = database.session

    # Bucle por los RFC's de Personas
    contador = 0
    for persona in Persona.query.filter_by(estatus="A").order_by(Persona.rfc).all():
        # Consultar a la API
        try:
            respuesta = requests.get(
                f"{RRHH_PERSONAL_URL}/personas",
                headers={"X-Api-Key": RRHH_PERSONAL_API_KEY},
                params={"rfc": safe_rfc(persona.rfc)},
                timeout=TIMEOUT,
            )
            respuesta.raise_for_status()
        except requests.exceptions.ConnectionError:
            click.echo("ERROR: No hubo respuesta al solicitar persona")
            sys.exit(1)
        except requests.exceptions.HTTPError as error:
            click.echo("ERROR: Status Code al solicitar persona: " + str(error))
            sys.exit(1)
        except requests.exceptions.RequestException:
            click.echo("ERROR: Inesperado al solicitar persona")
            sys.exit(1)
        datos = respuesta.json()
        if "success" not in datos:
            click.echo("ERROR: Fallo al solicitar persona")
            sys.exit(1)
        if datos["success"] is False:
            if "message" in datos:
                click.echo(f"  AVISO: Fallo en Persona {persona.rfc}: {datos['message']}")
            else:
                click.echo(f"  AVISO: Fallo en Persona {persona.rfc}")
            continue

        # Si no contiene resultados, saltar
        if len(datos["items"]) == 0:
            click.echo(f"  AVISO: RFC: {persona.rfc} no encontrado")
            continue
        item = datos["items"][0]

        # Verificar la CURP de la persona
        try:
            curp = safe_curp(item["curp"])
        except ValueError:
            click.echo(f"  AVISO: La persona {persona.rfc}, tiene una CURP incorrecta {item['curp']}")
            curp = ""

        # Verificar la fecha de ingreso a gobierno como fecha
        fecha_ingreso_gobierno = None
        try:
            if item["fecha_ingreso_gobierno"] is not None:
                fecha_ingreso_gobierno = datetime.strptime(item["fecha_ingreso_gobierno"], "%Y-%m-%d").date()
        except ValueError as e:
            click.echo(f"  AVISO: La persona {persona.rfc}, tiene una Fecha de ingreso a gobierno incorrecta. {e}")

        # Verificar la fecha de ingreso a PJ como fecha
        fecha_ingreso_pj = None
        try:
            if item["fecha_ingreso_pj"] is not None:
                fecha_ingreso_pj = datetime.strptime(item["fecha_ingreso_pj"], "%Y-%m-%d").date()
        except ValueError as e:
            click.echo(f"  AVISO: La persona {persona.rfc}, tiene una Fecha de ingreso a PJ incorrecta. {e}")

        # Actualizar si hay cambios
        se_va_a_actualizar = False
        if curp != "" and persona.curp != curp:
            se_va_a_actualizar = True
            persona.curp = curp
        if fecha_ingreso_gobierno is not None and fecha_ingreso_gobierno != persona.ingreso_gobierno_fecha:
            se_va_a_actualizar = True
            persona.ingreso_gobierno_fecha = fecha_ingreso_gobierno
        if fecha_ingreso_pj is not None and fecha_ingreso_pj != persona.ingreso_pj_fecha:
            se_va_a_actualizar = True
            persona.ingreso_pj_fecha = fecha_ingreso_pj

        # Añadir cambios e incrementar el contador
        if se_va_a_actualizar:
            # click.echo(f"  Persona con cambios: {persona}")
            sesion.add(persona)
            contador += 1
            if contador % 100 == 0:
                click.echo(f"  Van {contador}...")
                sesion.commit()

    # Guardar cambios
    if contador > 0:
        sesion.commit()
        sesion.close()

    # Mensaje de termino
    click.echo(f"Personas: {contador} sincronizados.")


cli.add_command(actualizar_datos_fiscales)
cli.add_command(actualizar_datos_personales)
cli.add_command(actualizar_ultimos)
cli.add_command(actualizar_nuevas_columnas)
cli.add_command(actualizar_tabuladores)
cli.add_command(actualizar_ultimos)
cli.add_command(cambiar_tabulador)
cli.add_command(cambiar_tabulador_a_todos)
cli.add_command(exportar_xlsx)
cli.add_command(migrar_eliminar_rfc)
cli.add_command(sincronizar_con_rrhh_personal)
