"""
CLI db
"""

import os
import sys

import click
from dotenv import load_dotenv

from cli.commands.alimentar_autoridades import alimentar_autoridades
from cli.commands.alimentar_distritos import alimentar_distritos
from cli.commands.alimentar_modulos import alimentar_modulos
from cli.commands.alimentar_permisos import alimentar_permisos
from cli.commands.alimentar_roles import alimentar_roles
from cli.commands.alimentar_usuarios import alimentar_usuarios
from cli.commands.alimentar_usuarios_roles import alimentar_usuarios_roles
from cli.commands.respaldar_autoridades import respaldar_autoridades
from cli.commands.respaldar_distritos import respaldar_distritos
from cli.commands.respaldar_modulos import respaldar_modulos
from cli.commands.respaldar_roles_permisos import respaldar_roles_permisos
from cli.commands.respaldar_usuarios_roles import respaldar_usuarios_roles
from perseo.app import create_app
from perseo.blueprints.autoridades.models import Autoridad
from perseo.blueprints.bitacoras.models import Bitacora
from perseo.blueprints.distritos.models import Distrito
from perseo.blueprints.entradas_salidas.models import EntradaSalida
from perseo.blueprints.modulos.models import Modulo
from perseo.blueprints.permisos.models import Permiso
from perseo.blueprints.roles.models import Rol
from perseo.blueprints.usuarios.models import Usuario
from perseo.blueprints.usuarios_roles.models import UsuarioRol
from perseo.extensions import database

app = create_app()
app.app_context().push()
database.app = app

load_dotenv()

ENTORNO_IMPLEMENTACION = os.getenv("ENTORNO_IMPLEMENTACION", "DEVELOPMENT")


@click.group()
def cli():
    """Base de Datos"""


@click.command()
def alimentar():
    """Alimentar"""
    if ENTORNO_IMPLEMENTACION == "PRODUCTION":
        click.echo("PROHIBIDO: No se alimenta porque este es el servidor de producción.")
        sys.exit(1)
    alimentar_modulos()
    alimentar_roles()
    alimentar_permisos()
    alimentar_distritos()
    alimentar_autoridades()
    alimentar_usuarios()
    alimentar_usuarios_roles()
    click.echo("Termina alimentar.")


@click.command()
def inicializar():
    """Inicializar"""
    if ENTORNO_IMPLEMENTACION == "PRODUCTION":
        click.echo("PROHIBIDO: No se inicializa porque este es el servidor de producción.")
        sys.exit(1)
    database.drop_all()
    database.create_all()
    click.echo("Termina inicializar.")


@click.command()
@click.pass_context
def reiniciar(ctx):
    """Reiniciar ejecuta inicializar y alimentar"""
    ctx.invoke(inicializar)
    ctx.invoke(alimentar)


@click.command()
@click.pass_context
def respaldar(ctx):
    """Respaldar crea archivos CSV en la carpeta seed"""
    respaldar_autoridades()
    respaldar_distritos()
    respaldar_modulos()
    respaldar_roles_permisos()
    respaldar_usuarios_roles()
    click.echo("Termina respaldar.")


cli.add_command(alimentar)
cli.add_command(inicializar)
cli.add_command(reiniciar)
cli.add_command(respaldar)
