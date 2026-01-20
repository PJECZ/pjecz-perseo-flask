"""
CLI Bancos
"""

import sys

import click

from pjecz_perseo_flask.blueprints.bancos.tasks import reiniciar_consecutivos_generados as task_reiniciar_consecutivos_generados


@click.group()
def cli():
    """Bancos"""


@click.command()
def reiniciar_consecutivos_temp():
    """Lanzar reiniciar los consecutivos temporales"""

    # Ejecutar la tarea
    try:
        mensaje_termino, _, _ = task_reiniciar_consecutivos_generados()
    except Exception as error:
        click.echo(click.style(str(error), fg="red"))
        sys.exit(1)

    # Mensaje de termino
    click.echo(click.style(mensaje_termino, fg="green"))


cli.add_command(reiniciar_consecutivos_temp)
