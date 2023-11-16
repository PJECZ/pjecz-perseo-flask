"""
Alimentar autoriades
"""
import csv
import sys
from pathlib import Path

import click

from lib.safe_string import safe_clave, safe_string
from perseo.blueprints.autoridades.models import Autoridad
from perseo.blueprints.distritos.models import Distrito

AUTORIDADES_CSV = "seed/autoridades.csv"


def alimentar_autoridades():
    """Alimentar autoridades"""
    ruta = Path(AUTORIDADES_CSV)
    if not ruta.exists():
        click.echo(f"ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        click.echo(f"ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)
    click.echo("Alimentando autoridades...")
    contador = 0
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            distrito_id = int(row["distrito_id"])
            distrito = Distrito.query.get(distrito_id)
            if distrito is None:
                click.echo(f"  AVISO: Falta el distrito {distrito_id}")
                continue
            autoridad_id = int(row["autoridad_id"])
            if autoridad_id != contador + 1:
                click.echo(f"  AVISO: autoridad_id {autoridad_id} no es consecutivo")
                continue
            Autoridad(
                distrito=distrito,
                clave=safe_clave(row["clave"]),
                descripcion=safe_string(row["descripcion"], save_enie=True),
                descripcion_corta=safe_string(row["descripcion_corta"], save_enie=True),
                es_extinto=False,
                estatus=row["estatus"],
            ).save()
            contador += 1
            if contador % 100 == 0:
                click.echo(f"  Van {contador}...")
    click.echo(f"  {contador} autoridades alimentadas.")
