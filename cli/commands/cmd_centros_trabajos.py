"""
CLI Centros de Trabajo
"""

import csv
import os
import sys
from pathlib import Path

import click
import requests
from dotenv import load_dotenv

from lib.exceptions import MyAnyError
from lib.safe_string import safe_clave, safe_string
from perseo.app import create_app
from perseo.blueprints.centros_trabajos.models import CentroTrabajo
from perseo.blueprints.centros_trabajos.tasks import exportar_xlsx as task_exportar_xlsx
from perseo.extensions import database

load_dotenv()

RRHH_PERSONAL_URL = os.getenv("RRHH_PERSONAL_URL")
RRHH_PERSONAL_API_KEY = os.getenv("RRHH_PERSONAL_API_KEY")
TIMEOUT = 12

CENTROS_TRABAJOS_CSV = "seed/centros_trabajos.csv"

app = create_app()
app.app_context().push()
database.app = app


@click.group()
def cli():
    """Centros de Trabajo"""


@click.command()
@click.option("--centros-trabajos-csv", default=CENTROS_TRABAJOS_CSV, help="Archivo CSV con los datos de los C.T.")
def agregar_actualizar(centros_trabajos_csv: str):
    """Agregar o actualizar C.T. a partir de un archivo CSV"""

    # Validar archivo
    ruta = Path(centros_trabajos_csv)
    if not ruta.exists():
        click.echo(f"ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        click.echo(f"ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)

    # Inicializar los contadores
    agregados_contador = 0
    actualizados_contador = 0

    # Leer el archivo CSV
    click.echo("Actualizar Personas: ", nl=False)
    with open(ruta, newline="", encoding="utf8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Validar que tenga clave
            if "clave" not in row:
                click.echo("ERROR: No se encontro la columna 'clave' en el archivo CSV.")
                sys.exit(1)
            clave = safe_clave(row["clave"])

            # Consultar el Centro de Trabajo
            centro_trabajo = CentroTrabajo.query.filter_by(clave=clave).first()

            # Si no existe, agregar
            if centro_trabajo is None:
                centro_trabajo = CentroTrabajo(
                    clave=clave,
                    descripcion=safe_string(row["descripcion"], save_enie=True),
                )
                centro_trabajo.save()
                agregados_contador += 1
                click.echo(click.style("u", fg="green"), nl=False)
                continue

            # Bandera si hubo cambios
            hay_cambios = False

            # Si la descripcion es diferente, actualizar
            if "descripcion" in row:
                descripcion = safe_string(row["descripcion"], save_enie=True)
                if centro_trabajo.descripcion != descripcion:
                    centro_trabajo.descripcion = row["descripcion"]
                hay_cambios = True

            # Si hubo cambios, agregar a la sesión e incrementar el contador
            if hay_cambios:
                centro_trabajo.save()
                actualizados_contador += 1
                click.echo(click.style("u", fg="cyan"), nl=False)

    # Poner avance de linea
    click.echo("")

    # Si no hubo agregados o actualizados, mostrar mensaje y terminar
    if agregados_contador == 0 and actualizados_contador == 0:
        click.echo("  AVISO: No hubo cambios.")
        sys.exit(0)

    # Mensaje de termino
    click.echo("  Centros de Trabajo: ", nl=False)
    if agregados_contador > 0:
        click.echo(f" {agregados_contador} agregados", nl=False)
    if actualizados_contador > 0:
        click.echo(f" {actualizados_contador} actualizados", nl=False)
    click.echo("")


@click.command()
def exportar_xlsx():
    """Exportar Centros de Trabajo a un archivo XLSX"""

    # Ejecutar la tarea
    try:
        mensaje_termino, _, _ = task_exportar_xlsx()
    except MyAnyError as error:
        click.echo(click.style(str(error), fg="red"))
        sys.exit(1)

    # Mensaje de termino
    click.echo(click.style(mensaje_termino, fg="green"))


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


cli.add_command(agregar_actualizar)
cli.add_command(exportar_xlsx)
cli.add_command(sincronizar)
