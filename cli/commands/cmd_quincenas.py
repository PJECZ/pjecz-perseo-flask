"""
CLI Quincenas
"""
import click

from perseo.app import create_app
from perseo.blueprints.bancos.models import Banco
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
    """Cerrar TODAS las quincenas con estado ABIERTA"""

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

    # Bucle por las quincenas
    for quincena_obj in quincenas:
        # Si la quincena esta abierta, cerrarla
        if quincena_obj.estado == "ABIERTA":
            quincena_obj.estado = "CERRADA"
            sesion.add(quincena_obj)
            click.echo(f"  Quincena {quincena_obj.quincena} ahora esta CERRADA")
            contador += 1

    # Si no hubo cambios, mostrar mensaje y salir
    if contador == 0:
        click.echo("Quincenas terminado: No se hicieron cambios")
        return

    # Igualar los consecutivos a los consecutivos_generado de los bancos
    for banco in Banco.query.filter_by(estatus="A").all():
        if banco.consecutivo != banco.consecutivo_generado:
            banco.consecutivo = banco.consecutivo_generado
            sesion.add(banco)
            click.echo(f"  Consecutivo de {banco.nombre} ahora es {banco.consecutivo}")

    # Hacer commit de los cambios en la base de datos
    sesion.commit()

    # Mostrar mensaje de termino, si no hubo cambios o la cantidad de los mismos
    click.echo(f"Quincenas terminado: {contador} cambios")


cli.add_command(cerrar)
