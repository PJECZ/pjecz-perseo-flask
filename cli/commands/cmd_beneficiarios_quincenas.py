"""
CLI Beneficiarios Quincenas
"""

import re
import sys
from datetime import datetime

import click
from openpyxl import Workbook

from pjecz_perseo_flask.blueprints.bancos.models import Banco
from pjecz_perseo_flask.blueprints.beneficiarios.models import Beneficiario
from pjecz_perseo_flask.blueprints.beneficiarios_cuentas.models import BeneficiarioCuenta
from pjecz_perseo_flask.blueprints.beneficiarios_quincenas.models import BeneficiarioQuincena
from pjecz_perseo_flask.blueprints.quincenas.models import Quincena
from pjecz_perseo_flask.config.extensions import database
from pjecz_perseo_flask.lib.safe_string import QUINCENA_REGEXP
from pjecz_perseo_flask.main import app

# Inicializar el contexto de la aplicación Flask
app.app_context().push()


@click.group()
def cli():
    """Beneficiarios Quincenas"""


@click.command()
@click.argument("quincena_clave", type=str)
def generar(quincena_clave: str):
    """Generar archivo XLSX con los numeros de cheque para los beneficiarios de una quincena"""

    # Validar quincena
    if re.match(QUINCENA_REGEXP, quincena_clave) is None:
        click.echo("ERROR: Quincena inválida.")
        sys.exit(1)

    # Iniciar sesion con la base de datos para que la alimentacion sea rapida
    sesion = database.session

    # Consultar quincena
    quincena = Quincena.query.filter_by(clave=quincena_clave).first()

    # Si no existe la quincena, entonces se termina
    if quincena is None:
        click.echo(f"ERROR: Quincena {quincena_clave} no existe.")
        sys.exit(1)

    # Si existe la quincena, pero no esta ABIERTA, entonces se termina
    if quincena.estado != "ABIERTA":
        click.echo(f"ERROR: Quincena {quincena_clave} no esta ABIERTA.")
        sys.exit(1)

    # Si existe la quincena, pero ha sido eliminada, entonces se termina
    if quincena.estatus != "A":
        click.echo(f"ERROR: Quincena {quincena_clave} esta eliminada.")
        sys.exit(1)

    # Consultar las quincenas de los beneficiarios activos
    beneficiarios_quincenas = BeneficiarioQuincena.query.filter_by(quincena_id=quincena.id).filter_by(estatus="A").all()

    # TODO: Si no hay quincenas de los beneficiarios, tomamos la quincena anterior para agregar nuevos registros

    # Iniciar el archivo XLSX
    libro = Workbook()

    # Tomar la hoja del libro XLSX
    hoja = libro.active
    if hoja is None:
        click.echo("ERROR: No se pudo crear la hoja del archivo XLSX.")
        sys.exit(1)

    # Agregar la fila con las cabeceras de las columnas
    hoja.append(
        [
            "QUINCENA",
            "CT CLASIF",
            "RFC",
            "NOMBRE DEL BENEFICIARIO",
            "NUM EMPLEADO",
            "MODELO",
            "PLAZA",
            "NOMBRE DEL BANCO",
            "CLAVE DEL BANCO",
            "NUMERO DE CUENTA",
            "MONTO TOTAL",
            "NO DE CHEQUE",
        ]
    )

    # Bucle para crear cada fila del archivo XLSX
    contador = 0
    contador = 0
    personas_sin_cuentas = []
    for bq in beneficiarios_quincenas:
        # Si el modelo de la persona NO es 4, se omite
        if bq.persona.modelo != 4:
            continue

        # Tomar las cuentas de la persona
        cuentas = bq.persona.cuentas

        # Si no tiene cuentas, entonces se agrega a la lista de personas_sin_cuentas y se salta
        if len(cuentas) == 0:
            personas_sin_cuentas.append(bq.persona.rfc)
            continue

        # Tomar la cuenta de la persona que no tenga la clave 9, porque esa clave es la de DESPENSA
        su_cuenta = None
        for cuenta in cuentas:
            if cuenta.banco.clave != "9" and cuenta.estatus == "A":
                su_cuenta = cuenta
                break

        # Si no tiene cuenta bancaria, entonces se agrega a la lista de personas_sin_cuentas y se salta
        if su_cuenta is None:
            personas_sin_cuentas.append(bq.persona.rfc)
            continue

        # Tomar el banco de la cuenta de la persona
        su_banco = su_cuenta.banco

        # Incrementer el consecutivo_generado del banco
        su_banco.consecutivo_generado += 1

        # Elaborar el numero de cheque, juntando la clave del banco y la consecutivo, siempre de 9 digitos
        num_cheque = f"{su_cuenta.banco.clave.zfill(2)}{su_banco.consecutivo_generado:07}"

        # Agregar la fila
        hoja.append(
            [
                bq.quincena.clave,
                "NO SE CT CLASIF",
                bq.beneficiario.rfc,
                bq.beneficiario.nombre_completo,
                "NO TIENE NO DE EMP",
                "NO TIENE MODELO",
                "NO TIENE PLAZA",
                su_banco.nombre,
                su_banco.clave,
                su_cuenta.num_cuenta,
                bq.importe,
                num_cheque,
            ]
        )

        # Incrementar contador
        contador += 1
        if contador % 100 == 0:
            click.echo(f"  Van {contador}...")

    # Actualizar los consecutivos de cada banco
    sesion.commit()

    # Determinar el nombre del archivo XLSX
    nombre_archivo = f"beneficiarios_{quincena_clave}_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.xlsx"

    # Guardar el archivo XLSX
    libro.save(nombre_archivo)

    # Si hubo personas sin cuentas, se muestran
    if len(personas_sin_cuentas) > 0:
        click.echo(click.style(f"  Hubo {len(personas_sin_cuentas)} Personas sin cuentas:", fg="yellow"))
        click.echo(click.style(f"  {', '.join(personas_sin_cuentas)}", fg="yellow"))

    # Mensaje termino
    click.echo(f"  Generar Beneficiarios Quincenas: {contador} filas en {nombre_archivo}")


cli.add_command(generar)
