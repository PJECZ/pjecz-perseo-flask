"""
CLI Bancos
"""
import csv
from pathlib import Path

import click

from lib.safe_string import safe_string
from perseo.app import create_app
from perseo.blueprints.bancos.models import Banco
from perseo.extensions import database

BANCOS_CSV = "seed/bancos.csv"

app = create_app()
app.app_context().push()


@click.group()
def cli():
    """Bancos"""


@click.command()
def alimentar():
    """Alimentar bancos"""
    ruta = Path(BANCOS_CSV)
    if not ruta.exists():
        click.echo(f"AVISO: {ruta.name} no se encontró.")
        return
    if not ruta.is_file():
        click.echo(f"AVISO: {ruta.name} no es un archivo.")
        return
    click.echo("Alimentando bancos...")
    contador = 0
    with open(ruta, newline="", encoding="utf8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                clave = row["clave"]
                nombre = safe_string(row["nombre"])
                clave_dispersion_pensionados = row["clave_dispersion_pensionados"]
            except ValueError as error:
                click.echo(f"  {error}")
                continue
            Banco(
                clave=clave,
                clave_dispersion_pensionados=clave_dispersion_pensionados,
                nombre=nombre,
                consecutivo=0,
                consecutivo_generado=0,
            ).save()
            contador += 1
            if contador % 100 == 0:
                click.echo(f"  Van {contador}...")
    click.echo(f"Bancos terminado: {contador} bancos alimentados.")


@click.command()
def reiniciar_consecutivos_generados():
    """Reiniciar los consecutivos generados de cada banco con el consecutivo"""

    # Iniciar sesion con la base de datos para que la alimentacion sea rapida
    sesion = database.session

    # Bucle por todos los bancos
    contador = 0
    for banco in Banco.query.filter_by(estatus="A").all():
        # Si son diferentes
        if banco.consecutivo_generado != banco.consecutivo:
            # Poner el valor de consecutivo generado con el de consecutivo
            banco.consecutivo_generado = banco.consecutivo

            # Guardar el banco
            sesion.add(banco)

            # Mostrar en pantalla el cambio
            click.echo(f"- {banco.nombre} ({banco.consecutivo_generado})")

            # Incrementar el contador
            contador += 1

    # Si no hubo cambios
    if contador == 0:
        click.echo("No hubo necesidad de reiniciar ningun consecutivo_generado.")
        return

    # Actualizar los consecutivos_generados de cada banco
    sesion.commit()

    # Mensaje de termino
    click.echo(f"{contador} consecutivos generados reiniciados.")


cli.add_command(alimentar)
cli.add_command(reiniciar_consecutivos_generados)
