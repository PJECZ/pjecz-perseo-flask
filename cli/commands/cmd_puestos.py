"""
CLI Puestos
"""

import sys

import click

from pjecz_perseo_flask.blueprints.puestos.tasks import exportar_xlsx as task_exportar_xlsx
from pjecz_perseo_flask.main import app

# Inicializar el contexto de la aplicación Flask
app.app_context().push()


@click.group()
def cli():
    """Puestos"""


@click.command()
def exportar_xlsx():
    """Exportar Puestos a un archivo XLSX"""

    # Ejecutar la tarea
    try:
        mensaje_termino, _, _ = task_exportar_xlsx()
    except Exception as error:
        click.echo(click.style(str(error), fg="red"))
        sys.exit(1)

    # Mensaje de termino
    click.echo(click.style(mensaje_termino, fg="green"))


cli.add_command(exportar_xlsx)
