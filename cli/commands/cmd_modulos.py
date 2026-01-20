"""
CLI Modulos
"""

import csv
import sys
from pathlib import Path

import click

from pjecz_perseo_flask.blueprints.modulos.models import Modulo
from pjecz_perseo_flask.main import app

MODULOS_CSV = "seed/modulos.csv"

# Inicializar el contexto de la aplicación Flask
app.app_context().push()


@click.group()
def cli():
    """Bancos"""


@click.command()
def actualizar():
    """Actualizar los módulos leyendo el archivo CSV y guardando los cambios si los hay"""
    modulos_csv = Path(MODULOS_CSV)
    if not modulos_csv.exists():
        click.echo(f"ERROR: {modulos_csv.name} no se encontró.")
        sys.exit(1)
    if not modulos_csv.is_file():
        click.echo(f"ERROR: {modulos_csv.name} no es un archivo.")
        sys.exit(1)
    click.echo("Actualizando módulos...")
    contador = 0
    with open(modulos_csv, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            modulo_id = int(row["modulo_id"])
            nombre = row["nombre"]
            nombre_corto = row["nombre_corto"]
            icono = row["icono"]
            ruta = row["ruta"]
            en_navegacion = row["en_navegacion"] == "1"  # 0 o 1
            estatus = row["estatus"]  # 'A' o 'B'
            # Consultar el módulo por su ID
            modulo = Modulo.query.filter_by(id=modulo_id).first()
            if modulo:
                hay_cambios = False
                if modulo.nombre != nombre:
                    modulo.nombre = nombre
                    hay_cambios = True
                if modulo.nombre_corto != nombre_corto:
                    modulo.nombre_corto = nombre_corto
                    hay_cambios = True
                if modulo.icono != icono:
                    modulo.icono = icono
                    hay_cambios = True
                if modulo.ruta != ruta:
                    modulo.ruta = ruta
                    hay_cambios = True
                if modulo.en_navegacion != en_navegacion:
                    modulo.en_navegacion = en_navegacion
                    hay_cambios = True
                if modulo.estatus != estatus:
                    modulo.estatus = estatus
                    hay_cambios = True
                if hay_cambios:
                    modulo.save()
                    contador += 1
                    click.echo(f"  Módulo {nombre} actualizado.")
    click.echo(f"  {contador} módulos actualizados.")


cli.add_command(actualizar)
