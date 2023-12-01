"""
CLI Tabuladores
"""
import csv
import sys
from datetime import datetime
from pathlib import Path

import click

from lib.safe_string import safe_clave
from perseo.app import create_app
from perseo.blueprints.puestos.models import Puesto
from perseo.blueprints.tabuladores.models import Tabulador

TABULADORES_CSV = "seed/tabuladores.csv"

app = create_app()
app.app_context().push()


@click.group()
def cli():
    """Tabuladores"""


@click.command()
@click.option("--tabuladores-csv", default=TABULADORES_CSV, help="Archivo CSV con los datos de los Tabuladores")
def alimentar(tabuladores_csv: str):
    """Alimentar tabuladores"""

    # Validar archivo
    ruta = Path(tabuladores_csv)
    if not ruta.exists():
        click.echo(f"ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        click.echo(f"ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)

    # Inicializar contadores y mensajes
    contador = 0
    errores = []

    # Leer el archivo CSV
    click.echo("Alimentando Tabuladores: ", nl=False)
    with open(ruta, newline="", encoding="utf8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # MODELO, NIVEL, QUINQUENIO, SUELDO BASE
            try:
                modelo = int(row["MODELO"])
                nivel = int(row["NIVEL"])
                quinquenio = int(row["QUINQUENIO"])
                sueldo_base = float(row["SUELDO BASE"])
            except ValueError as error:
                click.echo(click.style(f"  Es incorrecto y se omite: {error}", fg="red"))
                continue
            # CLAVE DE PUESTO
            clave_puesto = safe_clave(row["CLAVE DE PUESTO"])
            if clave_puesto == "":
                click.echo(click.style("  Falta una clave de puesto, se omite", fg="red"))
                continue
            # INCENTIVO
            try:
                incentivo = float(row["INCENTIVO"])
            except ValueError:
                incentivo = 0.0
            # MONEDERO
            try:
                monedero = float(row["MONEDERO"])
            except ValueError:
                monedero = 0.0
            # RECREACION CULTURA Y DEPORTE
            try:
                rec_cul_dep = float(row["RECREACION CULTURA Y DEPORTE"])
            except ValueError:
                rec_cul_dep = 0.0
            # SOBRESUELDO
            try:
                sobresueldo = float(row["SOBRESUELDO"])
            except ValueError:
                sobresueldo = 0.0
            # RECREACION DEPORTE Y CULTURA GRAVADO
            try:
                rec_dep_cul_gravado = float(row["RECREACION DEPORTE Y CULTURA GRAVADO"])
            except ValueError:
                rec_dep_cul_gravado = 0.0
            # RECREACION DEPORTE Y CULTURA EXCENTO
            try:
                rec_dep_cul_excento = float(row["RECREACION DEPORTE Y CULTURA EXCENTO"])
            except ValueError:
                rec_dep_cul_excento = 0.0
            # AYUDA DE TRANSPORTE
            try:
                ayuda_transp = float(row["AYUDA DE TRANSPORTE"])
            except ValueError:
                ayuda_transp = 0.0
            # MONTO QUINQUENIO
            try:
                monto_quinquenio = float(row["MONTO QUINQUENIO"])
            except ValueError:
                monto_quinquenio = 0.0
            # TOTAL DE PERCEPCIONES
            try:
                total_percepciones = float(row["TOTAL DE PERCEPCIONES"])
            except ValueError:
                click.echo(click.style("  Falta TOTAL DE PERCEPCIONES, se omite", fg="red"))
                continue
            # SALARIO DIARIO
            try:
                salario_diario = float(row["SALARIO DIARIO"])
            except ValueError:
                salario_diario = 0.0
            # PRIMA VACACIONAL MENSUAL
            try:
                prima_vacacional_mensual = float(row["PRIMA VACACIONAL MENSUAL"])
            except ValueError:
                prima_vacacional_mensual = 0.0
            # AGUINALDO MENSUAL
            try:
                aguinaldo_mensual = float(row["AGUINALDO MENSUAL"])
            except ValueError:
                aguinaldo_mensual = 0.0
            # PRIMA VACACIONAL MENSUAL ADICIONAL
            try:
                prima_vacacional_mensual_adicional = float(row["PRIMA VACACIONAL MENSUAL ADICIONAL"])
            except ValueError:
                prima_vacacional_mensual_adicional = 0.0
            # TOTAL DE PERCEPCIONES INTEGRADO
            try:
                total_percepciones_integrado = float(row["TOTAL DE PERCEPCIONES INTEGRADO"])
            except ValueError:
                click.echo(click.style("  Falta TOTAL DE PERCEPCIONES INTEGRADO, se omite", fg="red"))
                continue
            # SALARIO DIARIO INTEGRADO
            try:
                salario_diario_integrado = float(row["SALARIO DIARIO INTEGRADO"])
            except ValueError:
                salario_diario_integrado = 0.0
            # FECHA INICIO viene como DD/MM/YYYY convertir a date
            try:
                fecha_inicio = datetime.strptime(row["FECHA INICIO"], "%d/%m/%Y").date()
            except ValueError:
                fecha_inicio = datetime.now().date()
            # Consular el puesto, si no existe el puesto, se inserta con una descripción NO DEFINIDO
            puesto = Puesto.query.filter(Puesto.clave == clave_puesto).first()
            if not puesto:
                puesto = Puesto(
                    clave=clave_puesto,
                    descripcion="NO DEFINIDO",
                ).save()
            # TODO: Antes de insertar el tabulador, validar que la clave de puesto, modelo, nivel y quinquenio no se repitan
            # TODO: Insertar o actualizar el tabulador
            # Insertar tabulador
            tabulador = Tabulador(
                puesto_id=puesto.id,
                modelo=modelo,
                nivel=nivel,
                quinquenio=quinquenio,
                sueldo_base=sueldo_base,
                incentivo=incentivo,
                monedero=monedero,
                rec_cul_dep=rec_cul_dep,
                sobresueldo=sobresueldo,
                rec_dep_cul_gravado=rec_dep_cul_gravado,
                rec_dep_cul_excento=rec_dep_cul_excento,
                ayuda_transp=ayuda_transp,
                monto_quinquenio=monto_quinquenio,
                total_percepciones=total_percepciones,
                salario_diario=salario_diario,
                prima_vacacional_mensual=prima_vacacional_mensual,
                aguinaldo_mensual=aguinaldo_mensual,
                prima_vacacional_mensual_adicional=prima_vacacional_mensual_adicional,
                total_percepciones_integrado=total_percepciones_integrado,
                salario_diario_integrado=salario_diario_integrado,
                fecha=fecha_inicio,
            )
            tabulador.save()
            contador += 1
            click.echo(click.style(".", fg="cyan"), nl=False)

    # Mensaje termino
    click.echo(f"  Tabuladores: {contador} alimentados.")


cli.add_command(alimentar)
