"""
CLI Cuentas

Toma el archivo EmpleadosAlfabetico.XLS

Necesita la quincena como argumento para saber donde buscar el archivo

"""
import os
import re
import sys
from pathlib import Path

import click
import xlrd
from dotenv import load_dotenv

from lib.safe_string import QUINCENA_REGEXP
from perseo.app import create_app
from perseo.blueprints.bancos.models import Banco
from perseo.blueprints.centros_trabajos.models import CentroTrabajo
from perseo.blueprints.conceptos.models import Concepto
from perseo.blueprints.conceptos_productos.models import ConceptoProducto
from perseo.blueprints.cuentas.models import Cuenta
from perseo.blueprints.nominas.models import Nomina
from perseo.blueprints.percepciones_deducciones.models import PercepcionDeduccion
from perseo.blueprints.personas.models import Persona
from perseo.blueprints.plazas.models import Plaza
from perseo.blueprints.productos.models import Producto
from perseo.extensions import database

EXPLOTACION_BASE_DIR = os.environ.get("EXPLOTACION_BASE_DIR")
CUENTAS_FILENAME_XLS = "EmpleadosAlfabetico.XLS"
MONEDEROS_FILENAME_XLS = "Monederos.XLS"

app = create_app()
app.app_context().push()
database.app = app


@click.group()
def cli():
    """Cuentas"""


