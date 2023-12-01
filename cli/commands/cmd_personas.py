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
from dotenv import load_dotenv

from lib.safe_string import safe_curp, safe_rfc
from perseo.app import create_app
from perseo.blueprints.personas.models import Persona
from perseo.extensions import database

load_dotenv()

RRHH_PERSONAL_URL = os.getenv("RRHH_PERSONAL_URL")
RRHH_PERSONAL_API_KEY = os.getenv("RRHH_PERSONAL_API_KEY")
TIMEOUT = 12

PERSONAS_CSV = "seed/personas.csv"

app = create_app()
app.app_context().push()
database.app = app


@click.group()
def cli():
    """Personas"""


@click.command()
@click.option("--personas-csv", default=PERSONAS_CSV, help="Archivo CSV con los datos de las Personas")
def actualizar(personas_csv: str):
    """Actualizar los CP y/o CURP de las Personas en base a su RFC a partir de un archivo CSV"""

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

            # Validar el numero de seguridad social
            seguridad_social = None
            if "seguridad_social" in row and row["seguridad_social"] != "":
                if re.match(r"^\d{1,24}$", row["seguridad_social"]):
                    seguridad_social = row["seguridad_social"]
                    if persona.seguridad_social != seguridad_social:
                        persona.seguridad_social = seguridad_social
                        hay_cambios = True
                else:
                    errores.append(f"{row['rfc']}: NSS inválido: {row['seguridad_social']}")

            # Si hubo cambios, agregar a la sesión e incrementar el contador
            if hay_cambios:
                sesion.add(persona)
                contador += 1
                click.echo(click.style(".", fg="cyan"), nl=False)

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
def sincronizar():
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


cli.add_command(actualizar)
cli.add_command(sincronizar)
