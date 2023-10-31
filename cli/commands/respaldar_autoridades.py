"""
Respaldar Autoridades
"""
import csv
from pathlib import Path

import click

from perseo.blueprints.autoridades.models import Autoridad

AUTORIDADES_CSV = "seed/autoridades.csv"


def respaldar_autoridades():
    """Respaldar Autoridades a un archivo CSV"""
    directorio = Path("seed")
    directorio.mkdir(exist_ok=True)
    ruta = Path(AUTORIDADES_CSV)
    if ruta.exists():
        ruta.unlink()
    click.echo("Respaldando autoridades...")
    contador = 0
    autoridades = Autoridad.query.order_by(Autoridad.id).all()
    with open(ruta, "w", encoding="utf8") as puntero:
        respaldo = csv.writer(puntero)
        respaldo.writerow(
            [
                "autoridad_id",
                "distrito_id",
                "clave",
                "descripcion",
                "descripcion_corta",
                "es_extinto",
                "estatus",
            ]
        )
        for autoridad in autoridades:
            respaldo.writerow(
                [
                    autoridad.id,
                    autoridad.distrito_id,
                    autoridad.clave,
                    autoridad.descripcion,
                    autoridad.descripcion_corta,
                    int(autoridad.es_extinto),
                    autoridad.estatus,
                ]
            )
            contador += 1
            if contador % 100 == 0:
                click.echo(f"  Van {contador}...")
    click.echo(f"  {contador} en {ruta.name}")
