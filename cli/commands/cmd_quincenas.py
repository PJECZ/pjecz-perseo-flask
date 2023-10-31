"""
CLI Quincenas
"""
import click

from perseo.app import create_app
from perseo.blueprints.quincenas.models import Quincena
from perseo.extensions import database

app = create_app()
app.app_context().push()
database.app = app


@click.group()
def cli():
    """Quincenas"""


@click.command()
def cerrar():
    """Cerrar las quincenas con estado ABIERTA, a execpcion de la ultima quincena"""

    # Iniciar sesion con la base de datos para que la alimentacion sea rapida
    sesion = database.session

    # Consultar todas las quincenas con estatus "A"
    quincenas = sesion.query(Quincena).order_by(Quincena.quincena).filter_by(estatus="A").all()

    # Si no hay quincenas, mostrar mensaje de error y salir
    if len(quincenas) == 0:
        click.echo("ERROR: No hay quincenas activas.")
        return

    # Inicializar contador de cambios
    contador = 0

    # Separar la ultima quincena de las demas
    ultima_quincena = quincenas.pop()

    # Bucle por las quincenas
    for quincena_obj in quincenas:
        # Si la quincena esta abierta, cerrarla
        if quincena_obj.estado == "ABIERTA":
            quincena_obj.estado = "CERRADA"
            sesion.add(quincena_obj)
            click.echo(f"  Quincena {quincena_obj.quincena} ahora esta CERRADA")
            contador += 1

    # Si la ultima quincena esta cerrada, abrirla
    if ultima_quincena.estado == "CERRADA":
        ultima_quincena.estado = "ABIERTA"
        sesion.add(ultima_quincena)
        click.echo(f"  Quincena {ultima_quincena.quincena} ahora esta ABIERTA")
        contador += 1

    # Hacer commit de los cambios en la base de datos
    sesion.commit()

    # Mostrar mensaje de termino, si no hubo cambios o la cantidad de los mismos
    if contador == 0:
        click.echo("Quincenas terminado: No se hicieron cambios")
        return
    click.echo(f"Quincenas terminado: {contador} cambios")


cli.add_command(cerrar)
