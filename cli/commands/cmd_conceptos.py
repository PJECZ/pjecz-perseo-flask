"""
CLI Conceptos

Columnas del CSV:

- P_D
- Concepto
- Descripcion

"""
import csv
import re
import sys
from pathlib import Path

import click

from lib.safe_string import QUINCENA_REGEXP, safe_clave, safe_string
from perseo.app import create_app
from perseo.blueprints.centros_trabajos.models import CentroTrabajo
from perseo.blueprints.conceptos.models import Concepto
from perseo.blueprints.conceptos_productos.models import ConceptoProducto
from perseo.blueprints.percepciones_deducciones.models import PercepcionDeduccion
from perseo.blueprints.personas.models import Persona
from perseo.blueprints.plazas.models import Plaza
from perseo.blueprints.productos.models import Producto
from perseo.blueprints.quincenas.models import Quincena

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
        click.echo(f"ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        click.echo(f"ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)
    click.echo("Alimentando Conceptos...")
    contador = 0
    with open(ruta, newline="", encoding="utf8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                clave = safe_clave(f"{row['P_D']}{row['Concepto']}")
                descripcion = safe_string(row["Descripcion"], save_enie=True)
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
    click.echo(f"Conceptos terminado: {contador} conceptos alimentados.")


@click.command()
@click.option("--quincena-clave", default="", help="6 digitos")
def eliminar_recuperar(quincena_clave: str):
    """Eliminar o recuperar Conceptos si no/si se usan en Percepciones-Deducciones"""
    click.echo("Eliminar Conceptos que no se usan...")

    # Si viene la quincena, validar y consultar
    quincena = None
    if quincena_clave != "":
        if re.match(QUINCENA_REGEXP, quincena_clave) is None:
            click.echo("ERROR: Quincena inválida.")
            sys.exit(1)
        quincena = Quincena.query.filter_by(clave=quincena_clave).filter_by(estatus="A").first()
        if quincena is None:
            click.echo("ERROR: Quincena no encontrada o eliminada.")
            sys.exit(1)

    # Consultar todos los conceptos, en uso y eliminados
    conceptos = Concepto.query.all()

    # Si no hay conceptos, salir
    if not conceptos:
        click.echo("AVISO: No hay conceptos.")
        sys.exit(0)

    # Bucle por cada concepto
    conceptos_eliminados = []
    conceptos_recuperados = []
    for concepto in conceptos:
        # Consultar las Percepciones-Deducciones que usen el concepto en turno
        percepciones_deducciones = PercepcionDeduccion.query.filter_by(concepto_id=concepto.id)

        # Si se especifico la quincena, filtrar las P-D por quincena
        if quincena is not None:
            percepciones_deducciones = percepciones_deducciones.filter_by(quincena_id=quincena.id)

        # Si la cantidad de Percepciones-Deducciones es 0, eliminar el concepto, de lo contrario, recuperarlo
        if percepciones_deducciones.count() == 0 and concepto.estatus == "A":
            concepto.estatus = "B"
            concepto.save()
            conceptos_eliminados.append(concepto.clave)
        elif percepciones_deducciones.count() > 0 and concepto.estatus == "B":
            concepto.estatus = "A"
            concepto.save()
            conceptos_recuperados.append(concepto.clave)

    # Si hubo conceptos eliminados, mostrarlos
    click.echo(click.style(f"Se eliminaron {len(conceptos_eliminados)} Conceptos", fg="red"))
    click.echo(click.style(f"  {', '.join(conceptos_eliminados)}", fg="red"))

    # Si hubo conceptos recuperados, mostrarlos
    click.echo(click.style(f"Se recuperaron {len(conceptos_recuperados)} Conceptos", fg="green"))
    click.echo(click.style(f"  {', '.join(conceptos_recuperados)}", fg="green"))


cli.add_command(alimentar)
cli.add_command(eliminar_recuperar)
