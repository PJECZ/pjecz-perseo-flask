"""
CLI Quincenas
"""

import sys

import click

from pjecz_perseo_flask.blueprints.quincenas.tasks import cerrar as task_cerrar


@click.group()
def cli():
    """Quincenas"""


@click.command()
def cerrar():
    """Lanzar cerrar TODAS las quincenas con estado ABIERTA"""

    # Ejecutar la tarea
    try:
        mensaje_termino, _, _ = task_cerrar()
    except Exception as error:
        click.echo(click.style(str(error), fg="red"))
        sys.exit(1)

    # Mensaje de termino
    click.echo(click.style(mensaje_termino, fg="green"))


cli.add_command(cerrar)
