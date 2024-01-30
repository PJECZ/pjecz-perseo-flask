"""
CLI Conceptos

Columnas del CSV:

- P_D
- Concepto
- Descripcion

"""
import csv
import re
import sys
from pathlib import Path

import click

from lib.exceptions import MyAnyError
from lib.safe_string import QUINCENA_REGEXP, safe_clave, safe_string
from perseo.app import create_app
from perseo.blueprints.conceptos.models import Concepto
from perseo.blueprints.conceptos.tasks import exportar_xlsx
from perseo.blueprints.percepciones_deducciones.models import PercepcionDeduccion
from perseo.blueprints.quincenas.models import Quincena

CONCEPTOS_CSV = "seed/conceptos.csv"

app = create_app()
app.app_context().push()


@click.group()
def cli():
    """Conceptos"""


@click.command()
@click.option("--conceptos-csv", default=CONCEPTOS_CSV, help="Archivo CSV con los datos de los Conceptos")
def agregar_actualizar(conceptos_csv: str):
    """Agregar o actualizar Conceptos a partir de un archivo CSV"""

    # Validar archivo CSV
    ruta = Path(conceptos_csv)
    if not ruta.exists():
        click.echo(f"ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        click.echo(f"ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)

    # Inicializar contadores y mensajes
    contador_insertados = 0
    contador_actualizados = 0
    errores = []

    # Leer el archivo CSV
    click.echo("Alimentando Conceptos: ", nl=False)
    with open(ruta, newline="", encoding="utf8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Validar
            try:
                clave = safe_clave(f"{row['P_D']}{row['Concepto']}")
                descripcion = safe_string(row["Descripcion"], save_enie=True)
                if descripcion == "":
                    raise ValueError("Descripcion vacía")
            except ValueError as error:
                errores.append(f"  {row['P_D']}{row['Concepto']}: {error}")
                click.echo("E", nl=False)
                continue

            # Revisar si ya existe
            concepto = Concepto.query.filter_by(clave=clave).first()

            # Si NO existe, se agrega
            if concepto is None:
                Concepto(
                    clave=clave,
                    descripcion=descripcion,
                ).save()
                contador_insertados += 1
                click.echo(".", nl=False)
            elif concepto.descripcion != descripcion:
                # Si cambia la descripcion, se actualiza
                concepto.descripcion = descripcion
                concepto.save()
                contador_actualizados += 1
                click.echo("u", nl=False)

    # Poner avance de linea
    click.echo("")

    # Si hubo errores, mostrarlos
    if len(errores) > 0:
        click.echo(click.style(f"  Hubo {len(errores)} errores:", fg="red"))
        click.echo(click.style(f"  {', '.join(errores)}", fg="red"))

    # Si hubo contador_insertados, mostrar contador
    if contador_insertados > 0:
        click.echo(click.style(f"  Conceptos: {contador_insertados} insertados.", fg="green"))

    # Si hubo contador_actualizados, mostrar contador
    if contador_actualizados > 0:
        click.echo(click.style(f"  Conceptos: {contador_actualizados} actualizados.", fg="green"))


@click.command()
@click.option("--quincena-clave", default="", help="6 digitos")
def eliminar_recuperar(quincena_clave: str):
    """Eliminar o recuperar Conceptos si no/si se usan en Percepciones-Deducciones"""
    click.echo("Eliminar Conceptos que no se usan...")

    # Si viene la quincena, validar y consultar
    quincena = None
    if quincena_clave != "":
        if re.match(QUINCENA_REGEXP, quincena_clave) is None:
            click.echo("ERROR: Quincena inválida.")
            sys.exit(1)
        quincena = Quincena.query.filter_by(clave=quincena_clave).filter_by(estatus="A").first()
        if quincena is None:
            click.echo("ERROR: Quincena no encontrada o eliminada.")
            sys.exit(1)

    # Consultar todos los conceptos, en uso y eliminados
    conceptos = Concepto.query.all()

    # Si no hay conceptos, salir
    if not conceptos:
        click.echo("AVISO: No hay conceptos.")
        sys.exit(0)

    # Bucle por cada concepto
    conceptos_eliminados = []
    conceptos_recuperados = []
    for concepto in conceptos:
        # Se salta si tiene clave PAZ, DAZ y D62 porque se usan en el apoyo anual
        if concepto.clave in ["PAZ", "DAZ", "D62"]:
            continue

        # Consultar las Percepciones-Deducciones que usen el concepto en turno
        percepciones_deducciones = PercepcionDeduccion.query.filter_by(concepto_id=concepto.id)

        # Si se especifico la quincena, filtrar las P-D por quincena
        if quincena is not None:
            percepciones_deducciones = percepciones_deducciones.filter_by(quincena_id=quincena.id)

        # Si la cantidad de Percepciones-Deducciones es 0, eliminar el concepto, de lo contrario, recuperarlo
        if percepciones_deducciones.count() == 0 and concepto.estatus == "A":
            concepto.estatus = "B"
            concepto.save()
            conceptos_eliminados.append(concepto.clave)
        elif percepciones_deducciones.count() > 0 and concepto.estatus == "B":
            concepto.estatus = "A"
            concepto.save()
            conceptos_recuperados.append(concepto.clave)

    # Si hubo conceptos eliminados, mostrarlos
    click.echo(click.style(f"Se eliminaron {len(conceptos_eliminados)} Conceptos", fg="red"))
    click.echo(click.style(f"  {', '.join(conceptos_eliminados)}", fg="red"))

    # Si hubo conceptos recuperados, mostrarlos
    click.echo(click.style(f"Se recuperaron {len(conceptos_recuperados)} Conceptos", fg="green"))
    click.echo(click.style(f"  {', '.join(conceptos_recuperados)}", fg="green"))


@click.command()
def exportar():
    """Exportar Conceptos a un archivo XLSX"""

    # Ejecutar la tarea
    try:
        mensaje_termino, _, _ = exportar_xlsx()
    except MyAnyError as error:
        click.echo(click.style(str(error), fg="red"))
        sys.exit(1)

    # Mensaje de termino
    click.echo(click.style(mensaje_termino, fg="green"))


cli.add_command(agregar_actualizar)
cli.add_command(eliminar_recuperar)
cli.add_command(exportar)
