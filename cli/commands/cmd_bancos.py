"""
CLI Bancos
"""
import csv
from pathlib import Path

import click

from lib.safe_string import safe_string
from perseo.app import create_app
from perseo.blueprints.bancos.models import Banco

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
            except ValueError as error:
                click.echo(f"  {error}")
                continue
            Banco(
                clave=clave,
                nombre=nombre,
                consecutivo=0,
                consecutivo_generado=0,
            ).save()
            contador += 1
            if contador % 100 == 0:
                click.echo(f"  Van {contador}...")
    click.echo(f"Terminado con {contador} bancos alimentados.")


cli.add_command(alimentar)
