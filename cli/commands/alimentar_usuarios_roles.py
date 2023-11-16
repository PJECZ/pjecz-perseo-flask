"""
Alimentar usuarios-roles
"""
import csv
import sys
from pathlib import Path

import click

from lib.safe_string import safe_string
from perseo.blueprints.roles.models import Rol
from perseo.blueprints.usuarios.models import Usuario
from perseo.blueprints.usuarios_roles.models import UsuarioRol

USUARIOS_ROLES_CSV = "seed/usuarios_roles.csv"


def alimentar_usuarios_roles():
    """Alimentar usuarios-roles"""
    ruta = Path(USUARIOS_ROLES_CSV)
    if not ruta.exists():
        click.echo(f"ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        click.echo(f"ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)
    if Usuario.query.count() == 0:
        click.echo("ERROR: Faltan de alimentar los usuarios")
        sys.exit(1)
    click.echo("Alimentando usuarios-roles...")
    contador = 0
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            usuario_id = int(row["usuario_id"])
            usuario = Usuario.query.get(usuario_id)
            if usuario is None:
                click.echo(f"  ERROR: Falta el usuario_id {usuario_id}")
                sys.exit(1)
            for rol_str in row["roles"].split(","):
                rol_str = rol_str.strip().upper()
                if rol_str == "":
                    click.echo(f"  AVISO: El usuario {usuario.email} no tiene roles.")
                    continue
                rol = Rol.query.filter_by(nombre=rol_str).first()
                if rol is None:
                    click.echo(f"  AVISO: Falta el rol {rol_str}")
                    continue
                UsuarioRol(
                    usuario=usuario,
                    rol=rol,
                    descripcion=safe_string(f"{usuario.email} en {rol.nombre}", save_enie=True, to_uppercase=False),
                ).save()
                contador += 1
                if contador % 100 == 0:
                    click.echo(f"  Van {contador}...")
    click.echo(f"  {contador} usuarios-roles alimentados.")
