"""
CLI Beneficiarios
"""
import csv
from pathlib import Path

import click

from lib.safe_string import safe_rfc, safe_string
from perseo.app import create_app
from perseo.blueprints.bancos.models import Banco
from perseo.blueprints.beneficiarios.models import Beneficiario
from perseo.blueprints.beneficiarios_cuentas.models import BeneficiarioCuenta

BENEFICIARIOS_CSV = "seed/beneficiarios.csv"

app = create_app()
app.app_context().push()


@click.group()
def cli():
    """Beneficiarios"""


@click.command()
def alimentar():
    """Alimentar Beneficiarios"""
    ruta = Path(BENEFICIARIOS_CSV)
    if not ruta.exists():
        click.echo(f"AVISO: {ruta.name} no se encontró.")
        return
    if not ruta.is_file():
        click.echo(f"AVISO: {ruta.name} no es un archivo.")
        return
    click.echo("Alimentando beneficiarios...")
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

            # Agregar beneficiario
            beneficiario = Beneficiario(
                rfc=rfc,
                nombres=safe_string(row["NOMBRES"], save_enie=True),
                apellido_primero=safe_string(row["APELLIDO PRIMERO"], save_enie=True),
                apellido_segundo=safe_string(row["APELLIDO SEGUNDO"], save_enie=True),
                modelo=4,
            )
            beneficiario.save()

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
            beneficiario_cuenta.save()

            # Incrementar contador
            contador += 1
            if contador % 100 == 0:
                click.echo(f"  Van {contador}...")

    # Mensaje de termino
    click.echo(f"Beneficiarios terminado: {contador} beneficiarios alimentados.")


cli.add_command(alimentar)
