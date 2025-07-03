"""
CLI Percepciones-Deducciones
"""

import csv
import os
import re
import sys
from pathlib import Path

import click
import xlrd

from lib.fechas import quincena_to_fecha, quinquenio_count
from lib.safe_string import QUINCENA_REGEXP, safe_clave, safe_rfc, safe_string
from perseo.app import create_app
from perseo.blueprints.centros_trabajos.models import CentroTrabajo
from perseo.blueprints.conceptos.models import Concepto
from perseo.blueprints.conceptos_productos.models import ConceptoProducto
from perseo.blueprints.nominas.models import Nomina
from perseo.blueprints.percepciones_deducciones.models import PercepcionDeduccion
from perseo.blueprints.personas.models import Persona
from perseo.blueprints.plazas.models import Plaza
from perseo.blueprints.productos.models import Producto
from perseo.blueprints.puestos.models import Puesto
from perseo.blueprints.quincenas.models import Quincena
from perseo.blueprints.tabuladores.models import Tabulador
from perseo.extensions import database

EXPLOTACION_BASE_DIR = os.getenv("EXPLOTACION_BASE_DIR", "")

AGUINALDOS_FILENAME_XLS = "Aguinaldos.XLS"
APOYOS_FILENAME_XLS = "Apoyos.XLS"
NOMINAS_FILENAME_XLS = "NominaFmt2.XLS"

app = create_app()
app.app_context().push()
database.app = app


@click.group()
def cli():
    """Percepciones-Deducciones"""


