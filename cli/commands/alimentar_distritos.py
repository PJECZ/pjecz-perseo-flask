"""
Alimentar distritos
"""
import csv
import sys
from pathlib import Path

import click

from lib.safe_string import safe_clave, safe_string
from perseo.blueprints.distritos.models import Distrito

DISTRITOS_CSV = "seed/distritos.csv"


def alimentar_distritos():
    """Alimentar distritos"""
    ruta = Path(DISTRITOS_CSV)
    if not ruta.exists():
        click.echo(f"ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        click.echo(f"ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)
    click.echo("Alimentando distritos...")
    contador = 0
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            distrito_id = int(row["distrito_id"])
            if distrito_id != contador + 1:
                click.echo(f"  AVISO: distrito_id {distrito_id} no es consecutivo")
                continue
            Distrito(
                clave=safe_clave(row["clave"]),
                nombre=safe_string(row["nombre"], save_enie=True),
                nombre_corto=safe_string(row["nombre_corto"], save_enie=True),
                es_distrito=(row["es_distrito"] == "1"),
                es_jurisdiccional=(row["es_jurisdiccional"] == "1"),
                estatus=row["estatus"],
            ).save()
            contador += 1
            if contador % 100 == 0:
                click.echo(f"  Van {contador}...")
    click.echo(f"  {contador} distritos alimentados.")
