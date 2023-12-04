"""
CLI Bancos
"""
import csv
import sys
from pathlib import Path

import click

from lib.safe_string import safe_string
from perseo.app import create_app
from perseo.blueprints.bancos.models import Banco
from perseo.extensions import database

BANCOS_CSV = "seed/bancos.csv"

app = create_app()
app.app_context().push()


@click.group()
def cli():
    """Bancos"""


@click.command()
def alimentar():
    """Alimentar bancos"""

    # Validar archivo CSV
    ruta = Path(BANCOS_CSV)
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
    click.echo("Alimentando Bancos: ", nl=False)
    with open(ruta, newline="", encoding="utf8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Validar
            try:
                clave = row["clave"]
                nombre = safe_string(row["nombre"])
                if nombre == "":
                    raise ValueError("nombre vacio")
                clave_dispersion_pensionados = row["clave_dispersion_pensionados"]
                if clave_dispersion_pensionados == "":
                    raise ValueError("clave_dispersion_pensionados vacio")
            except ValueError as error:
                errores.append(f"  {row['clave']}: {error}")
                click.echo("E", nl=False)
                continue

            # Revisar si ya existe
            banco = Banco.query.filter_by(clave=clave).first()

            # Si no existe, se agrega
            if banco is None:
                Banco(
                    clave=clave,
                    clave_dispersion_pensionados=clave_dispersion_pensionados,
                    nombre=nombre,
                    consecutivo=0,
                    consecutivo_generado=0,
                ).save()
                contador_insertados += 1
                click.echo(".", nl=False)
            elif banco.nombre != nombre or banco.clave_dispersion_pensionados != clave_dispersion_pensionados:
                # Si cambio el nombre o la clave de dispersion de pensionados, se actualiza
                banco.nombre = nombre
                banco.clave_dispersion_pensionados = clave_dispersion_pensionados
                banco.save()
                contador_actualizados += 1
                click.echo("u", nl=False)

    # Poner avance de linea
    click.echo("")

    # Si hubo errores, mostrarlos
    if len(errores) > 0:
        click.echo(click.style(f"  Hubo {len(errores)} errores:", fg="red"))
        click.echo(click.style(f"  {', '.join(errores)}", fg="red"))

    # Si hubo bancos insertados, mostrar contador
    if contador_insertados > 0:
        click.echo(click.style(f"  Bancos: {contador_insertados} insertados.", fg="green"))

    # Si hubo bancos actualizados, mostrar contador
    if contador_actualizados > 0:
        click.echo(click.style(f"  Bancos: {contador_actualizados} actualizados.", fg="green"))


@click.command()
def reiniciar_consecutivos_generados():
    """Reiniciar los consecutivos generados de cada banco con el consecutivo"""

    # Iniciar sesion con la base de datos para que la alimentacion sea rapida
    sesion = database.session

    # Bucle por todos los bancos
    contador = 0
    for banco in Banco.query.filter_by(estatus="A").all():
        # Si son diferentes
        if banco.consecutivo_generado != banco.consecutivo:
            # Recordar el valor anterior
            valor_anterior = banco.consecutivo_generado

            # Recordar el valor nuevo
            valor_nuevo = banco.consecutivo

            # Poner el valor de consecutivo generado con el de consecutivo
            banco.consecutivo_generado = valor_nuevo

            # Guardar el banco
            sesion.add(banco)

            # Mostrar en pantalla el cambio
            click.echo(f"  {banco.nombre} cambia de {valor_anterior} a {valor_nuevo}")

            # Incrementar el contador
            contador += 1

    # Si no hubo cambios
    if contador == 0:
        click.echo("AVISO: No hubo necesidad de reiniciar ningun consecutivo_generado.")
        sys.exit(0)

    # Actualizar los consecutivos_generados de cada banco
    sesion.commit()

    # Mensaje de termino
    click.echo(f"Reiniciar los consecutivos generados terminado: {contador} reiniciados.")


cli.add_command(alimentar)
cli.add_command(reiniciar_consecutivos_generados)
