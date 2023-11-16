"""
Alimentar usuarios
"""
import csv
import sys
from datetime import datetime
from pathlib import Path

import click

from lib.pwgen import generar_contrasena
from lib.safe_string import safe_string
from perseo.blueprints.autoridades.models import Autoridad
from perseo.blueprints.usuarios.models import Usuario
from perseo.extensions import pwd_context

USUARIOS_CSV = "seed/usuarios_roles.csv"


def alimentar_usuarios():
    """Alimentar usuarios"""
    ruta = Path(USUARIOS_CSV)
    if not ruta.exists():
        click.echo(f"ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        click.echo(f"ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)
    click.echo("Alimentando usuarios...")
    contador = 0
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            # Validar autoridad
            if "autoridad_clave" in row:
                autoridad_clave = row["autoridad_clave"]
                autoridad = Autoridad.query.filter_by(clave=autoridad_clave).first()
                if autoridad is None:
                    click.echo(f"  AVISO: Falta la autoridad_clave {autoridad_clave}")
                    continue
            elif "autoridad_id" in row:
                autoridad_id = row["autoridad_id"]
                autoridad = Autoridad.query.get(autoridad_id)
                if autoridad is None:
                    click.echo(f"  AVISO: Falta la autoridad_id {autoridad_id}")
                    continue
            else:
                click.echo("ERROR: No tiene la columna autoridad_clave o autoridad_id")
                sys.exit(1)

            # Validar consecutivo
            usuario_id = int(row["usuario_id"])
            if usuario_id != contador + 1:
                click.echo(f"  AVISO: usuario_id {usuario_id} no es consecutivo")
                continue

            # Insertar
            Usuario(
                autoridad=autoridad,
                email=row["email"],
                nombres=safe_string(row["nombres"], save_enie=True),
                apellido_primero=safe_string(row["apellido_primero"], save_enie=True),
                apellido_segundo=safe_string(row["apellido_segundo"], save_enie=True),
                curp=safe_string(row["curp"]),
                puesto=safe_string(row["puesto"], save_enie=True),
                api_key="",
                api_key_expiracion=datetime(year=2000, month=1, day=1),
                contrasena=pwd_context.hash(generar_contrasena()),
                estatus=row["estatus"],
            ).save()
            contador += 1
            if contador % 100 == 0:
                click.echo(f"  Van {contador}...")
    click.echo(f"  {contador} usuarios alimentados con contraseñas aleatorias.")
