"""
CLI Plazas
"""

import sys

import click

from pjecz_perseo_flask.blueprints.plazas.tasks import exportar_xlsx
from pjecz_perseo_flask.main import app

# Inicializar el contexto de la aplicación Flask
app.app_context().push()


@click.group()
def cli():
    """Plazas"""


@click.command()
def exportar():
    """Exportar Plazas a un archivo XLSX"""

    # Ejecutar la tarea
    try:
        mensaje_termino, _, _ = exportar_xlsx()
    except Exception as error:
        click.echo(click.style(str(error), fg="red"))
        sys.exit(1)

    # Mensaje de termino
    click.echo(click.style(mensaje_termino, fg="green"))


cli.add_command(exportar)
