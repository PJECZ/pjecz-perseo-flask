"""
Alimentar módulos
"""
import csv
import sys
from pathlib import Path

import click

from lib.safe_string import safe_string
from perseo.blueprints.modulos.models import Modulo

MODULOS_CSV = "seed/modulos.csv"


def alimentar_modulos():
    """Alimentar modulos"""
    ruta = Path(MODULOS_CSV)
    if not ruta.exists():
        click.echo(f"ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        click.echo(f"ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)
    click.echo("Alimentando módulos...")
    contador = 0
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            modulo_id = int(row["modulo_id"])
            if modulo_id != contador + 1:
                click.echo(f"  AVISO: modulo_id {modulo_id} no es consecutivo")
                continue
            Modulo(
                nombre=safe_string(row["nombre"], save_enie=True),
                nombre_corto=safe_string(row["nombre_corto"], save_enie=True, to_uppercase=False),
                icono=row["icono"],
                ruta=row["ruta"],
                en_navegacion=row["en_navegacion"] == "1",
                estatus=row["estatus"],
            ).save()
            contador += 1
            if contador % 100 == 0:
                click.echo(f"  Van {contador}...")
    click.echo(f"  {contador} módulos alimentados.")
