"""
CLI Personas
"""
import os
import sys

import click
import requests
from dotenv import load_dotenv
from datetime import datetime

from lib.safe_string import safe_curp, safe_rfc, safe_string
from perseo.app import create_app
from perseo.blueprints.personas.models import Persona
from perseo.extensions import database

load_dotenv()

RRHH_PERSONAL_URL = os.getenv("RRHH_PERSONAL_URL")
RRHH_PERSONAL_API_KEY = os.getenv("RRHH_PERSONAL_API_KEY")
TIMEOUT = 12

app = create_app()
app.app_context().push()
database.app = app


@click.group()
def cli():
    """Personas"""


@click.command()
def sincronizar():
    """Sincronizar las Personas con la información de RRHH Personal"""
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
            click.echo(f"  RFC: {persona.rfc} no encontrado")
            continue
        item = datos["items"][0]

        # Verificar la CURP de la persona
        try:
            curp = safe_curp(item["curp"])
        except ValueError:
            click.echo(f"  ERROR: La persona {persona.rfc}, tiene una CURP incorrecta {item['curp']}")
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
        actualizar = False
        if curp != "" and persona.curp != curp:
            actualizar = True
            persona.curp = curp
        if fecha_ingreso_gobierno is not None and fecha_ingreso_gobierno != persona.ingreso_gobierno_fecha:
            actualizar = True
            persona.ingreso_gobierno_fecha = fecha_ingreso_gobierno
        if fecha_ingreso_pj is not None and fecha_ingreso_pj != persona.ingreso_pj_fecha:
            actualizar = True
            persona.ingreso_pj_fecha = fecha_ingreso_pj

        # Añadir cambios e incrementar el contador
        if actualizar:
            click.echo(f"  Persona con cambios: {persona}")
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


cli.add_command(sincronizar)
