"""
CLI Beneficiarios
"""
import csv
import re
import sys
from pathlib import Path

import click

from lib.safe_string import QUINCENA_REGEXP, safe_rfc, safe_string
from perseo.app import create_app
from perseo.blueprints.bancos.models import Banco
from perseo.blueprints.beneficiarios.models import Beneficiario
from perseo.blueprints.beneficiarios_cuentas.models import BeneficiarioCuenta
from perseo.blueprints.beneficiarios_quincenas.models import BeneficiarioQuincena
from perseo.blueprints.quincenas.models import Quincena
from perseo.extensions import database

BENEFICIARIOS_CSV = "seed/beneficiarios.csv"

app = create_app()
app.app_context().push()
database.app = app


@click.group()
def cli():
    """Beneficiarios"""


@click.command()
@click.argument("quincena_clave", type=str)
@click.option("--beneficiarios-csv", default=BENEFICIARIOS_CSV, help="Archivo CSV con los datos de los Beneficiarios")
def alimentar(quincena_clave: str, beneficiarios_csv: str):
    """Alimentar Beneficiarios"""

    # Validar quincena
    if re.match(QUINCENA_REGEXP, quincena_clave) is None:
        click.echo("ERROR: Quincena inválida.")
        sys.exit(1)

    # Validar archivo
    ruta = Path(beneficiarios_csv)
    if not ruta.exists():
        click.echo(f"ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        click.echo(f"ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)

    # Iniciar sesion con la base de datos para que la alimentacion sea rapida
    sesion = database.session

    # Consultar quincena
    quincena = Quincena.query.filter_by(clave=quincena_clave).first()

    # Si existe la quincena, pero no esta ABIERTA, entonces se termina
    if quincena and quincena.estado != "ABIERTA":
        click.echo(f"ERROR: Quincena {quincena_clave} no esta ABIERTA.")
        sys.exit(1)

    # Si existe la quincena, pero ha sido eliminada, entonces se termina
    if quincena and quincena.estatus != "A":
        click.echo(f"ERROR: Quincena {quincena_clave} ha sido eliminada.")
        sys.exit(1)

    # Si no existe la quincena, se agrega
    if quincena is None:
        quincena = Quincena(clave=quincena_clave, estado="ABIERTA")
        sesion.add(quincena)
        sesion.commit()

    # Inicializar contadores y mensajes
    contador_beneficiarios_insertados = 0
    contador_beneficiarios_actualizados = 0
    contador_quincenas_insertadas = 0
    personas_errores = []
    bancos_errores = []

    # Leer el archivo CSV
    click.echo("Alimentando Beneficiarios: ", nl=False)
    with open(ruta, newline="", encoding="utf8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Validar RFC
            try:
                rfc = safe_rfc(row["RFC"])
            except ValueError as error:
                personas_errores.append(f"{row['RFC']}: {error}")
                continue

            # Revistar si ya existe el beneficiario
            beneficiario = Beneficiario.query.filter_by(rfc=rfc).first()

            # Si no existe, se agrega
            if beneficiario is None:
                beneficiario = Beneficiario(
                    rfc=rfc,
                    nombres=safe_string(row["NOMBRES"], save_enie=True),
                    apellido_primero=safe_string(row["APELLIDO PRIMERO"], save_enie=True),
                    apellido_segundo=safe_string(row["APELLIDO SEGUNDO"], save_enie=True),
                    modelo=4,
                )
                sesion.add(beneficiario)
                contador_beneficiarios_insertados += 1
                click.echo(".", nl=False)
            else:
                # Si cambio nombres, apellido_primero o apellido_segundo, se actualiza
                if (
                    beneficiario.nombres != safe_string(row["NOMBRES"], save_enie=True)
                    or beneficiario.apellido_primero != safe_string(row["APELLIDO PRIMERO"], save_enie=True)
                    or beneficiario.apellido_segundo != safe_string(row["APELLIDO SEGUNDO"], save_enie=True)
                ):
                    beneficiario.nombres = safe_string(row["NOMBRES"], save_enie=True)
                    beneficiario.apellido_primero = safe_string(row["APELLIDO PRIMERO"], save_enie=True)
                    beneficiario.apellido_segundo = safe_string(row["APELLIDO SEGUNDO"], save_enie=True)
                    sesion.add(beneficiario)
                    contador_beneficiarios_actualizados += 1
                    click.echo("u", nl=False)

            # Consultar banco
            banco = Banco.query.filter_by(clave=row["BANCO"]).first()
            if banco is None:
                bancos_errores.append(f"{row['BANCO']}: No existe")
                continue

            # Agregar cuenta al beneficiario
            beneficiario_cuenta = BeneficiarioCuenta(
                beneficiario=beneficiario,
                banco=banco,
                num_cuenta=safe_string(row["NUM CUENTA"]),
            )
            sesion.add(beneficiario_cuenta)

            # Agregar quincena al beneficiario
            beneficiario_quincena = BeneficiarioQuincena(
                beneficiario=beneficiario,
                quincena=quincena,
                importe=row["IMPORTE"],
            )
            sesion.add(beneficiario_quincena)

            # Incrementar contador
            contador_quincenas_insertadas += 1
            click.echo(click.style(".", fg="cyan"), nl=False)

    # Poner avance de linea
    click.echo("")

    # Cerrar la sesion para que se guarden todos los datos en la base de datos
    sesion.commit()
    sesion.close()

    # Si hubo personas_errores, mostrarlos
    if len(personas_errores) > 0:
        click.echo(click.style(f"  Hubo {len(personas_errores)} errores:", fg="red"))
        click.echo(click.style(f"  {', '.join(personas_errores)}", fg="red"))

    # Si hubo bancos_errores, mostrarlos
    if len(bancos_errores) > 0:
        click.echo(click.style(f"  Hubo {len(bancos_errores)} errores:", fg="red"))
        click.echo(click.style(f"  {', '.join(bancos_errores)}", fg="red"))

    # Si hubo beneficiarios insertados, se muestra la cantidad
    if contador_beneficiarios_insertados > 0:
        click.echo(click.style(f"  Beneficiarios: {contador_beneficiarios_insertados} insertados.", fg="green"))

    # Si hubo beneficiarios actualizados, se muestra la cantidad
    if contador_beneficiarios_actualizados > 0:
        click.echo(click.style(f"  Beneficiarios: {contador_beneficiarios_actualizados} actualizados.", fg="green"))

    # Mensaje de termino
    click.echo(click.style(f"  Beneficiarios: {contador_quincenas_insertadas} quincenas insertadas.", fg="green"))


cli.add_command(alimentar)