@click.command()
@click.argument("quincena_clave", type=str)
@click.option(
    "--tipo", type=click.Choice(["", "SALARIO", "DESPENSA", "AGUINALDO", "APOYO ANUAL", "APOYO DIA DE LA MADRE"]), default=""
)
def alimentar(quincena_clave: str, tipo: str):
    """Alimentar percepciones-deducciones"""

    # Iniciar sesión con la base de datos para que la alimentación sea rápida
    sesion = database.session

    # Validar quincena
    if re.match(QUINCENA_REGEXP, quincena_clave) is None:
        click.echo("ERROR: Quincena inválida")
        sys.exit(1)

    # Si no de especifica el tipo, se alimentan con el tipo SALARIO
    if tipo == "":
        tipo = "SALARIO"

    # Definir la fecha_final en base a la clave de la quincena
    try:
        fecha_final = quincena_to_fecha(quincena_clave, dame_ultimo_dia=True)
    except ValueError:
        click.echo("ERROR: Quincena inválida")
        sys.exit(1)

    # Validar el directorio donde espera encontrar los archivos de explotacion
    if EXPLOTACION_BASE_DIR is None:
        click.echo("ERROR: Variable de entorno EXPLOTACION_BASE_DIR no definida.")
        sys.exit(1)

    # Si el tipo es AGUINALDO, se usara el archivo AGUINALDOS_FILENAME_XLS
    if tipo == "AGUINALDO":
        ruta = Path(EXPLOTACION_BASE_DIR, quincena_clave, AGUINALDOS_FILENAME_XLS)
    else:
        ruta = Path(EXPLOTACION_BASE_DIR, quincena_clave, NOMINAS_FILENAME_XLS)

    # Validar si existe el archivo
    if not ruta.exists():
        click.echo(f"ERROR: {str(ruta)} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        click.echo(f"ERROR: {str(ruta)} no es un archivo.")
        sys.exit(1)

    # Consultar quincena
    quincena = Quincena.query.filter_by(clave=quincena_clave).first()

    # Si existe la quincena, pero no esta ABIERTA, entonces se termina
    if quincena and quincena.estado != "ABIERTA":
        click.echo(f"ERROR: Quincena {quincena_clave} no esta ABIERTA.")
        sys.exit(1)

    # Si existe la quincena, pero ha sido eliminada, entonces se termina
    if quincena and quincena.estatus != "A":
        click.echo(f"ERROR: Quincena {quincena_clave} ha sido eliminada.")
        sys.exit(1)

    # Si no existe la quincena, se agrega
    if quincena is None:
        quincena = Quincena(clave=quincena_clave, estado="ABIERTA")
        sesion.add(quincena)
        sesion.commit()

    # Abrir el archivo XLS con xlrd
    libro = xlrd.open_workbook(str(ruta))

    # Obtener la primera hoja
    hoja = libro.sheet_by_index(0)

    # Iniciar listado de conceptos que no existen
    conceptos_no_existentes = []

    # Definir el puesto genérico al que se van a relacionar las personas que no tengan su puesto
    puesto_generico = Puesto.query.filter_by(clave="ND").first()
    if puesto_generico is None:
        click.echo("ERROR: Falta el puesto con clave ND.")
        sys.exit(1)

    # Definir el tabulador genérico al que se van a relacionar los puestos que no tengan su tabulador
    tabulador_generico = Tabulador.query.filter_by(puesto_id=puesto_generico.id).first()
    if tabulador_generico is None:
        click.echo("ERROR: Falta el tabulador del puesto con clave ND.")
        sys.exit(1)

    # Iniciar contadores
    contador = 0
    centros_trabajos_insertados_contador = 0
    personas_actualizadas_contador = 0
    personas_actualizadas_del_tabulador = []
    personas_actualizadas_del_modelo = []
    personas_actualizadas_del_num_empleado = []
    personas_insertadas_contador = 0
    personas_sin_puestos = []
    personas_sin_tabulador = []
    plazas_insertadas_contador = 0

    # Bucle por cada fila
    click.echo(f"Alimentando Percepciones-Deducciones a la quincena {quincena.clave}: ", nl=False)
    for fila in range(1, hoja.nrows):
        # Tomar las columnas
        centro_trabajo_clave = hoja.cell_value(fila, 1)
        plaza_clave = hoja.cell_value(fila, 8)

        # Tomar las columnas con datos de la Persona
        rfc = hoja.cell_value(fila, 2)
        modelo = int(hoja.cell_value(fila, 236))
        nombre_completo = hoja.cell_value(fila, 3)
        num_empleado = int(hoja.cell_value(fila, 240))

        # Tomar las columnas necesarias para el timbrado
        puesto_clave = safe_clave(hoja.cell_value(fila, 20))
        nivel = int(hoja.cell_value(fila, 9))
        quincena_ingreso = str(int(hoja.cell_value(fila, 19)))

        # Consultar el Centro de Trabajo, si no existe se agrega
        centro_trabajo = CentroTrabajo.query.filter_by(clave=centro_trabajo_clave).first()
        if centro_trabajo is None:
            centro_trabajo = CentroTrabajo(clave=centro_trabajo_clave, descripcion="ND")
            sesion.add(centro_trabajo)
            sesion.commit()
            centros_trabajos_insertados_contador += 1

        # Consultar la Plaza, si no existe se agrega
        plaza = Plaza.query.filter_by(clave=plaza_clave).first()
        if plaza is None:
            plaza = Plaza(clave=plaza_clave, descripcion="ND")
            sesion.add(plaza)
            sesion.commit()
            plazas_insertadas_contador += 1

        # Si el modelo es 2, entonces en SINDICALIZADO y se toman 4 caracteres del puesto
        quinquenios = None
        if modelo == 2:
            puesto_clave = puesto_clave[:4]

            # Inicializar la bandera para saltar la fila si el concepto es PME
            es_concepto_pme = False

            # Bucle entre las columnas de los conceptos para encontrar PQ1, PQ2, PQ3, PQ4, PQ5, PQ6
            col_num = 26
            while True:
                # Tomar el p_o_d
                p_o_d = safe_string(hoja.cell_value(fila, col_num))
                # Tomar el conc
                conc = safe_string(hoja.cell_value(fila, col_num + 1))
                # Si 'P' o 'D' es un texto vacio, se rompe el ciclo
                if p_o_d == "":
                    break
                # Si NO es P, se salta
                if p_o_d != "P":
                    col_num += 6
                    continue
                # Si conc es ME es monedero, se rompe el ciclo porque aqui no hay quinquenios
                if conc == "ME":
                    es_concepto_pme = True
                    break
                # Si el concepto no es PQ1, PQ2, PQ3, PQ4, PQ5, PQ6, se salta
                if conc not in ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6"]:
                    col_num += 6
                    continue
                # Tomar el tercer carácter del concepto y convertirlo a entero porque es la cantidad de quinquenios
                quinquenios = int(conc[1])
                break

            # Si es PME, entonces en esta fila NO esta el quinquenio, se mantiene en None
            if es_concepto_pme:
                quinquenios = None

        else:
            # Entonces NO es SINDICALIZADO, se define quinquenios en cero
            quinquenios = 0

        # Consultar el Puesto, si no existe se agrega a personas_sin_puestos y se le asigna el puesto_generico
        puesto = Puesto.query.filter_by(clave=puesto_clave).first()
        if puesto is None:
            personas_sin_puestos.append(puesto_clave)
            puesto = puesto_generico

        # Consultar la Persona
        persona = Persona.query.filter_by(rfc=rfc).first()

        # Si NO existe la Persona, se agrega
        if persona is None:
            # Separar nombre_completo, en apellido_primero, apellido_segundo y nombres
            separado = safe_string(nombre_completo, save_enie=True).split(" ")
            apellido_primero = separado[0]
            apellido_segundo = separado[1]
            nombres = " ".join(separado[2:])

            # Si el modelo es 2 y quinquenios es None, entonces es SINDICALIZADO y se calculan los quinquenios
            if modelo == 2 and quinquenios is None:
                # Calcular la cantidad de quinquenios
                fecha_ingreso = quincena_to_fecha(quincena_ingreso, dame_ultimo_dia=False)
                quinquenios = quinquenio_count(fecha_ingreso, fecha_final)

            # Consultar el tabulador que coincida con puesto_clave, modelo, nivel y quinquenios
            tabulador = (
                Tabulador.query.filter_by(puesto_id=puesto.id)
                .filter_by(modelo=modelo)
                .filter_by(nivel=nivel)
                .filter_by(quinquenio=quinquenios)
                .first()
            )

            # Si no existe el tabulador, se agrega a personas_sin_tabulador y se le asigna tabulador_generico
            if tabulador is None:
                personas_sin_tabulador.append(rfc)
                tabulador = tabulador_generico

            # Insertar a la Persona
            persona = Persona(
                tabulador_id=tabulador.id,
                rfc=rfc,
                nombres=nombres,
                apellido_primero=apellido_primero,
                apellido_segundo=apellido_segundo,
                modelo=modelo,
                num_empleado=num_empleado,
            )
            sesion.add(persona)
            sesion.commit()
            personas_insertadas_contador += 1

        # De lo contrario, se revisa si cambia la Persona de tabulador, modelo o num_empleado
        else:
            # Inicializar hay_cambios
            hay_cambios = False

            # Si la fila es concepto PME NO va tener los quinquenios, entonces se define con la Persona
            if quinquenios is None:
                quinquenios = persona.tabulador.quinquenio

            # Consultar el tabulador que coincida con puesto_clave, modelo, nivel y quinquenios
            tabulador = (
                Tabulador.query.filter_by(puesto_id=puesto.id)
                .filter_by(modelo=modelo)
                .filter_by(nivel=nivel)
                .filter_by(quinquenio=quinquenios)
                .first()
            )

            # Si NO existe el tabulador, se agrega a personas_sin_tabulador y se le asigna tabulador_generico
            if tabulador is None:
                personas_sin_tabulador.append(rfc)
                tabulador = tabulador_generico

            # Revisar si hay que actualizar el tabulador a la Persona
            if persona.tabulador_id != tabulador.id:
                personas_actualizadas_del_tabulador.append(
                    f"{rfc} {persona.nombre_completo}: Tabulador: {persona.tabulador_id} -> {tabulador.id}"
                )
                persona.tabulador_id = tabulador.id
                hay_cambios = True

            # Revisar si hay que actualizar el modelo a la Persona
            if persona.modelo != modelo:
                personas_actualizadas_del_modelo.append(
                    f"{rfc} {persona.nombre_completo}: Modelo: {persona.modelo} -> {modelo}"
                )
                persona.modelo = modelo
                hay_cambios = True

            # Revisar si hay que actualizar el numero de empleado a la Persona
            if persona.num_empleado != num_empleado:
                personas_actualizadas_del_num_empleado.append(
                    f"{rfc} {persona.nombre_completo}: No. Emp. {persona.num_empleado} -> {num_empleado}"
                )
                persona.num_empleado = num_empleado
                hay_cambios = True

            # Si hay cambios, guardar la Persona
            if hay_cambios:
                persona.save()
                personas_actualizadas_contador += 1

        # Buscar percepciones y deducciones
        percepciones_deducciones_agregadas_contador = 0
        col_num = 26
        while True:
            # Tomar 'P' o 'D', primero
            p_o_d = safe_string(hoja.cell_value(fila, col_num))

            # Si 'P' o 'D' es un texto vacio, se rompe el ciclo
            if p_o_d == "":
                break

            # Tomar los dos caracteres adicionales del concepto
            conc = safe_string(hoja.cell_value(fila, col_num + 1))

            # Tomar el importe
            try:
                impt = int(hoja.cell_value(fila, col_num + 3)) / 100.0
            except ValueError:
                impt = 0.0

            # Revisar si el Concepto existe, de lo contrario se agrega
            concepto_clave = f"{p_o_d}{conc}"
            concepto = Concepto.query.filter_by(clave=concepto_clave).first()
            if concepto is None and concepto_clave not in conceptos_no_existentes:
                conceptos_no_existentes.append(concepto_clave)
                concepto = Concepto(clave=concepto_clave, descripcion="DESCONOCIDO")
                sesion.add(concepto)
                sesion.commit()

            # Alimentar percepcion-deduccion
            percepcion_deduccion = PercepcionDeduccion(
                centro_trabajo=centro_trabajo,
                concepto=concepto,
                persona=persona,
                plaza=plaza,
                quincena=quincena,
                importe=impt,
                tipo=tipo,
            )
            sesion.add(percepcion_deduccion)
            percepciones_deducciones_agregadas_contador += 1

            # Incrementar col_num en SEIS
            col_num += 6

            # Romper el ciclo cuando se llega a la columna
            if col_num > 236:
                break

        # Incrementar contador
        contador += 1

        # Mostrar un cero en rojo si no se agregaron percepciones-deducciones
        if percepciones_deducciones_agregadas_contador == 0:
            click.echo(click.style("0", fg="yellow"), nl=False)
        else:
            click.echo(click.style(".", fg="cyan"), nl=False)

    # Poner avance de linea
    click.echo("")

    # Cerrar la sesion para que se guarden todos los datos en la base de datos
    sesion.commit()
    sesion.close()

    # Si hubo centros trabajos insertados, mostrar contador
    if centros_trabajos_insertados_contador > 0:
        click.echo(click.style(f"  Se insertaron {centros_trabajos_insertados_contador} Centros de Trabajo", fg="green"))

    # Si hubo personas actualizadas, mostrar contador
    if personas_actualizadas_contador > 0:
        click.echo(click.style(f"  Se actualizaron {personas_actualizadas_contador} Personas", fg="green"))
        for item in personas_actualizadas_del_tabulador:
            click.echo(click.style(f"  {item}", fg="yellow"))
        for item in personas_actualizadas_del_modelo:
            click.echo(click.style(f"  {item}", fg="yellow"))
        for item in personas_actualizadas_del_num_empleado:
            click.echo(click.style(f"  {item}", fg="yellow"))

    # Si hubo personas insertadas, mostrar contador
    if personas_insertadas_contador > 0:
        click.echo(click.style(f"  Se insertaron {personas_insertadas_contador} Personas", fg="green"))

    # Si hubo plazas insertadas, mostrar contador
    if plazas_insertadas_contador > 0:
        click.echo(click.style(f"  Se insertaron {plazas_insertadas_contador} Plazas", fg="green"))

    # Si hubo conceptos no existentes, mostrarlos
    if len(conceptos_no_existentes) > 0:
        click.echo(click.style(f"  Hubo {len(conceptos_no_existentes)} Conceptos que no existen:", fg="yellow"))
        click.echo(click.style(f"  {','.join(conceptos_no_existentes)}", fg="yellow"))

    # Si hubo personas sin puestos, mostrarlos
    if personas_insertadas_contador > 0 and len(personas_sin_puestos) > 0:
        click.echo(click.style(f"  Hubo {len(personas_sin_puestos)} Personas sin reconocer su Puesto:", fg="yellow"))
        # click.echo(click.style(f"  {','.join(personas_sin_puestos)}", fg="yellow"))

    # Si hubo personas_sin_tabulador, mostrarlas en pantalla
    if personas_insertadas_contador > 0 and len(personas_sin_tabulador) > 0:
        click.echo(click.style(f"  Hubo {len(personas_sin_tabulador)} Personas sin reconocer su Tabulador.", fg="yellow"))
        # click.echo(click.style(f"  {', '.join(personas_sin_tabulador)}", fg="yellow"))

    # Mensaje termino
    click.echo(click.style(f"  Alimentar Percepciones-Deducciones: {contador} insertadas.", fg="green"))


@click.command()
@click.argument("quincena_clave", type=str)
def alimentar_apoyos_anuales(quincena_clave: str):
    """Alimentar percepciones-deducciones para apoyos anuales"""

    # Validar quincena
    if re.match(QUINCENA_REGEXP, quincena_clave) is None:
        click.echo("ERROR: Quincena inválida.")
        sys.exit(1)

    # Iniciar sesion con la base de datos para que la alimentacion sea rapida
    sesion = database.session

    # Validar el directorio donde espera encontrar los archivos de explotacion
    if EXPLOTACION_BASE_DIR is None:
        click.echo("ERROR: Variable de entorno EXPLOTACION_BASE_DIR no definida.")
        sys.exit(1)

    # Validar si existe el archivo
    ruta = Path(EXPLOTACION_BASE_DIR, quincena_clave, APOYOS_FILENAME_XLS)
    if not ruta.exists():
        click.echo(f"ERROR: {str(ruta)} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        click.echo(f"ERROR: {str(ruta)} no es un archivo.")
        sys.exit(1)

    # Consultar quincena
    quincena = Quincena.query.filter_by(clave=quincena_clave).first()

    # Si existe la quincena, pero no esta ABIERTA, entonces se termina
    if quincena and quincena.estado != "ABIERTA":
        click.echo(f"ERROR: Quincena {quincena_clave} no esta ABIERTA.")
        sys.exit(1)

    # Si existe la quincena, pero ha sido eliminada, entonces se termina
    if quincena and quincena.estatus != "A":
        click.echo(f"ERROR: Quincena {quincena_clave} esta sido eliminada.")
        sys.exit(1)

    # Si no existe la quincena, se agrega
    if quincena is None:
        quincena = Quincena(clave=quincena_clave, estado="ABIERTA")
        sesion.add(quincena)
        sesion.commit()

    # Consultar el concepto con clave PAZ que es APOYO ANUAL, si no se encuentra, error
    concepto_paz = Concepto.query.filter_by(clave="PAZ").first()
    if concepto_paz is None:
        click.echo("ERROR: No existe el concepto con clave PAZ")
        sys.exit(1)

    # Consultar el concepto con clave DAZ que es ISR DE APOYO DE FIN DE AÑO, si no se encuentra, error
    concepto_daz = Concepto.query.filter_by(clave="DAZ").first()
    if concepto_daz is None:
        click.echo("ERROR: No existe el concepto con clave DAZ")
        sys.exit(1)

    # Consultar el concepto con clave D62 que es PENSION ALIMENTICIA, si no se encuentra, error
    concepto_d62 = Concepto.query.filter_by(clave="D62").first()
    if concepto_d62 is None:
        click.echo("ERROR: No existe el concepto con clave D62")
        sys.exit(1)

    # Abrir el archivo XLS con xlrd
    libro = xlrd.open_workbook(str(ruta))

    # Obtener la primera hoja
    hoja = libro.sheet_by_index(0)

    # Iniciar contadores
    contador = 0
    centros_trabajos_inexistentes = []
    nominas_inexistentes = []
    personas_inexistentes = []
    plazas_inexistentes = []

    # Bucle por cada fila
    click.echo("Alimentando Nominas de Apoyos Anuales: ", nl=False)
    for fila in range(1, hoja.nrows):
        # Tomar las columnas
        rfc = hoja.cell_value(fila, 0).strip().upper()
        centro_trabajo_clave = hoja.cell_value(fila, 1).strip().upper()
        plaza_clave = hoja.cell_value(fila, 2).strip().upper()
        percepcion = float(hoja.cell_value(fila, 4))
        deduccion = float(hoja.cell_value(fila, 5))
        impte = float(hoja.cell_value(fila, 6))

        # Tomar el importe del concepto D62, si no esta presente sera cero
        try:
            impte_concepto_d62 = float(hoja.cell_value(fila, 10))
        except ValueError:
            impte_concepto_d62 = 0.0

        # Consultar la persona
        persona = Persona.query.filter_by(rfc=rfc).first()

        # Si NO existe, se agrega a la lista de personas_inexistentes y se salta
        if persona is None:
            personas_inexistentes.append(rfc)
            continue

        # Consultar el Centro de Trabajo
        centro_trabajo = CentroTrabajo.query.filter_by(clave=centro_trabajo_clave).first()

        # Si NO existe se agrega a la lista de centros_trabajos_inexistentes y se salta
        if centro_trabajo is None:
            centros_trabajos_inexistentes.append(centro_trabajo_clave)
            continue

        # Consultar la Plaza
        plaza = Plaza.query.filter_by(clave=plaza_clave).first()

        # Si NO existe se agrega a la lista de plazas_inexistentes y se salta
        if plaza is None:
            plazas_inexistentes.append(plaza_clave)
            continue

        # Consultar la nomina de la quincena, de la persona y que sea de tipo APOYO ANUAL
        nomina = (
            Nomina.query.filter_by(persona_id=persona.id)
            .filter_by(quincena_id=quincena.id)
            .filter_by(tipo="APOYO ANUAL")
            .filter_by(estatus="A")
            .first()
        )

        # Si NO existe, se agrega a la lista de nominas_inexistentes y se salta
        if nomina is None:
            nominas_inexistentes.append(rfc)
            continue

        # Alimentar percepcion en PercepcionDeduccion, con concepto PAZ
        percepcion_deduccion_paz = PercepcionDeduccion(
            centro_trabajo=centro_trabajo,
            concepto=concepto_paz,
            persona=persona,
            plaza=plaza,
            quincena=quincena,
            importe=percepcion,
            tipo="APOYO ANUAL",
        )
        sesion.add(percepcion_deduccion_paz)

        # Alimentar deduccion en PercepcionDeduccion, con concepto DAZ
        percepcion_deduccion_daz = PercepcionDeduccion(
            centro_trabajo=centro_trabajo,
            concepto=concepto_daz,
            persona=persona,
            plaza=plaza,
            quincena=quincena,
            importe=deduccion,
            tipo="APOYO ANUAL",
        )
        sesion.add(percepcion_deduccion_daz)

        # Si tiene concepto_d62, alimentar registro en PercepcionDeduccion
        if impte_concepto_d62 > 0:
            percepcion_deduccion_d62 = PercepcionDeduccion(
                centro_trabajo=centro_trabajo,
                concepto=concepto_d62,
                persona=persona,
                plaza=plaza,
                quincena=quincena,
                importe=impte_concepto_d62,
                tipo="APOYO ANUAL",
            )
            sesion.add(percepcion_deduccion_d62)

            # Sumar a deduccion el impte_concepto_d62
            deduccion += impte_concepto_d62

        # Actualizar el registro en Nominas con percepcion, deducción e importe
        if nomina.percepcion != percepcion or nomina.deduccion != deduccion or nomina.importe != impte:
            nomina.percepcion = percepcion
            nomina.deduccion = deduccion
            nomina.importe = impte
            sesion.add(nomina)

        # Incrementar contador
        contador += 1
        click.echo(click.style(".", fg="cyan"), nl=False)

    # Poner avance de linea
    click.echo("")

    # Si contador es cero, mostrar mensaje de error y terminar
    if contador == 0:
        click.echo(click.style("ERROR: No se alimentaron registros en nominas.", fg="red"))
        sys.exit(1)

    # Cerrar la sesion para que se guarden todos los datos en la base de datos
    sesion.commit()
    sesion.close()

    # Si hubo centros_trabajos_inexistentes, mostrarlos
    if len(centros_trabajos_inexistentes) > 0:
        click.echo(click.style(f"  Hubo {len(centros_trabajos_inexistentes)} C. de T. que no existen:", fg="yellow"))
        click.echo(click.style(f"  {', '.join(centros_trabajos_inexistentes)}", fg="yellow"))

    # Si hubo plazas_inexistentes, mostrarlos
    if len(plazas_inexistentes) > 0:
        click.echo(click.style(f"  Hubo {len(plazas_inexistentes)} Plazas que no existen:", fg="yellow"))
        click.echo(click.style(f"  {', '.join(plazas_inexistentes)}", fg="yellow"))

    # Si hubo personas_inexistentes, mostrar contador
    if len(personas_inexistentes) > 0:
        click.echo(click.style(f"  Hubo {len(personas_inexistentes)} Personas que no existen:", fg="yellow"))
        click.echo(click.style(f"  {', '.join(personas_inexistentes)}", fg="yellow"))

    # Si hubo nominas_inexistentes, mostrarlas
    if len(nominas_inexistentes) > 0:
        click.echo(click.style(f"  Hubo {len(nominas_inexistentes)} Nominas de tipo APOYO ANUAL que no existen:", fg="yellow"))
        click.echo(click.style(f"  {', '.join(nominas_inexistentes)}", fg="yellow"))

    # Mensaje termino
    click.echo(click.style(f"  Alimentar P-D Apoyos Anuales: {contador} insertadas.", fg="green"))


@click.command()
@click.argument("archivo_csv", type=click.Path(exists=True))
def inyectar(archivo_csv):
    """Inyectar registros en P-D a partir de un archivo CSV"""

    # Validar que el archivo sea CSV
    archivo_csv = Path(archivo_csv)
    if archivo_csv.exists() and archivo_csv.suffix != ".csv":
        click.echo("ERROR: El archivo no existe o no es CSV.")
        sys.exit(1)

    # Iniciar contadores
    contador_p_d_actualizados = 0
    contador_p_d_insertados = 0

    # Leer el archivo CSV
    click.echo("Inyectando Percepciones-Deducciones: ", nl=False)
    with open(archivo_csv, newline="", encoding="utf8") as csvfile:
        # Para evitar que se carguen registros y se interrumpa por un error, se inicializa un listado de datos
        datos = []

        # Bucle por cada fila
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Tomar las columnas rfc, centro de trabajo, plaza, quincena, tipo, concepto, concepto descripcion, importe
            try:
                rfc = safe_rfc(row["rfc"])
                centro_trabajo_clave = safe_clave(row["centro de trabajo"])
                plaza_clave = safe_clave(row["plaza"], max_len=24)
                quincena_clave = safe_clave(row["quincena"])
                tipo = safe_string(row["tipo"])
                concepto_clave = safe_clave(row["concepto"])
                importe = float(row["importe"])
            except (KeyError, ValueError):
                click.echo("ERROR: Columnas no encontradas.")
                sys.exit(1)

            # Consultar la persona por su rfc
            persona = Persona.query.filter_by(rfc=rfc).first()
            if persona is None:
                click.echo(click.style(f"ERROR: No existe la persona con rfc {rfc}", fg="red"))
                sys.exit(1)

            # Consultar el centro de trabajo por su clave
            centro_trabajo = CentroTrabajo.query.filter_by(clave=centro_trabajo_clave).first()
            if centro_trabajo is None:
                click.echo(click.style(f"ERROR: No existe el centro de trabajo con clave {centro_trabajo_clave}", fg="red"))
                sys.exit(1)

            # Consultar la plaza por su clave
            plaza = Plaza.query.filter_by(clave=plaza_clave).first()
            if plaza is None:
                click.echo(click.style(f"ERROR: No existe la plaza con clave {plaza_clave}", fg="red"))
                sys.exit(1)

            # Consultar la quincena por su clave
            quincena = Quincena.query.filter_by(clave=quincena_clave).first()
            if quincena is None:
                click.echo(click.style(f"ERROR: No existe la quincena con clave {quincena_clave}", fg="red"))
                sys.exit(1)

            # Validar el tipo
            if tipo not in PercepcionDeduccion.TIPOS:
                click.echo(click.style(f"ERROR: Tipo no reconocido {tipo}", fg="red"))
                sys.exit(1)

            # Consultar el concepto por su clave
            concepto = Concepto.query.filter_by(clave=concepto_clave).first()
            if concepto is None:
                click.echo(click.style(f"ERROR: No existe el concepto con clave {concepto_clave}", fg="red"))
                sys.exit(1)

            # Acumular en el listado de datos
            datos.append(
                {
                    "centro_trabajo": centro_trabajo,
                    "concepto": concepto,
                    "importe": importe,
                    "persona": persona,
                    "plaza": plaza,
                    "quincena": quincena,
                    "tipo": tipo,
                }
            )

        # Bucle por cada dato
        for dato in datos:
            # Consultar el registro en PercepcionDeduccion
            p_d = (
                PercepcionDeduccion.query.filter_by(centro_trabajo_id=dato["centro_trabajo"].id)
                .filter_by(concepto_id=dato["concepto"].id)
                .filter_by(persona_id=dato["persona"].id)
                .filter_by(plaza_id=dato["plaza"].id)
                .filter_by(quincena_id=dato["quincena"].id)
                .filter_by(tipo=dato["tipo"])
                .first()
            )

            # Si existe el registros...
            if p_d is not None:
                # Si el importe es diferente, se actualiza
                if p_d.importe != dato["importe"]:
                    p_d.importe = dato["importe"]
                    p_d.save()
                    contador_p_d_actualizados += 1
                    click.echo(click.style("u", fg="cyan"), nl=False)
            # De lo contrario, se agrega
            else:
                p_d = PercepcionDeduccion(
                    centro_trabajo=dato["centro_trabajo"],
                    concepto=dato["concepto"],
                    importe=dato["importe"],
                    persona=dato["persona"],
                    plaza=dato["plaza"],
                    quincena=dato["quincena"],
                    tipo=dato["tipo"],
                )
                p_d.save()
                contador_p_d_insertados += 1
                click.echo(click.style("+", fg="green"), nl=False)

    # Poner avance de linea
    click.echo("")

    # Mostrar el contador de registros actualizados
    if contador_p_d_actualizados > 0:
        click.echo(click.style(f"  Se actualizaron {contador_p_d_actualizados} registros.", fg="green"))

    # Mostrar el contador de registros insertados
    if contador_p_d_insertados > 0:
        click.echo(click.style(f"  Se insertaron {contador_p_d_insertados} registros.", fg="green"))


@click.command()
def corregir_concepto_d62_a_d62m():
    """Corregir el concepto D62 a D62M"""

    # Consultar el concepto con clave D62
    concepto_d62 = Concepto.query.filter_by(clave="D62").first()
    if concepto_d62 is None:
        click.echo("ERROR: No existe el concepto con clave D62.")
        sys.exit(1)

    # Consultar el concepto con clave D62M
    concepto_d62m = Concepto.query.filter_by(clave="D62M").first()
    if concepto_d62m is None:
        click.echo("ERROR: No existe el concepto con clave D62M.")
        sys.exit(1)

    # Consultar las quincenas activas ordenadas por la clave
    quincenas = Quincena.query.filter_by(estatus="A").order_by(Quincena.clave).all()

    # Si no hay quincenas, mostrar mensaje y terminar
    if len(quincenas) == 0:
        click.echo("ERROR: No hay quincenas abiertas.")
        sys.exit(1)

    # Inicializar contadores
    correcciones_contador = 0
    errores_contador = 0

    # Bucle por cada quincena
    for quincena in quincenas:
        # Mostrar la clave de la quincena
        click.echo(f"  Corrigiendo la quincena {quincena.clave}: ", nl=False)

        # Consultar los registros en PercepcionesDeducciones con concepto D62M
        p_d_d62m = (
            PercepcionDeduccion.query.filter_by(concepto_id=concepto_d62m.id)
            .filter_by(quincena_id=quincena.id)
            .filter_by(tipo="SALARIO")
            .filter_by(estatus="A")
            .all()
        )

        # Si hay registros, se omite esta quincena porque ya esta corregida
        if len(p_d_d62m) > 0:
            # Mostrar un OK en verde con avance de linea y omitir
            click.echo(click.style("OK", fg="green"))
            continue

        # Consultar los registros en PercepcionesDeducciones con concepto D62 ordenados por persona_id
        p_d_d62 = (
            PercepcionDeduccion.query.filter_by(concepto_id=concepto_d62.id)
            .filter_by(quincena_id=quincena.id)
            .filter_by(tipo="SALARIO")
            .filter_by(estatus="A")
            .order_by(PercepcionDeduccion.persona_id, PercepcionDeduccion.importe)
            .all()
        )

        # Si no hay registros, se omite esta quincena
        if len(p_d_d62) == 0:
            # Mostrar un Sin D62 en amarillo con avance de linea y omitir
            click.echo(click.style("Sin D62", fg="yellow"))
            continue

        # Bucle para cada registro
        persona_id_anterior = None
        p_d_d62_anterior = None
        contador = 0
        for p_d in p_d_d62:
            # Si es el primero en revisar o si ha cambiado la persona, se recuerda y se omite
            if persona_id_anterior is None or p_d_d62_anterior is None or p_d.persona_id != persona_id_anterior:
                persona_id_anterior = p_d.persona_id
                p_d_d62_anterior = p_d
                contador = 0
                continue

            # Incrementar el contador
            contador += 1

            # Si contador es mayor a uno (no es 1)
            if contador > 1:
                errores_contador += 1
                # Mostrar una letra e en color amarillo
                click.echo(click.style("e", fg="yellow"), nl=False)
                continue

            # Cambiar el concepto del registro anterior a D62M
            p_d_d62_anterior.concepto_id = concepto_d62m.id

            # Guardar el registro anterior
            p_d_d62_anterior.save()

            # Mostrar una letra u en color cyan
            click.echo(click.style("u", fg="cyan"), nl=False)

            # Incrementar el contador
            correcciones_contador += 1

        # Poner avance de linea
        click.echo("")

    # Si hubo errores, mostrar mensaje
    if errores_contador > 0:
        click.echo(click.style(f"  Hubo {errores_contador} casos donde habia mas de dos D62.", fg="yellow"))

    # Mensaje termino
    click.echo(click.style(f"  Se corrigieron {correcciones_contador} p_d.", fg="green"))


cli.add_command(alimentar)
cli.add_command(alimentar_apoyos_anuales)
cli.add_command(inyectar)
cli.add_command(corregir_concepto_d62_a_d62m)
