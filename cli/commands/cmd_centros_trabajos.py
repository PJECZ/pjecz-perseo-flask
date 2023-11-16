"""
CLI Centros de Trabajo
"""
import os
import sys

import click
import requests
from dotenv import load_dotenv

from lib.safe_string import safe_string
from perseo.app import create_app
from perseo.blueprints.centros_trabajos.models import CentroTrabajo
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
    """Centros de Trabajo"""


@click.command()
def sincronizar():
    """Sincronizar los Centros de Trabajo con la informacion de RRHH Personal"""
    click.echo("Sincronizando Centros de Trabajo...")

    # Validar que se haya definido RRHH_PERSONAL_URL
    if RRHH_PERSONAL_URL is None:
        click.echo("ERROR: No se ha definido RRHH_PERSONAL_URL.")
        sys.exit(1)

    # Validar que se haya definido RRHH_PERSONAL_API_KEY
    if RRHH_PERSONAL_API_KEY is None:
        click.echo("ERROR: No se ha definido RRHH_PERSONAL_API_KEY.")
        sys.exit(1)

    # Iniciar sesion con la base de datos para que la alimentacion sea rapida
    sesion = database.session

    # Bucle por las claves de los Centros de Trabajo
    contador = 0
    for centro_trabajo in CentroTrabajo.query.filter_by(estatus="A").all():
        # Consultar a la API
        try:
            respuesta = requests.get(
                f"{RRHH_PERSONAL_URL}/centros_trabajos/{centro_trabajo.clave}",
                headers={"X-Api-Key": RRHH_PERSONAL_API_KEY},
                timeout=TIMEOUT,
            )
            respuesta.raise_for_status()
        except requests.exceptions.ConnectionError:
            click.echo("ERROR: No hubo respuesta al solicitar centros de trabajo")
            sys.exit(1)
        except requests.exceptions.HTTPError as error:
            click.echo("ERROR: Status Code al solicitar centros de trabajo: " + str(error))
            sys.exit(1)
        except requests.exceptions.RequestException:
            click.echo("ERROR: Inesperado al solicitar centros de trabajo")
            sys.exit(1)
        datos = respuesta.json()
        if "success" not in datos:
            click.echo("ERROR: Fallo al solicitar centros de trabajo")
            sys.exit(1)
        if datos["success"] is False:
            if "message" in datos:
                click.echo(f"  AVISO: Fallo en Centro de Trabajo {centro_trabajo.clave}: {datos['message']}")
            else:
                click.echo(f"  AVISO: Fallo en Centro de Trabajo {centro_trabajo.clave}")
            continue

        # Actualizar el Centro de Trabajo
        descripcion = safe_string(datos["nombre"], save_enie=True)
        if centro_trabajo.descripcion != descripcion:
            centro_trabajo.descripcion = descripcion
            sesion.add(centro_trabajo)
            contador += 1
            if contador % 100 == 0:
                click.echo(f"  Van {contador}...")
            # click.echo(f"Centro de Trabajo {centro_trabajo.clave} actualizado.")

    # Guardar cambios
    if contador > 0:
        sesion.commit()
        sesion.close()

    # Mensaje de termino
    click.echo(f"Centros de Trabajo: {contador} sincronizados.")


cli.add_command(sincronizar)
