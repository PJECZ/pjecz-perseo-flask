"""
CLI Cuentas

Toma el archivo EmpleadosAlfabetico.XLS

Necesita la quincena como argumento para saber donde buscar el archivo

"""
import os
import re
from pathlib import Path

import click
import xlrd
from dotenv import load_dotenv

from lib.safe_string import QUINCENA_REGEXP
from perseo.app import create_app
from perseo.blueprints.bancos.models import Banco
from perseo.blueprints.centros_trabajos.models import CentroTrabajo
from perseo.blueprints.conceptos.models import Concepto
from perseo.blueprints.conceptos_productos.models import ConceptoProducto
from perseo.blueprints.cuentas.models import Cuenta
from perseo.blueprints.nominas.models import Nomina
from perseo.blueprints.percepciones_deducciones.models import PercepcionDeduccion
from perseo.blueprints.personas.models import Persona
from perseo.blueprints.plazas.models import Plaza
from perseo.blueprints.productos.models import Producto
from perseo.extensions import database

EXPLOTACION_BASE_DIR = os.environ.get("EXPLOTACION_BASE_DIR")
CUENTAS_FILENAME_XLS = "EmpleadosAlfabetico.XLS"
MONEDEROS_FILENAME_XLS = "Monederos.XLS"

app = create_app()
app.app_context().push()
database.app = app


@click.group()
def cli():
    """Cuentas"""


@click.command()
@click.argument("quincena", type=str)
def alimentar_bancarias(quincena: str):
    """Alimentar cuentas bancarias"""

    # Iniciar sesion con la base de datos para que la alimentacion sea rapida
    sesion = database.session

    # Validar quincena
    if re.match(QUINCENA_REGEXP, quincena) is None:
        click.echo("Quincena inválida")
        return

    # Validar el directorio donde espera encontrar los archivos de explotacion
    if EXPLOTACION_BASE_DIR is None:
        click.echo("Variable de entorno EXPLOTACION_BASE_DIR no definida.")
        return

    # Validar si existe el archivo
    ruta = Path(EXPLOTACION_BASE_DIR, quincena, CUENTAS_FILENAME_XLS)
    if not ruta.exists():
        click.echo(f"AVISO: {str(ruta)} no se encontró.")
        return
    if not ruta.is_file():
        click.echo(f"AVISO: {str(ruta)} no es un archivo.")
        return

    # Abrir el archivo XLS con xlrd
    libro = xlrd.open_workbook(str(ruta))

    # Obtener la primera hoja
    hoja = libro.sheet_by_index(0)

    # Iniciar contador de cuentas alimentadas
    contador = 0

    # Bucle por cada fila
    click.echo("Alimentando cuentas...")
    for fila in range(1, hoja.nrows):
        # Tomar las columnas
        rfc = hoja.cell_value(fila, 0)
        bco_admdor = str(int(hoja.cell_value(fila, 23)))  # Tiene 5 y 10
        emp_cta_bancaria = str(int(hoja.cell_value(fila, 22)))

        # Revisar si el banco existe
        banco = Banco.query.filter_by(clave=bco_admdor).first()
        if banco is None:
            click.echo(f"  No existe el banco {bco_admdor}")
            continue

        # Revisar si la persona existe
        persona = Persona.query.filter_by(rfc=rfc).first()
        if persona is None:
            click.echo(f"  No existe la persona {rfc}")
            continue

        # Si esa persona ya tiene esa cuenta, se salta
        cuenta_existente = Cuenta.query.filter_by(persona_id=persona.id).filter_by(num_cuenta=emp_cta_bancaria).first()
        if cuenta_existente is not None:
            continue

        # Alimentar la cuenta
        cuenta = Cuenta(
            persona_id=persona.id,
            banco_id=banco.id,
            num_cuenta=emp_cta_bancaria,
        )
        sesion.add(cuenta)

        # Incrementar contador
        contador += 1
        if contador % 100 == 0:
            click.echo(f"  Van {contador}...")

    # Cerrar la sesion para que se guarden todos los datos en la base de datos
    sesion.commit()
    sesion.close()

    # Mensaje termino
    click.echo(f"Cuentas terminado: {contador} cuentas alimentados.")


@click.command()
@click.argument("quincena", type=str)
def alimentar_monederos(quincena: str):
    """Alimentar cuentas monederos"""

    # Iniciar sesion con la base de datos para que la alimentacion sea rapida
    sesion = database.session

    # Validar quincena
    if re.match(QUINCENA_REGEXP, quincena) is None:
        click.echo("Quincena inválida")
        return

    # Validar el directorio donde espera encontrar los archivos de explotacion
    if EXPLOTACION_BASE_DIR is None:
        click.echo("Variable de entorno EXPLOTACION_BASE_DIR no definida.")
        return

    # Validar si existe el archivo
    ruta = Path(EXPLOTACION_BASE_DIR, quincena, MONEDEROS_FILENAME_XLS)
    if not ruta.exists():
        click.echo(f"AVISO: {str(ruta)} no se encontró.")
        return
    if not ruta.is_file():
        click.echo(f"AVISO: {str(ruta)} no es un archivo.")
        return

    # Consultar el banco con clave 9 que es PREVIVALE
    banco = Banco.query.filter_by(clave="9").first()
    if banco is None:
        click.echo("ERROR: No existe el banco con clave 9")
        return

    # Abrir el archivo XLS con xlrd
    libro = xlrd.open_workbook(str(ruta))

    # Obtener la primera hoja
    hoja = libro.sheet_by_index(0)

    # Iniciar contador de monederos alimentadas
    contador = 0

    # Bucle por cada fila
    click.echo("Alimentando monederos...")
    for fila in range(1, hoja.nrows):
        # Tomar las columnas
        rfc = str(hoja.cell_value(fila, 1)).strip().upper()
        num_tarjeta = str(hoja.cell_value(fila, 4)).strip()

        # Validar que el num_tarjeta sea de 16 digitos, de lo contrarrio, se pone en 16 ceros
        if re.match(r"^\d{16}$", num_tarjeta) is None:
            num_tarjeta = "0" * 16

        # Revisar si la persona existe
        persona = Persona.query.filter_by(rfc=rfc).first()
        if persona is None:
            click.echo(f"  No existe la persona {rfc}")
            continue

        # Si esa persona ya tiene esa cuenta, se salta
        cuenta_existente = Cuenta.query.filter_by(persona_id=persona.id).filter_by(num_cuenta=num_tarjeta).first()
        if cuenta_existente is not None:
            continue

        # Alimentar la cuenta
        cuenta = Cuenta(
            persona_id=persona.id,
            banco_id=banco.id,
            num_cuenta=num_tarjeta,
        )
        sesion.add(cuenta)

        # Incrementar contador
        contador += 1
        if contador % 100 == 0:
            click.echo(f"  Van {contador}...")

    # Cerrar la sesion para que se guarden todos los datos en la base de datos
    sesion.commit()
    sesion.close()

    # Mensaje termino
    click.echo(f"Cuentas terminado: {contador} monederos alimentados.")


cli.add_command(alimentar_bancarias)
cli.add_command(alimentar_monederos)
