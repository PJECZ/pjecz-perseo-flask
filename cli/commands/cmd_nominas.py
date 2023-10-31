"""
CLI Nominas

Columnas a entregar

- Centro de trabajo
- RFC
- Nombre completo
- Banco administrador, su clave
- Nombre del banco
- Numero de cuenta
- Monto a depositar, columna (IMPTE)
- Numero de empleado
- Quincena
- Modelo
- No de cheque (Clave del banco + secuencia) deben ser 9 digitos

"""
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
from perseo.extensions import database

EXPLOTACION_BASE_DIR = os.environ.get("EXPLOTACION_BASE_DIR")
NOMINAS_FILENAME_XLS = "NominaFmt2.XLS"

app = create_app()
app.app_context().push()
database.app = app


@click.group()
def cli():
    """Nominas"""


@click.command()
@click.argument("quincena", type=str)
def alimentar(quincena: str):
    """Alimentar nominas"""

    # Iniciar sesion con la base de datos para que la alimentacion sea rapida
    sesion = database.session

    # Validar quincena
    if re.match(QUINCENA_REGEXP, quincena) is None:
        click.echo("Quincena inválida")
        return

    # Validar el directorio donde espera encontrar los archivos de explotacion
    if EXPLOTACION_BASE_DIR is None:
        click.echo("Variable de entorno EXPLOTACION_BASE_DIR no definida.")
        return

    # Validar si existe el archivo
    ruta = Path(EXPLOTACION_BASE_DIR, quincena, NOMINAS_FILENAME_XLS)
    if not ruta.exists():
        click.echo(f"AVISO: {str(ruta)} no se encontró.")
        return
    if not ruta.is_file():
        click.echo(f"AVISO: {str(ruta)} no es un archivo.")
        return

    # Abrir el archivo XLS con xlrd
    libro = xlrd.open_workbook(str(ruta))

    # Obtener la primera hoja
    hoja = libro.sheet_by_index(0)

    # Iniciar contador de percepciones-deducciones alimentadas
    contador = 0

    # Bucle por cada fila
    click.echo("Alimentando nominas...")
    for fila in range(1, hoja.nrows):
        # Tomar las columnas
        centro_trabajo_clave = hoja.cell_value(fila, 1)
        rfc = hoja.cell_value(fila, 2)
        nombre_completo = hoja.cell_value(fila, 3)
        plaza_clave = hoja.cell_value(fila, 8)
        percepcion = int(hoja.cell_value(fila, 12)) / 100.0
        deduccion = int(hoja.cell_value(fila, 13)) / 100.0
        impte = int(hoja.cell_value(fila, 14)) / 100.0
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

        # Alimentar nomina
        nomina = Nomina(
            centro_trabajo=centro_trabajo,
            persona=persona,
            plaza=plaza,
            quincena=quincena,
            percepcion=percepcion,
            deduccion=deduccion,
            importe=impte,
        )
        sesion.add(nomina)

        # Incrementar contador
        contador += 1
        if contador % 100 == 0:
            click.echo(f"  Van {contador}...")

    # Cerrar la sesion para que se guarden todos los datos en la base de datos
    sesion.commit()
    sesion.close()

    # Mensaje termino
    click.echo(f"Terminado con {contador} nominas alimentadas.")


cli.add_command(alimentar)
