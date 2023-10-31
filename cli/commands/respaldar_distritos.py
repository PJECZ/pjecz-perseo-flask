"""
Respaldar Distritos
"""
import csv
from pathlib import Path

import click

from perseo.blueprints.distritos.models import Distrito

DISTRITOS_CSV = "seed/distritos.csv"


def respaldar_distritos():
    """Respaldar Distritos a un archivo CSV"""
    directorio = Path("seed")
    directorio.mkdir(exist_ok=True)
    ruta = Path(DISTRITOS_CSV)
    if ruta.exists():
        ruta.unlink()
    click.echo("Respaldando distritos...")
    contador = 0
    distritos = Distrito.query.order_by(Distrito.id).all()
    with open(ruta, "w", encoding="utf8") as puntero:
        respaldo = csv.writer(puntero)
        respaldo.writerow(
            [
                "distrito_id",
                "clave",
                "nombre",
                "nombre_corto",
                "es_distrito",
                "es_jurisdiccional",
                "estatus",
            ]
        )
        for distrito in distritos:
            respaldo.writerow(
                [
                    distrito.id,
                    distrito.clave,
                    distrito.nombre,
                    distrito.nombre_corto,
                    int(distrito.es_distrito),
                    int(distrito.es_jurisdiccional),
                    distrito.estatus,
                ]
            )
            contador += 1
            if contador % 100 == 0:
                click.echo(f"  Van {contador}...")
    click.echo(f"  {contador} en {ruta.name}")
