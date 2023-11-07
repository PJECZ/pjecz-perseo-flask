"""
CLI Centros de Trabajo
"""
import os

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

    # Validar que se haya definido RRHH_PERSONAL_URL
    if RRHH_PERSONAL_URL is None:
        click.echo("AVISO: No se ha definido RRHH_PERSONAL_URL.")
        return

    # Validar que se haya definido RRHH_PERSONAL_API_KEY
    if RRHH_PERSONAL_API_KEY is None:
        click.echo("AVISO: No se ha definido RRHH_PERSONAL_API_KEY.")
        return

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
            click.echo("No hubo respuesta al solicitar centros de trabajo")
            return
        except requests.exceptions.HTTPError as error:
            click.echo("Status Code al solicitar centros de trabajo: " + str(error))
            return
        except requests.exceptions.RequestException:
            click.echo("Error inesperado al solicitar centros de trabajo")
            return
        datos = respuesta.json()
        if "success" not in datos:
            click.echo("Fallo al solicitar centros de trabajo")
            return
        if datos["success"] is False:
            if "message" in datos:
                click.echo(f"Fallo al solicitar centros de trabajo con clave {centro_trabajo.clave}: {datos['message']}")
            else:
                click.echo(f"Fallo al solicitar centros de trabajo con clave {centro_trabajo.clave}")
            continue

        # Actualizar el Centro de Trabajo
        descripcion = safe_string(datos["nombre"], save_enie=True)
        if centro_trabajo.descripcion != descripcion:
            centro_trabajo.descripcion = descripcion
            sesion.add(centro_trabajo)
            contador += 1
            click.echo(f"Centro de Trabajo {centro_trabajo.clave} actualizado.")

    # Guardar cambios
    if contador > 0:
        sesion.commit()
        sesion.close()

    # Mensaje de termino
    click.echo(f"Centros de Trabajo {contador} sincronizados.")


cli.add_command(sincronizar)
