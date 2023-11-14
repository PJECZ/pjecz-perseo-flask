"""
CLI Percepciones-Deducciones
"""
import csv
import os
import re
from pathlib import Path

import click
import xlrd
from dotenv import load_dotenv

from lib.safe_string import QUINCENA_REGEXP, safe_clave, safe_quincena, safe_string
from perseo.app import create_app
from perseo.blueprints.centros_trabajos.models import CentroTrabajo
from perseo.blueprints.conceptos.models import Concepto
from perseo.blueprints.conceptos_productos.models import ConceptoProducto
from perseo.blueprints.nominas.models import Nomina
from perseo.blueprints.percepciones_deducciones.models import PercepcionDeduccion
from perseo.blueprints.personas.models import Persona
from perseo.blueprints.plazas.models import Plaza
from perseo.blueprints.productos.models import Producto
from perseo.blueprints.quincenas.models import Quincena
from perseo.extensions import database

EXPLOTACION_BASE_DIR = os.environ.get("EXPLOTACION_BASE_DIR")
NOMINAS_FILENAME_XLS = "NominaFmt2.XLS"

app = create_app()
app.app_context().push()
database.app = app


@click.group()
def cli():
    """Percepciones-Deducciones"""


@click.command()
@click.argument("quincena_clave", type=str)
def alimentar(quincena_clave: str):
    """Alimentar percepciones-deducciones"""

    # Iniciar sesion con la base de datos para que la alimentacion sea rapida
    sesion = database.session

    # Validar quincena
    if re.match(QUINCENA_REGEXP, quincena_clave) is None:
        click.echo("Quincena inválida")
        return

    # Validar el directorio donde espera encontrar los archivos de explotacion
    if EXPLOTACION_BASE_DIR is None:
        click.echo("Variable de entorno EXPLOTACION_BASE_DIR no definida.")
        return

    # Validar si existe el archivo
    ruta = Path(EXPLOTACION_BASE_DIR, quincena_clave, NOMINAS_FILENAME_XLS)
    if not ruta.exists():
        click.echo(f"AVISO: {str(ruta)} no se encontró.")
        return
    if not ruta.is_file():
        click.echo(f"AVISO: {str(ruta)} no es un archivo.")
        return

    # Revisar si existe el registro en quincenas, de lo contrario insertarlo
    quincena = Quincena.query.filter_by(clave=quincena_clave).first()
    if quincena is None:
        quincena = Quincena(clave=quincena_clave, estado=Quincena.ESTADOS["ABIERTA"])
        sesion.add(quincena)
        click.echo(f"  Quincena {quincena_clave} insertada")

    # Abrir el archivo XLS con xlrd
    libro = xlrd.open_workbook(str(ruta))

    # Obtener la primera hoja
    hoja = libro.sheet_by_index(0)

    # Iniciar listado de conceptos que no existen
    conceptos_no_existentes = []

    # Iniciar contador de percepciones-deducciones alimentadas
    contador = 0

    # Bucle por cada fila
    click.echo("Alimentando percepciones-deducciones...")
    for fila in range(1, hoja.nrows):
        # Tomar las columnas
        centro_trabajo_clave = hoja.cell_value(fila, 1)
        rfc = hoja.cell_value(fila, 2)
        nombre_completo = hoja.cell_value(fila, 3)
        plaza_clave = hoja.cell_value(fila, 8)
        modelo = int(hoja.cell_value(fila, 236))
        num_empleado = int(hoja.cell_value(fila, 240))

        # Separar nombre_completo, en apellido_primero, apellido_segundo y nombres
        separado = safe_string(nombre_completo, save_enie=True).split(" ")
        apellido_primero = separado[0]
        apellido_segundo = separado[1]
        nombres = " ".join(separado[2:])

        # Revisar si el Centro de Trabajo existe, de lo contrario insertarlo
        centro_trabajo = CentroTrabajo.query.filter_by(clave=centro_trabajo_clave).first()
        if centro_trabajo is None:
            centro_trabajo = CentroTrabajo(clave=centro_trabajo_clave, descripcion="ND")
            sesion.add(centro_trabajo)
            click.echo(f"  Centro de Trabajo {centro_trabajo_clave} insertado")

        # Revisar si la Persona existe, de lo contrario insertarlo
        persona = Persona.query.filter_by(rfc=rfc).first()
        if persona is None:
            persona = Persona(
                rfc=rfc,
                nombres=nombres,
                apellido_primero=apellido_primero,
                apellido_segundo=apellido_segundo,
                modelo=modelo,
                num_empleado=num_empleado,
            )
            sesion.add(persona)
            click.echo(f"  Persona {rfc} insertada")

        # Revisar si la Plaza existe, de lo contrario insertarla
        plaza = Plaza.query.filter_by(clave=plaza_clave).first()
        if plaza is None:
            plaza = Plaza(clave=plaza_clave, descripcion="ND")
            sesion.add(plaza)
            click.echo(f"  Plaza {plaza_clave} insertada")

        # Buscar percepciones y deducciones
        col_num = 26
        while True:
            # Tomar el tipo, primero
            tipo = safe_string(hoja.cell_value(fila, col_num))

            # Si el tipo es un texto vacio, se rompe el ciclo
            if tipo == "":
                break

            # Tomar las cinco columnas
            conc = safe_string(hoja.cell_value(fila, col_num + 1))
            try:
                impt = int(hoja.cell_value(fila, col_num + 3)) / 100.0
            except ValueError:
                impt = 0.0

            # Revisar si el Concepto existe, de lo contrario SE OMITE
            concepto_clave = f"{tipo}{conc}"
            concepto = Concepto.query.filter_by(clave=concepto_clave).first()
            if concepto is None and concepto_clave not in conceptos_no_existentes:
                conceptos_no_existentes.append(concepto_clave)
                concepto = Concepto(clave=concepto_clave, descripcion="DESCONOCIDO")
                sesion.add(concepto)
                click.echo(f"  Concepto {concepto_clave} insertado")

            # Alimentar percepcion-deduccion
            percepcion_deduccion = PercepcionDeduccion(
                centro_trabajo=centro_trabajo,
                concepto=concepto,
                persona=persona,
                plaza=plaza,
                quincena=quincena,
                importe=impt,
            )
            sesion.add(percepcion_deduccion)

            # Incrementar col_num en SEIS
            col_num += 6

            # Romper el ciclo cuando se llega a la columna
            if col_num > 236:
                break

            # Incrementar contador
            contador += 1
            if contador % 100 == 0:
                click.echo(f"  Van {contador}...")

    # Cerrar la sesion para que se guarden todos los datos en la base de datos
    sesion.commit()
    sesion.close()

    # Mensaje termino
    if len(conceptos_no_existentes) > 0:
        click.echo(f"  AVISO: Conceptos no existentes: {','.join(conceptos_no_existentes)}")
    click.echo(f"Percepciones-Deducciones terminado: {contador} alimentados en la quincena {quincena_clave}.")


cli.add_command(alimentar)
