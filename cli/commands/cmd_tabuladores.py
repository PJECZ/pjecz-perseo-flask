"""
CLI Tabuladores
"""

import csv
import sys
from datetime import datetime
from pathlib import Path

import click

from lib.exceptions import MyAnyError
from lib.safe_string import safe_clave
from perseo.app import create_app
from perseo.blueprints.puestos.models import Puesto
from perseo.blueprints.tabuladores.models import Tabulador
from perseo.blueprints.tabuladores.tasks import exportar_xlsx as task_exportar_xlsx

TABULADORES_CSV = "seed/tabuladores-NNN.csv"

app = create_app()
app.app_context().push()


@click.group()
def cli():
    """Tabuladores"""


@click.command()
@click.option("--tabuladores-csv", default=TABULADORES_CSV, help="Archivo CSV con los datos de los Tabuladores")
def agregar_actualizar(tabuladores_csv: str):
    """Agregar o actualizar tabuladores y puestos a partir de un archivo CSV"""

    # Validar archivo CSV
    ruta = Path(tabuladores_csv)
    if not ruta.exists():
        click.echo(f"ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        click.echo(f"ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)

    # Inicializar contadores y mensajes
    contador_puestos_insertados = 0
    contador_tabuladores_insertados = 0
    contador_tabuladores_actualizados = 0
    errores = []

    # Leer el archivo CSV
    click.echo("Alimentando Tabuladores y Puestos: ", nl=False)
    with open(ruta, newline="", encoding="utf8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Validar MODELO, NIVEL, QUINQUENIO, SUELDO BASE
            try:
                modelo = int(row["MODELO"])
                nivel = int(row["NIVEL"])
                quinquenio = int(row["QUINQUENIO"])
            except (KeyError, ValueError) as error:
                errores.append(f"  Es incorrecto: {error}, se omite")
                click.echo("E", nl=False)
                continue

            # SUELDO BASE
            try:
                sueldo_base = float(row["SUELDO BASE"])
            except (KeyError, ValueError):
                sueldo_base = 0.0

            # Validar CLAVE DE PUESTO
            clave_puesto = safe_clave(row["CLAVE DE PUESTO"])
            if clave_puesto == "":
                errores.append("  Falta una clave de puesto, se omite")
                click.echo("E", nl=False)
                continue

            # INCENTIVO
            try:
                incentivo = float(row["INCENTIVO"])
            except (KeyError, ValueError):
                incentivo = 0.0

            # MONEDERO
            try:
                monedero = float(row["MONEDERO"])
            except (KeyError, ValueError):
                monedero = 0.0

            # RECREACION CULTURA Y DEPORTE
            try:
                rec_cul_dep = float(row["RECREACION CULTURA Y DEPORTE"])
            except (KeyError, ValueError):
                rec_cul_dep = 0.0

            # SOBRESUELDO
            try:
                sobresueldo = float(row["SOBRESUELDO"])
            except (KeyError, ValueError):
                sobresueldo = 0.0

            # RECREACION DEPORTE Y CULTURA GRAVADO
            try:
                rec_dep_cul_gravado = float(row["RECREACION DEPORTE Y CULTURA GRAVADO"])
            except (KeyError, ValueError):
                rec_dep_cul_gravado = 0.0

            # RECREACION DEPORTE Y CULTURA EXCENTO
            try:
                rec_dep_cul_excento = float(row["RECREACION DEPORTE Y CULTURA EXCENTO"])
            except (KeyError, ValueError):
                rec_dep_cul_excento = 0.0

            # AYUDA DE TRANSPORTE
            try:
                ayuda_transp = float(row["AYUDA DE TRANSPORTE"])
            except (KeyError, ValueError):
                ayuda_transp = 0.0

            # MONTO QUINQUENIO
            try:
                monto_quinquenio = float(row["MONTO QUINQUENIO"])
            except (KeyError, ValueError):
                monto_quinquenio = 0.0

            # TOTAL DE PERCEPCIONES
            try:
                total_percepciones = float(row["TOTAL DE PERCEPCIONES"])
            except (KeyError, ValueError):
                total_percepciones = 0.0

            # SALARIO DIARIO
            try:
                salario_diario = float(row["SALARIO DIARIO"])
            except (KeyError, ValueError):
                salario_diario = 0.0

            # PRIMA VACACIONAL MENSUAL
            try:
                prima_vacacional_mensual = float(row["PRIMA VACACIONAL MENSUAL"])
            except (KeyError, ValueError):
                prima_vacacional_mensual = 0.0

            # AGUINALDO MENSUAL
            try:
                aguinaldo_mensual = float(row["AGUINALDO MENSUAL"])
            except (KeyError, ValueError):
                aguinaldo_mensual = 0.0

            # PRIMA VACACIONAL MENSUAL ADICIONAL
            try:
                prima_vacacional_mensual_adicional = float(row["PRIMA VACACIONAL MENSUAL ADICIONAL"])
            except (KeyError, ValueError):
                prima_vacacional_mensual_adicional = 0.0

            # TOTAL DE PERCEPCIONES INTEGRADO
            try:
                total_percepciones_integrado = float(row["TOTAL DE PERCEPCIONES INTEGRADO"])
            except (KeyError, ValueError):
                total_percepciones_integrado = 0.0

            # SALARIO DIARIO INTEGRADO
            try:
                salario_diario_integrado = float(row["SALARIO DIARIO INTEGRADO"])
            except (KeyError, ValueError):
                salario_diario_integrado = 0.0

            # FECHA INICIO viene como DD/MM/YYYY convertir a date
            try:
                fecha_inicio = datetime.strptime(row["FECHA INICIO"], "%d/%m/%Y").date()
            except (KeyError, ValueError):
                fecha_inicio = datetime.now().date()

            # PENSION VITALICIA (EXENTO)
            try:
                pension_vitalicia_excento = float(row["PENSION VITALICIA (EXENTO)"])
            except (KeyError, ValueError):
                pension_vitalicia_excento = 0.0

            # PENSION VITALICIA (GRAVABLE)
            try:
                pension_vitalicia_gravable = float(row["PENSION VITALICIA (GRAVABLE)"])
            except (KeyError, ValueError):
                pension_vitalicia_gravable = 0.0

            # BONIFICACION
            try:
                pension_bonificacion = float(row["BONIFICACION"])
            except (KeyError, ValueError):
                pension_bonificacion = 0.0

            # Consular el puesto, si no existe el puesto, se inserta con una descripción NO DEFINIDO
            puesto = Puesto.query.filter(Puesto.clave == clave_puesto).first()
            if not puesto:
                puesto = Puesto(
                    clave=clave_puesto,
                    descripcion="NO DEFINIDO",
                ).save()
                contador_puestos_insertados += 1
                click.echo("p", nl=False)

            # Revisar el tabulador, porque la clave de puesto, modelo, nivel y quinquenio no deben repetirse
            tabulador = Tabulador.query.filter(
                Tabulador.puesto_id == puesto.id,
                Tabulador.modelo == modelo,
                Tabulador.nivel == nivel,
                Tabulador.quinquenio == quinquenio,
            ).first()

            # Si no existe el tabulador, se inserta
            if tabulador is None:
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
                    pension_vitalicia_excento=pension_vitalicia_excento,
                    pension_vitalicia_gravable=pension_vitalicia_gravable,
                    pension_bonificacion=pension_bonificacion,
                )
                tabulador.save()
                contador_tabuladores_insertados += 1
                click.echo("t", nl=False)
            else:
                # Si existe, se actualiza
                tabulador.sueldo_base = sueldo_base
                tabulador.incentivo = incentivo
                tabulador.monedero = monedero
                tabulador.rec_cul_dep = rec_cul_dep
                tabulador.sobresueldo = sobresueldo
                tabulador.rec_dep_cul_gravado = rec_dep_cul_gravado
                tabulador.rec_dep_cul_excento = rec_dep_cul_excento
                tabulador.ayuda_transp = ayuda_transp
                tabulador.monto_quinquenio = monto_quinquenio
                tabulador.total_percepciones = total_percepciones
                tabulador.salario_diario = salario_diario
                tabulador.prima_vacacional_mensual = prima_vacacional_mensual
                tabulador.aguinaldo_mensual = aguinaldo_mensual
                tabulador.prima_vacacional_mensual_adicional = prima_vacacional_mensual_adicional
                tabulador.total_percepciones_integrado = total_percepciones_integrado
                tabulador.salario_diario_integrado = salario_diario_integrado
                tabulador.fecha = fecha_inicio
                tabulador.pension_vitalicia_excento = pension_vitalicia_excento
                tabulador.pension_vitalicia_gravable = pension_vitalicia_gravable
                tabulador.pension_bonificacion = pension_bonificacion
                tabulador.save()
                contador_tabuladores_actualizados += 1
                click.echo("u", nl=False)

    # Poner avance de linea
    click.echo("")

    # Si hubo errores, mostrarlos
    if len(errores) > 0:
        click.echo(click.style(f"  Hubo {len(errores)} errores:", fg="red"))
        click.echo(click.style(f"  {', '.join(errores)}", fg="red"))

    # Si hubo puestos insertados, mostrar contador
    if contador_puestos_insertados > 0:
        click.echo(click.style(f"  Puestos: {contador_puestos_insertados} insertados.", fg="green"))

    # Si hubo tabuladores insertados, mostrar contador
    if contador_tabuladores_insertados > 0:
        click.echo(click.style(f"  Tabuladores: {contador_tabuladores_insertados} insertados.", fg="green"))

    # Si hubo tabuladores actualizados, mostrar contador
    if contador_tabuladores_actualizados > 0:
        click.echo(click.style(f"  Tabuladores: {contador_tabuladores_actualizados} actualizados.", fg="green"))


@click.command()
def exportar_xlsx():
    """Exportar Tabuladores a un archivo XLSX"""

    # Ejecutar la tarea
    try:
        mensaje_termino, _, _ = task_exportar_xlsx()
    except MyAnyError as error:
        click.echo(click.style(str(error), fg="red"))
        sys.exit(1)

    # Mensaje de termino
    click.echo(click.style(mensaje_termino, fg="green"))


cli.add_command(agregar_actualizar)
cli.add_command(exportar_xlsx)
