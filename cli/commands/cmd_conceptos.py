"""
CLI Conceptos

Columnas del CSV:

- P_D
- Concepto
- Descripcion

"""
import csv
from pathlib import Path

import click

from lib.safe_string import safe_clave, safe_string
from perseo.app import create_app
from perseo.blueprints.centros_trabajos.models import CentroTrabajo
from perseo.blueprints.conceptos.models import Concepto
from perseo.blueprints.conceptos_productos.models import ConceptoProducto
from perseo.blueprints.percepciones_deducciones.models import PercepcionDeduccion
from perseo.blueprints.personas.models import Persona
from perseo.blueprints.plazas.models import Plaza
from perseo.blueprints.productos.models import Producto

CONCEPTOS_CSV = "seed/conceptos.csv"

app = create_app()
app.app_context().push()


@click.group()
def cli():
    """Conceptos"""


@click.command()
def alimentar():
    """Alimentar conceptos"""
    ruta = Path(CONCEPTOS_CSV)
    if not ruta.exists():
        click.echo(f"AVISO: {ruta.name} no se encontró.")
        return
    if not ruta.is_file():
        click.echo(f"AVISO: {ruta.name} no es un archivo.")
        return
    click.echo("Alimentando conceptos...")
    contador = 0
    with open(ruta, newline="", encoding="utf8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                clave = safe_clave(f"{row['P_D']}{row['Concepto']}")
                descripcion = safe_string(row["Descripcion"])
            except ValueError as error:
                click.echo(f"  {error}")
                continue
            Concepto(
                clave=clave,
                descripcion=descripcion,
            ).save()
            contador += 1
            if contador % 100 == 0:
                click.echo(f"  Van {contador}...")
    click.echo(f"Terminado con {contador} conceptos alimentados.")


cli.add_command(alimentar)
