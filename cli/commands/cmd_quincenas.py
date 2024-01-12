"""
CLI Quincenas
"""
import os
import sys

import click
from dotenv import load_dotenv

from perseo.app import create_app
from perseo.blueprints.bancos.models import Banco
from perseo.blueprints.quincenas.models import Quincena
from perseo.extensions import database

app = create_app()
app.app_context().push()
database.app = app

load_dotenv()
HOST = os.getenv("HOST", "http://localhost:5000")


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
        sys.exit(1)

    # Bucle por las quincenas
    contador = 0
    for quincena_obj in quincenas:
        # Si la quincena esta abierta, cerrarla
        if quincena_obj.estado == "ABIERTA":
            quincena_obj.estado = "CERRADA"
            sesion.add(quincena_obj)
            click.echo(f"  Quincena {quincena_obj.quincena} ahora esta CERRADA")
            contador += 1

    # Si no hubo cambios, mostrar mensaje
    if contador == 0:
        click.echo("AVISO: No hubo quincenas por cerrar.")

    # Igualar los consecutivos a los consecutivos_generado de los bancos
    bancos_actualizados_contador = 0
    for banco in Banco.query.filter_by(estatus="A").all():
        if banco.consecutivo != banco.consecutivo_generado:
            antes = banco.consecutivo
            ahora = banco.consecutivo_generado
            banco.consecutivo = banco.consecutivo_generado
            sesion.add(banco)
            click.echo(f"  {banco.nombre} ({antes} -> {ahora})")
            bancos_actualizados_contador += 1

    # Si no hubo cambios, mostrar mensaje
    if bancos_actualizados_contador == 0:
        click.echo("AVISO: No hubo consecutivos de los bancos por cambiar.")

    # TODO: Actualizar nominas, beneficiarios_quincenas con su numero de cheque definitivo

    # Hacer commit de los cambios en la base de datos
    sesion.commit()

    # Mostrar mensaje de termino, si no hubo cambios o la cantidad de los mismos
    click.echo(f"Quincenas terminado: {contador} cambios en quincenas, {bancos_actualizados_contador} cambios en bancos.")


cli.add_command(cerrar)
