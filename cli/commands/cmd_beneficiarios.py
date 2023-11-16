"""
CLI Beneficiarios
"""
import csv
import re
import sys
from pathlib import Path

import click

from lib.safe_string import QUINCENA_REGEXP, safe_string
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
def alimentar(quincena_clave: str):
    """Alimentar Beneficiarios"""

    # Validar quincena
    if re.match(QUINCENA_REGEXP, quincena_clave) is None:
        click.echo("ERROR: Quincena inválida.")
        sys.exit(1)

    # Validar archivo
    ruta = Path(BENEFICIARIOS_CSV)
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

    # Leer el archivo CSV
    click.echo("Alimentando Beneficiarios...")
    contador = 0
    with open(ruta, newline="", encoding="utf8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Validar RFC
            try:
                rfc = safe_string(row["RFC"])  # TODO: Debe ser safe_rfc
            except ValueError as error:
                click.echo(str(error))
                continue

            # Revistar si ya existe el beneficiario
            beneficiario = Beneficiario.query.filter_by(rfc=rfc).first()
            if beneficiario is None:
                # Agregar beneficiario
                beneficiario = Beneficiario(
                    rfc=rfc,
                    nombres=safe_string(row["NOMBRES"], save_enie=True),
                    apellido_primero=safe_string(row["APELLIDO PRIMERO"], save_enie=True),
                    apellido_segundo=safe_string(row["APELLIDO SEGUNDO"], save_enie=True),
                    modelo=4,
                )
                sesion.add(beneficiario)
            else:
                # Si cambio nombres, apellido_primero o apellido_segundo, se actualizan
                if (
                    beneficiario.nombres != safe_string(row["NOMBRES"], save_enie=True)
                    or beneficiario.apellido_primero != safe_string(row["APELLIDO PRIMERO"], save_enie=True)
                    or beneficiario.apellido_segundo != safe_string(row["APELLIDO SEGUNDO"], save_enie=True)
                ):
                    beneficiario.nombres = safe_string(row["NOMBRES"], save_enie=True)
                    beneficiario.apellido_primero = safe_string(row["APELLIDO PRIMERO"], save_enie=True)
                    beneficiario.apellido_segundo = safe_string(row["APELLIDO SEGUNDO"], save_enie=True)
                    sesion.add(beneficiario)

            # Consultar banco
            banco = Banco.query.filter_by(clave=row["BANCO"]).first()
            if banco is None:
                click.echo(f"AVISO: Clave de banco {row['BANCO']} no se encontró.")
                continue

            # Agregar cuenta al beneficiario
            beneficiario_cuenta = BeneficiarioCuenta(
                beneficiario=beneficiario,
                banco=banco,
                num_cuenta=safe_string(row["NUM CUENTA"]),
            )
            sesion.add(beneficiario_cuenta)

            # Incrementer el consecutivo_generado del banco
            # banco.consecutivo_generado += 1
            # sesion.add(banco)

            # Elaborar el numero de cheque, juntando la clave del banco y el consecutivo, siempre de 9 digitos
            # num_cheque = f"{banco.clave.zfill(2)}{banco.consecutivo_generado:07}"

            # Agregar quincena al beneficiario
            beneficiario_quincena = BeneficiarioQuincena(
                beneficiario=beneficiario,
                quincena=quincena,
                importe=row["IMPORTE"],
            )
            sesion.add(beneficiario_quincena)

            # Incrementar contador
            contador += 1
            if contador % 100 == 0:
                click.echo(f"  Van {contador}...")

    # Cerrar la sesion para que se guarden todos los datos en la base de datos
    sesion.commit()
    sesion.close()

    # Mensaje de termino
    click.echo(f"Beneficiarios terminado: {contador} beneficiarios alimentados.")


cli.add_command(alimentar)