@click.command()
@click.argument("quincena", type=str)
def alimentar_bancarias(quincena: str):
    """Alimentar Cuentas Bancarias"""

    # Iniciar sesion con la base de datos para que la alimentacion sea rapida
    sesion = database.session

    # Validar quincena
    if re.match(QUINCENA_REGEXP, quincena) is None:
        click.echo("ERROR: Quincena inválida")
        sys.exit(1)

    # Validar el directorio donde espera encontrar los archivos de explotacion
    if EXPLOTACION_BASE_DIR is None:
        click.echo("ERROR: Variable de entorno EXPLOTACION_BASE_DIR no definida.")
        sys.exit(1)

    # Validar si existe el archivo
    ruta = Path(EXPLOTACION_BASE_DIR, quincena, CUENTAS_FILENAME_XLS)
    if not ruta.exists():
        click.echo(f"ERROR: {str(ruta)} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        click.echo(f"ERROR: {str(ruta)} no es un archivo.")
        sys.exit(1)

    # Abrir el archivo XLS con xlrd
    libro = xlrd.open_workbook(str(ruta))

    # Obtener la primera hoja
    hoja = libro.sheet_by_index(0)

    # Iniciar contador de cuentas alimentadas
    contador = 0
    bancos_que_no_existen = []
    personas_que_no_existen = []

    # Bucle por cada fila
    click.echo("Alimentando Cuentas:", nl=False)
    for fila in range(1, hoja.nrows):
        # Tomar las columnas
        rfc = hoja.cell_value(fila, 0)
        bco_admdor = str(int(hoja.cell_value(fila, 23)))  # Tiene 5 y 10
        emp_cta_bancaria = str(int(hoja.cell_value(fila, 22)))

        # Revisar si el banco existe
        banco = Banco.query.filter_by(clave=bco_admdor).first()
        if banco is None:
            bancos_que_no_existen.append(f"  No existe el banco {bco_admdor}")
            continue

        # Revisar si la persona existe
        persona = Persona.query.filter_by(rfc=rfc).first()
        if persona is None:
            personas_que_no_existen.append(f"  No existe la persona con RFC '{rfc}'")
            continue

        # Bucle por las cuentas de la persona
        tiene_cuenta = False
        contador_cuentas_bajas = 0
        for cuentas in persona.cuentas:
            # Se saltan las cuentas eliminadas
            if cuentas.estatus == "B":
                continue
            # Se salta la cuenta del banco con clave 9 que es PREVIVALE
            if cuentas.banco.clave == "9":
                continue
            # Si el banco y la cuenta son iguales, se salta
            if cuentas.banco.clave == bco_admdor and cuentas.num_cuenta == emp_cta_bancaria:
                tiene_cuenta = True
                continue
            # Entonces se elimina la cuenta porque se va a agregar una nueva mas adelante
            cuentas.estatus = "B"
            sesion.add(cuentas)
            contador_cuentas_bajas += 1

        # Si tiene_cuenta es verdadero, se salta
        if tiene_cuenta:
            continue

        # Alimentar la cuenta
        cuenta = Cuenta(
            persona_id=persona.id,
            banco_id=banco.id,
            num_cuenta=emp_cta_bancaria,
        )
        sesion.add(cuenta)

        # Incrementar contador
        contador += 1
        if contador % 100 == 0:
            click.echo(click.style(".", fg="cyan"), nl=False)

    # Poner avance de linea
    click.echo("")

    # Cerrar la sesion para que se guarden todos los datos en la base de datos
    sesion.commit()
    sesion.close()

    # Si hubo bancos que no existen, se muestra el mensaje
    if len(bancos_que_no_existen) > 0:
        for mensaje in bancos_que_no_existen:
            click.echo(click.style(mensaje, fg="yellow"))

    # Si hubo personas que no existen, se muestra el mensaje
    if len(personas_que_no_existen) > 0:
        for mensaje in personas_que_no_existen:
            click.echo(click.style(mensaje, fg="yellow"))

    # Mensaje termino
    click.echo(click.style(f"  Cuentas bancarias: {contador} alimentadas.", fg="green"))


@click.command()
@click.argument("quincena", type=str)
def alimentar_monederos(quincena: str):
    """Alimentar cuentas monederos"""

    # Iniciar sesion con la base de datos para que la alimentacion sea rapida
    sesion = database.session

    # Validar quincena
    if re.match(QUINCENA_REGEXP, quincena) is None:
        click.echo("ERROR: Quincena inválida")
        sys.exit(1)

    # Validar el directorio donde espera encontrar los archivos de explotacion
    if EXPLOTACION_BASE_DIR is None:
        click.echo("ERROR: Variable de entorno EXPLOTACION_BASE_DIR no definida.")
        sys.exit(1)

    # Validar si existe el archivo
    ruta = Path(EXPLOTACION_BASE_DIR, quincena, MONEDEROS_FILENAME_XLS)
    if not ruta.exists():
        click.echo(f"ERROR: {str(ruta)} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        click.echo(f"ERROR: {str(ruta)} no es un archivo.")
        sys.exit(1)

    # Consultar el banco con clave 9 que es PREVIVALE
    banco = Banco.query.filter_by(clave="9").first()
    if banco is None:
        click.echo("ERROR: No existe el banco con clave 9")
        sys.exit(1)

    # Abrir el archivo XLS con xlrd
    libro = xlrd.open_workbook(str(ruta))

    # Obtener la primera hoja
    hoja = libro.sheet_by_index(0)

    # Iniciar contador de monederos alimentadas
    contador_nuevas = 0
    contador_bajas = 0
    contador_num_tarjeta_invalido = 0
    personas_que_no_existen = []

    # Bucle por cada fila
    click.echo("Alimentando Monederos: ", nl=False)
    for fila in range(1, hoja.nrows):
        # Tomar las columnas
        rfc = str(hoja.cell_value(fila, 1)).strip().upper()
        num_tarjeta = str(hoja.cell_value(fila, 4)).strip()

        # Validar que el num_tarjeta sea de 16 digitos, de lo contrario, se pone en 16 ceros
        if re.match(r"^\d{16}$", num_tarjeta) is None:
            contador_num_tarjeta_invalido += 1
            num_tarjeta = "0" * 16

        # Revisar si la persona existe
        persona = Persona.query.filter_by(rfc=rfc).first()
        if persona is None:
            personas_que_no_existen.append(f"  No existe la persona con RFC '{rfc}'")
            continue

        # Consultar las cuentas de la persona, con el banco 9
        cuentas = Cuenta.query.filter_by(persona_id=persona.id).filter_by(banco_id=banco.id).all()

        # Inicializar hay_nueva_cuenta en falso
        hay_que_agregar_cuenta = False

        # Si no tiene cuentas, hay que agregar una cuenta nueva
        if len(cuentas) == 0:
            hay_que_agregar_cuenta = True

        #  De lo contrario, ya tiene cuentas, hay que revisar sus cuentas
        for cuenta in cuentas:
            # Si el num_cuenta es diferente, se le agrega la nueva y se da de baja la anterior
            if cuenta.num_cuenta != num_tarjeta and cuenta.estatus == "A":
                hay_que_agregar_cuenta = True
                cuenta.estatus = "B"
                sesion.add(cuenta)
                contador_bajas += 1

        # Si no hay que agregar una cuenta, se salta
        if not hay_que_agregar_cuenta:
            continue

        # Agregar la cuenta nueva
        cuenta_nueva = Cuenta(
            persona_id=persona.id,
            banco_id=banco.id,
            num_cuenta=num_tarjeta,
        )
        sesion.add(cuenta_nueva)

        # Incrementar contador
        contador_nuevas += 1
        if contador_nuevas % 100 == 0:
            click.echo(click.style(".", fg="cyan"), nl=False)

    # Poner avance de linea
    click.echo("")

    # Cerrar la sesion para que se guarden todos los datos en la base de datos
    sesion.commit()
    sesion.close()

    # Si hubo numeros de tarjeta invalidos, se muestra el mensaje
    if contador_num_tarjeta_invalido > 0:
        click.echo(click.style(f"  Hubo {contador_num_tarjeta_invalido} numeros de tarjeta invalidos", fg="yellow"))

    # Si hubo personas que no existen, se muestra el mensaje
    if len(personas_que_no_existen) > 0:
        for mensaje in personas_que_no_existen:
            click.echo(click.style(mensaje, fg="yellow"))

    # Mensaje termino
    click.echo(click.style(f"  Monederos: {contador_nuevas} nuevos y {contador_bajas} eliminados.", fg="green"))


@click.command()
def agregar_cuentas_faltantes():
    """Agregar cuentas a las personas que no tienen"""

    # Iniciar sesion con la base de datos para que la alimentacion sea rapida
    sesion = database.session

    # Consultar el Banco Santander
    banco = Banco.query.filter_by(clave="5").first()

    # Si no se encuentra el banco, se termina
    if banco is None:
        click.echo("ERROR: No se encontró el banco Santander.")
        sys.exit(1)

    # Consultar las personas activas
    personas = Persona.query.filter_by(estatus="A").all()

    # Si no hay personas, se termina
    if len(personas) == 0:
        click.echo("ERROR: No hay personas.")
        sys.exit(1)

    # Bucle por todas las personas
    contador = 0
    for persona in personas:
        # Consultar las cuentas de la persona
        cuentas = Cuenta.query.filter_by(persona_id=persona.id).all()

        # Tomar la cuenta de la persona que no tenga la clave 9, porque esa clave es la de DESPENSA
        tiene_cuenta_bancaria = False
        for cuenta in cuentas:
            if cuenta.banco.clave != "9" and cuenta.estatus == "A":
                tiene_cuenta_bancaria = True
                break

        # Si la persona no tiene cuenta bancaria, se le agrega una
        if not tiene_cuenta_bancaria:
            # Agregar la cuenta
            cuenta = Cuenta(
                persona=persona,
                banco=banco,
                num_cuenta="8" * 11,
            )
            database.session.add(cuenta)

            # Incrementar contador
            contador += 1

    # Si no hubo que agregar cuentas, se termina
    if contador == 0:
        click.echo("AVISO: No se agregaron cuentas.")
        sys.exit(0)

    # Actualizar
    sesion.commit()

    # Mensaje termino
    click.echo(f"Agregar cuentas faltantes: {contador} cuentas en SANTANDER con ochos")


cli.add_command(alimentar_bancarias)
cli.add_command(alimentar_monederos)
