"""
CLI db
"""
import os
import click

from dotenv import load_dotenv

from cli.commands.alimentar_autoridades import alimentar_autoridades
from cli.commands.alimentar_distritos import alimentar_distritos
from cli.commands.alimentar_modulos import alimentar_modulos
from cli.commands.alimentar_permisos import alimentar_permisos
from cli.commands.alimentar_roles import alimentar_roles
from cli.commands.alimentar_usuarios import alimentar_usuarios
from cli.commands.alimentar_usuarios_roles import alimentar_usuarios_roles

from perseo.app import create_app
from perseo.extensions import database

from perseo.blueprints.autoridades.models import Autoridad
from perseo.blueprints.distritos.models import Distrito
from perseo.blueprints.bitacoras.models import Bitacora
from perseo.blueprints.entradas_salidas.models import EntradaSalida
from perseo.blueprints.modulos.models import Modulo
from perseo.blueprints.permisos.models import Permiso
from perseo.blueprints.roles.models import Rol
from perseo.blueprints.usuarios.models import Usuario
from perseo.blueprints.usuarios_roles.models import UsuarioRol

app = create_app()
app.app_context().push()
database.app = app

load_dotenv()
ENTORNO_IMPLEMENTACION = os.getenv("ENTORNO_IMPLEMENTACION")


@click.group()
def cli():
    """Base de Datos"""


@click.command()
def alimentar():
    """Alimentar"""
    if ENTORNO_IMPLEMENTACION == "PRODUCTION":
        click.echo("PROHIBIDO: No se alimenta porque este es el servidor de producción.")
        return
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
        return
    database.drop_all()
    database.create_all()
    click.echo("Termina inicializar.")


cli.add_command(alimentar)
cli.add_command(inicializar)
