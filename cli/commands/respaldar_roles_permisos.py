"""
Respaldar Roles-Permisos
"""
import csv
from pathlib import Path

import click

from perseo.blueprints.modulos.models import Modulo
from perseo.blueprints.roles.models import Rol

ROLES_PERMISOS_CSV = "seed/roles_permisos.csv"


def respaldar_roles_permisos():
    """Respaldar Roles-Permisos a un archivo CSV"""
    directorio = Path("seed")
    directorio.mkdir(exist_ok=True)
    ruta = Path(ROLES_PERMISOS_CSV)
    if ruta.exists():
        ruta.unlink()
    click.echo("Respaldando roles...")
    contador = 0
    roles = Rol.query.order_by(Rol.id).all()
    modulos = Modulo.query.order_by(Modulo.id).all()
    with open(ruta, "w", encoding="utf8") as puntero:
        encabezados = [
            "rol_id",
            "nombre",
        ]
        for modulo in modulos:
            encabezados.append(modulo.nombre.lower())
        encabezados.append("estatus")
        respaldo = csv.writer(puntero)
        respaldo.writerow(encabezados)
        for rol in roles:
            renglon = [rol.id, rol.nombre]
            for modulo in modulos:
                permiso_str = ""
                for permiso in rol.permisos:
                    if permiso.modulo_id == modulo.id and permiso.estatus == "A":
                        permiso_str = str(permiso.nivel)
                renglon.append(permiso_str)
            renglon.append(rol.estatus)
            respaldo.writerow(renglon)
            contador += 1
            if contador % 100 == 0:
                click.echo(f"  Van {contador}...")
    click.echo(f"  {contador} en {ruta.name}")
