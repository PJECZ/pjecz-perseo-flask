"""
Alimentar roles
"""
import csv
import sys
from pathlib import Path

import click

from lib.safe_string import safe_string
from perseo.blueprints.roles.models import Rol

ROLES_CSV = "seed/roles_permisos.csv"


def alimentar_roles():
    """Alimentar roles"""
    ruta = Path(ROLES_CSV)
    if not ruta.exists():
        click.echo(f"ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        click.echo(f"ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)
    click.echo("Alimentando roles...")
    contador = 0
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            rol_id = int(row["rol_id"])
            if rol_id != contador + 1:
                click.echo(f"  AVISO: rol_id {rol_id} no es consecutivo")
                continue
            Rol(
                nombre=safe_string(row["nombre"], to_uppercase=False, save_enie=True),
                estatus=row["estatus"],
            ).save()
            contador += 1
            if contador % 100 == 0:
                click.echo(f"  Van {contador}...")
    click.echo(f"  {contador} roles alimentados.")
