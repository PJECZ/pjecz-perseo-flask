"""
CLI Tabuladores
"""
import csv
import sys
from pathlib import Path

import click

from lib.safe_string import safe_clave
from perseo.app import create_app
from perseo.blueprints.puestos.models import Puesto

PUESTOS_CSV = "seed/puestos.csv"

app = create_app()
app.app_context().push()


@click.group()
def cli():
    """Puestos"""


@click.command()
@click.option("--puestos-csv", default=PUESTOS_CSV, help="Archivo CSV con los datos")
def agregar(puestos_csv: str):
    """Agregar puestos a partir de un archivo CSV"""

    # Validar archivo CSV
    ruta = Path(puestos_csv)
    if not ruta.exists():
        click.echo(f"ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        click.echo(f"ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)
