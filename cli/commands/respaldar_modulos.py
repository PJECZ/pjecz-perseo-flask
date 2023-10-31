"""
Respaldar Modulos
"""
import csv
from pathlib import Path

import click

from perseo.blueprints.modulos.models import Modulo

MODULOS_CSV = "seed/modulos.csv"


def respaldar_modulos():
    """Respaldar Modulos a un archivo CSV"""
    directorio = Path("seed")
    directorio.mkdir(exist_ok=True)
    ruta = Path(MODULOS_CSV)
    if ruta.exists():
        ruta.unlink()
    click.echo("Respaldando módulos...")
    contador = 0
    modulos = Modulo.query.order_by(Modulo.id).all()
    with open(ruta, "w", encoding="utf8") as puntero:
        respaldo = csv.writer(puntero)
        respaldo.writerow(
            [
                "modulo_id",
                "nombre",
                "nombre_corto",
                "icono",
                "ruta",
                "en_navegacion",
                "estatus",
            ]
        )
        for modulo in modulos:
            respaldo.writerow(
                [
                    modulo.id,
                    modulo.nombre,
                    modulo.nombre_corto,
                    modulo.icono,
                    modulo.ruta,
                    int(modulo.en_navegacion),
                    modulo.estatus,
                ]
            )
            contador += 1
            if contador % 100 == 0:
                click.echo(f"  Van {contador}...")
    click.echo(f"  {contador} en {ruta.name}")
