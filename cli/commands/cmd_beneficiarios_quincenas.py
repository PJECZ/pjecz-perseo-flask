"""
CLI Beneficiarios Quincenas
"""
import csv
import re
from datetime import datetime
from pathlib import Path

import click
import xlrd
from dotenv import load_dotenv
from openpyxl import Workbook

from lib.safe_string import QUINCENA_REGEXP, safe_string
from perseo.app import create_app
from perseo.blueprints.bancos.models import Banco
from perseo.blueprints.beneficiarios.models import Beneficiario
from perseo.blueprints.beneficiarios_cuentas.models import BeneficiarioCuenta
from perseo.blueprints.beneficiarios_quincenas.models import BeneficiarioQuincena
from perseo.blueprints.quincenas.models import Quincena
from perseo.extensions import database

app = create_app()
app.app_context().push()
database.app = app


@click.group()
def cli():
    """Beneficiarios Quincenas"""


@click.command()
@click.argument("quincena_clave", type=str)
def generar(quincena_clave: str):
    """Generar archivo XLSX con los numeros de cheque para los beneficiarios de una quincena"""

    # Validar quincena
    if re.match(QUINCENA_REGEXP, quincena_clave) is None:
        click.echo("Quincena inválida.")
        return

    # Iniciar sesion con la base de datos para que la alimentacion sea rapida
    sesion = database.session

    # Consultar quincena
    quincena = Quincena.query.filter_by(clave=quincena_clave).first()

    # Si no existe la quincena, entonces se termina
    if quincena is None:
        click.echo("Quincena no existe.")
        return

    # Si existe la quincena, pero no esta ABIERTA, entonces se termina
    if quincena.estado != "ABIERTA":
        click.echo("Quincena no esta ABIERTA.")
        return

    # Si existe la quincena, pero ha sido eliminada, entonces se termina
    if quincena.estatus != "A":
        click.echo("Quincena ha sido eliminada.")
        return

    # Consultar las quincenas de los beneficiarios activos
    beneficiarios_quincenas = BeneficiarioQuincena.query.filter_by(quincena_id=quincena.id).filter_by(estatus="A").all()

    # TODO: Si no hay quincenas de los beneficiarios, tomamos la quincena anterior para agregar nuevos registros

    # Iniciar el archivo XLSX
    libro = Workbook()

    # Tomar la hoja del libro XLSX
    hoja = libro.active

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
            personas_sin_cuentas.append(bq.persona)
            continue

        # Tomar la cuenta de la persona que no tenga la clave 9, porque esa clave es la de DESPENSA
        su_cuenta = None
        for cuenta in cuentas:
            if cuenta.banco.clave != "9":
                su_cuenta = cuenta
                break

        # Si no tiene cuenta bancaria, entonces se agrega a la lista de personas_sin_cuentas y se salta
        if su_cuenta is None:
            personas_sin_cuentas.append(bq.persona)
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

    # Si hubo personas sin cuentas, entonces mostrarlas en pantalla
    if len(personas_sin_cuentas) > 0:
        click.echo("AVISO: Hubo personas sin cuentas:")
        for persona in personas_sin_cuentas:
            click.echo(f"- {persona.rfc} {persona.nombre_completo}")

    # Mensaje termino
    click.echo(f"Beneficiarios quincenas: {contador} filas en {nombre_archivo}")


cli.add_command(generar)
