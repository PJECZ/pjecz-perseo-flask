"""
CLI Plazas
"""
import sys

import click

from lib.exceptions import MyAnyError
from perseo.app import create_app
from perseo.blueprints.plazas.tasks import exportar_plazas

app = create_app()
app.app_context().push()


@click.group()
def cli():
    """Plazas"""


@click.command()
def exportar():
    """Exportar Plazas a un archivo XLSX"""

    # Ejecutar la tarea
    try:
        mensaje = exportar_plazas()
    except MyAnyError as error:
        click.echo(click.style(str(error), fg="red"))
        sys.exit(1)

    # Mensaje de termino
    click.echo(click.style(mensaje, fg="green"))


cli.add_command(exportar)
