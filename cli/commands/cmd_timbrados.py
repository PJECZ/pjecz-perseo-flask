"""
CLI Timbrados
"""

import csv
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import click
import pytz
from dotenv import load_dotenv
from openpyxl import Workbook
from sqlalchemy.exc import MultipleResultsFound, NoResultFound

from pjecz_perseo_flask.blueprints.nominas.models import Nomina
from pjecz_perseo_flask.blueprints.personas.models import Persona
from pjecz_perseo_flask.blueprints.quincenas.models import Quincena
from pjecz_perseo_flask.blueprints.timbrados.models import Timbrado
from pjecz_perseo_flask.blueprints.timbrados.tasks import exportar_xlsx as task_exportar_xlsx
from pjecz_perseo_flask.lib.google_cloud_storage import (
    check_file_exists_from_gcs,
    get_file_from_gcs,
    get_public_url_from_gcs,
    upload_file_to_gcs,
)
from pjecz_perseo_flask.lib.safe_string import QUINCENA_REGEXP, RFC_REGEXP, safe_string
from pjecz_perseo_flask.main import app

TIMEZONE = "America/Mexico_City"

CARPETA = "timbrados"
XML_TAG_CFD_PREFIX = "{http://www.sat.gob.mx/cfd/4}"
XML_TAG_TFD_PREFIX = "{http://www.sat.gob.mx/TimbreFiscalDigital}"
XML_TAG_NOMINA_PREFIX = "{http://www.sat.gob.mx/nomina12}"

GCS_TIMBRADOS_URL_BASE = "https://storage.googleapis.com/pjecz-consultas/timbrados"

load_dotenv()

CFDI_EMISOR_RFC = os.getenv("CFDI_EMISOR_RFC", "")
CFDI_EMISOR_NOMBRE = os.getenv("CFDI_EMISOR_NOMBRE", "")
CFDI_EMISOR_REGFIS = os.getenv("CFDI_EMISOR_REGFIS", "")
CLOUD_STORAGE_DEPOSITO = os.getenv("CLOUD_STORAGE_DEPOSITO", "")
TIMBRADOS_BASE_DIR = os.getenv("TIMBRADOS_BASE_DIR", "")

# Inicializar el contexto de la aplicación Flask
app.app_context().push()


@click.group()
def cli():
    """Timbrados"""


@click.command()
@click.argument("quincena_clave", type=str)
@click.option("--tipo", type=str, default="SALARIO")
@click.option("--desde-clave", type=str, default="")
@click.option("--hasta-clave", type=str, default="")
@click.option("--poner_en_ceros", is_flag=True, default=False, help="Poner en ceros el campo timbrado_id")
@click.option("--sobreescribir", is_flag=True, default=False, help="Sin importar el valor de timbrado_id")
@click.option("--subdir", type=str, default=None)
def actualizar(
    quincena_clave: str, tipo: str, desde_clave: str, hasta_clave: str, poner_en_ceros: bool, sobreescribir: bool, subdir: str
):
    """Actualizar los timbrados de una quincena a partir de archivos XML y PDF"""

    # Validar el directorio donde espera encontrar los archivos de explotacion
    if TIMBRADOS_BASE_DIR == "":
        click.echo("ERROR: Variable de entorno TIMBRADOS_BASE_DIR no definida.")
        sys.exit(1)

    # Validar quincena
    if re.match(QUINCENA_REGEXP, quincena_clave) is None:
        click.echo("ERROR: Quincena inválida.")
        sys.exit(1)

    # Validar tipo
    tipo = safe_string(tipo)
    if tipo not in Nomina.TIPOS:
        click.echo("ERROR: Tipo inválido.")
        sys.exit(1)

    # Por defecto, el directorio es <quincena_clave>
    directorio = quincena_clave
    archivo_sufijo = ""

    # Si el tipo es AGUINALDO, el directorio es <quincena_clave>Aguinaldo
    if tipo == "AGUINALDO":
        directorio = f"{quincena_clave}Aguinaldos"
        archivo_sufijo = "aguinaldo"

    # Si el tipo es APOYO ANUAL, el directorio es <quincena_clave>ApoyoAnual
    if tipo == "APOYO ANUAL":
        directorio = f"{quincena_clave}ApoyosAnuales"
        archivo_sufijo = "apoyo-anual"

    # Si el tipo es "APOYO DIA DE LA MADRE", el directorio es <quincena_clave>ApoyoAnual
    if tipo == "APOYO DIA DE LA MADRE":
        directorio = f"{quincena_clave}ApoyosDiaDeLaMadre"
        archivo_sufijo = "apoyo-dia-de-la-madre"

    # Si el tipo es AGUINALDO, el directorio es <quincena_clave>Aguinaldo
    if tipo == "PRIMA VACACIONAL":
        directorio = f"{quincena_clave}PrimasVacacionales"
        archivo_sufijo = "prima-vacacional"

    # Validar que exista el directorio
    if subdir == "":
        timbrados_dir = Path(TIMBRADOS_BASE_DIR, directorio)
    else:
        timbrados_dir = Path(TIMBRADOS_BASE_DIR, directorio, subdir)
    if not timbrados_dir.exists():
        click.echo(f"ERROR: No existe el directorio {timbrados_dir}")
        sys.exit(1)

    # Si se pide poner_en_ceros los timbrado_id
    if poner_en_ceros:
        click.echo(f"Poner a cero el campo timbrado_id de TODAS las nominas {quincena_clave} y {tipo}: ", nl=False)
        nominas = (
            Nomina.query.join(Quincena)
            .filter(Quincena.clave == quincena_clave)
            .filter(Nomina.tipo == tipo)
            .filter(Nomina.estatus == "A")
            .all()
        )
        for nomina in nominas:
            if nomina.timbrado_id != 0:
                nomina.timbrado_id = 0
                nomina.save()
                click.echo(click.style("u", fg="green"), nl=False)
        click.echo("")

    # Inicializar listas de errores
    archivos_pdf_no_encontrados = []
    emisor_rfc_no_coincide = []
    emisor_nombre_no_coincide = []
    emisor_regfis_no_coincide = []
    nomina_total_percepciones_no_encontrado = []
    nomina_total_deducciones_no_encontrado = []
    receptor_rfc_no_encontrado = []
    receptor_rfc_no_coincide = []
    nomina_no_encontrada = []
    timbrados_sin_nominas = []

    # Inicializar contadores
    actualizados_contador = 0
    agregados_contador = 0
    errores_cargas_xml_contador = 0
    errores_cargas_pdf_contador = 0
    errores_xml = 0
    procesados_contador = 0

    # Recorrer los archivos con extension xml
    click.echo(f"Actualizar los timbrados de las nominas {quincena_clave} y {tipo}: ", nl=False)
    for archivo in timbrados_dir.glob("*.xml"):
        # Obtener el nombre del archivo
        archivo_nombre = archivo.name
        # click.echo(f"  {archivo_nombre}")

        # Definir ruta al archivo XML
        ruta_xml = Path(timbrados_dir, archivo_nombre)

        # Definir ruta al archivo PDF
        ruta_pdf = Path(timbrados_dir, archivo_nombre.replace(".xml", ".pdf"))

        # Si no existe el archivo PDF, se agrega a la lista de errores y se omite
        if not ruta_pdf.is_file:
            archivos_pdf_no_encontrados.append(archivo_nombre)
            continue

        # Obtener el RFC que esta en los primeros 13 caracteres del nombre del archivo
        rfc_en_nombre = archivo_nombre[:13]

        # Parsear el archivo XML
        tree = ET.parse(ruta_xml)
        root = tree.getroot()

        # Estructura del CFDI version 4.0
        # - cfdi:Comprobante [xmlns:xsi, xmlns:nomina12, xmlns:cfdi, Version, Serie, Folio, Fecha, SubTotal, Descuento, Moneda,
        #     Total, TipoDeComprobante, Exportacion, MetodoPago, LugarExpedicion, Sello, Certificado, NoCertificado]
        #   - cfdi:Emisor [Rfc, Nombre, RegimenFiscal]
        #   - cfdi:Receptor [Rfc, Nombre, DomicilioFiscalReceptor, RegimenFiscalReceptor, UsoCFDI]
        #   - cfdi:Conceptos
        #     - cfdi:Concepto [ClaveProdServ, Cantidad, ClaveUnidad, Descripcion, ValorUnitario, Importe, Descuento, ObjetoImp]
        #   - cfdi:Complemento
        #     - tfd:TimbreFiscalDigital [Version, UUID, FechaTimbrado, RfcProvCertif, SelloCFD, NoCertificadoSAT, SelloSAT]
        #     - nomina12:Nomina [Version, TipoNomina, FechaPago, FechaInicialPago, FechaFinalPago, NumDiasPagados,
        #         TotalPercepciones, TotalDeducciones, TotalOtrosPagos]
        #       - nomina12:Emisor [RegistroPatronal]
        #         - nomina12:EntidadSNCF [OrigenRecurso]
        #       - nomina12:Receptor [Curp, NumSeguridadSocial, FechaInicioRelLaboral, Antigüedad, TipoContrato, Sindicalizado,
        #           TipoJornada, TipoRegimen, NumEmpleado, Departamento, Puesto, RiesgoPuesto, PeriodicidadPago, Banco,
        #           CuentaBancaria, SalarioBaseCotApor, SalarioDiarioIntegrado, ClaveEntFed]
        #       - nomina12:Percepciones [TotalSueldos, TotalGravado, TotalExento]
        #         - nomina12:Percepcion [TipoPercepcion, Clave, Concepto, ImporteGravado, ImporteExento]
        #       - nomina12:Deducciones [TotalOtrasDeducciones]
        #         - nomina12:Deduccion [TipoDeduccion, Clave, Concepto, Importe]
        #       - nomina12:OtrosPagos
        #         - nomina12:OtroPago [TipoOtroPago, Clave, Concepto, Importe]

        # Validar que el tag raiz sea cfdi:Comprobante
        if root.tag != f"{XML_TAG_CFD_PREFIX}Comprobante":
            errores_xml += 1
            continue

        # Obtener datos de cfdi:Comprobante
        # cfdi_comprobante_version = None
        # if "Version" in root.attrib:
        #     cfdi_comprobante_version = root.attrib["Version"]
        # click.echo(click.style(f"    Version: {cfdi_comprobante_version}", fg="green"))
        # cfdi_comprobante_serie = None
        # if "Serie" in root.attrib:
        #     cfdi_comprobante_serie = root.attrib["Serie"]
        # click.echo(click.style(f"    Serie: {cfdi_comprobante_serie}", fg="green"))
        # cfdi_comprobante_folio = None
        # if "Folio" in root.attrib:
        #     cfdi_comprobante_folio = root.attrib["Folio"]
        # click.echo(click.style(f"    Folio: {cfdi_comprobante_folio}", fg="green"))
        # cfdi_comprobante_fecha = None
        # if "Fecha" in root.attrib:
        #     cfdi_comprobante_fecha = root.attrib["Fecha"]
        # click.echo(click.style(f"    Fecha: {cfdi_comprobante_fecha}", fg="green"))

        # Inicializar variables de los datos que se van a obtener
        cfdi_emisor_rfc = None  # cfdi:Emisor [Rfc]
        cfdi_emisor_nombre = None  # cfdi:Emisor [Nombre]
        cfdi_emisor_regimen_fiscal = None  # cfdi:Emisor [RegimenFiscal]
        cfdi_receptor_rfc = None  # cfdi:Receptor [Rfc]
        cfdi_receptor_nombre = None  # cfdi:Receptor [Nombre]
        tfd_version = None  # tfd:TimbreFiscalDigital [Version]
        tfd_uuid = None  # tfd:TimbreFiscalDigital [UUID]
        tfd_fecha_timbrado = None  # tfd:TimbreFiscalDigital [FechaTimbrado]
        tfd_sello_cfd = None  # tfd:TimbreFiscalDigital [SelloCFD]
        tfd_num_cert_sat = None  # tfd:TimbreFiscalDigital [NoCertificadoSAT]
        tfd_sello_sat = None  # tfd:TimbreFiscalDigital [SelloSAT]
        nomina12_nomina_version = None  # nomina12:Nomina [Version]
        nomina12_nomina_tipo_nomina = None  # nomina12:Nomina [TipoNomina]
        nomina12_nomina_fecha_pago = None  # nomina12:Nomina [FechaPago]
        nomina12_nomina_fecha_inicial_pago = None  # nomina12:Nomina [FechaInicialPago]
        nomina12_nomina_fecha_final_pago = None  # nomina12:Nomina [FechaFinalPago]
        nomina12_nomina_total_percepciones = None  # nomina12:Nomina [TotalPercepciones]
        nomina12_nomina_total_deducciones = None  # nomina12:Nomina [TotalDeducciones]
        nomina12_nomina_total_otros_pagos = None  # nomina12:Nomina [TotalOtrosPagos]

        # Bucle por los elementos de root
        for element in root.iter():
            # Mostrar el tag
            # click.echo(click.style(f"    {element.tag}", fg="blue"))

            # Obtener datos de Emisor
            if element.tag == f"{XML_TAG_CFD_PREFIX}Emisor":
                if "Rfc" in element.attrib:
                    cfdi_emisor_rfc = element.attrib["Rfc"]
                if "Nombre" in element.attrib:
                    cfdi_emisor_nombre = element.attrib["Nombre"]
                if "RegimenFiscal" in element.attrib:
                    cfdi_emisor_regimen_fiscal = element.attrib["RegimenFiscal"]

            # Obtener datos de Receptor
            if element.tag == f"{XML_TAG_CFD_PREFIX}Receptor":
                if "Rfc" in element.attrib:
                    cfdi_receptor_rfc = element.attrib["Rfc"]
                if "Nombre" in element.attrib:
                    cfdi_receptor_nombre = element.attrib["Nombre"]

            # Obtener datos de TimbreFiscalDigital
            if element.tag == f"{XML_TAG_TFD_PREFIX}TimbreFiscalDigital":
                if "Version" in element.attrib:
                    tfd_version = element.attrib["Version"]
                if "UUID" in element.attrib:
                    tfd_uuid = element.attrib["UUID"]
                if "FechaTimbrado" in element.attrib:
                    tfd_fecha_timbrado = element.attrib["FechaTimbrado"]
                if "SelloCFD" in element.attrib:
                    tfd_sello_cfd = element.attrib["SelloCFD"]
                if "NoCertificadoSAT" in element.attrib:
                    tfd_num_cert_sat = element.attrib["NoCertificadoSAT"]
                if "SelloSAT" in element.attrib:
                    tfd_sello_sat = element.attrib["SelloSAT"]

            # Obtener datos de Nomina
            if element.tag == f"{XML_TAG_NOMINA_PREFIX}Nomina":
                if "Version" in element.attrib:
                    nomina12_nomina_version = element.attrib["Version"]
                if "TipoNomina" in element.attrib:
                    nomina12_nomina_tipo_nomina = element.attrib["TipoNomina"]
                if "FechaPago" in element.attrib:
                    try:
                        nomina12_nomina_fecha_pago = datetime.strptime(element.attrib["FechaPago"], "%Y-%m-%d").date()
                    except ValueError:
                        nomina12_nomina_fecha_pago = None
                if "FechaInicialPago" in element.attrib:
                    try:
                        nomina12_nomina_fecha_inicial_pago = datetime.strptime(
                            element.attrib["FechaInicialPago"], "%Y-%m-%d"
                        ).date()
                    except ValueError:
                        nomina12_nomina_fecha_inicial_pago = None
                if "FechaFinalPago" in element.attrib:
                    try:
                        nomina12_nomina_fecha_final_pago = datetime.strptime(
                            element.attrib["FechaFinalPago"], "%Y-%m-%d"
                        ).date()
                    except ValueError:
                        nomina12_nomina_fecha_final_pago = None
                if "TotalPercepciones" in element.attrib:
                    try:
                        nomina12_nomina_total_percepciones = Decimal(format(float(element.attrib["TotalPercepciones"]), ".4f"))
                    except InvalidOperation:
                        nomina12_nomina_total_percepciones = None
                if "TotalDeducciones" in element.attrib:
                    try:
                        nomina12_nomina_total_deducciones = Decimal(format(float(element.attrib["TotalDeducciones"]), ".4f"))
                    except InvalidOperation:
                        nomina12_nomina_total_deducciones = None
                if "TotalOtrosPagos" in element.attrib:
                    try:
                        nomina12_nomina_total_otros_pagos = Decimal(format(float(element.attrib["TotalOtrosPagos"]), ".4f"))
                    except InvalidOperation:
                        nomina12_nomina_total_otros_pagos = None

        # Si NO se encontro el Receptor RFC, se agrega a la lista de errores y se omite
        if cfdi_receptor_rfc is None:
            receptor_rfc_no_encontrado.append(archivo_nombre)
            continue

        # Si el Receptor RFC no coincide con el RFC en el nombre del archivo, se agrega a la lista de errores y se omite
        if cfdi_receptor_rfc != rfc_en_nombre:
            receptor_rfc_no_coincide.append(archivo_nombre)
            continue

        # Si el Emisor RFC no coincide con CFDI_EMISOR_RFC, se agrega a la lista de errores y se omite
        if CFDI_EMISOR_RFC != "" and cfdi_emisor_rfc != CFDI_EMISOR_RFC:
            emisor_rfc_no_coincide.append(archivo_nombre)
            continue

        # Si el Emisor Nombre no coincide con CFDI_EMISOR_NOMBRE, se agrega a la lista de errores y se omite
        if CFDI_EMISOR_NOMBRE != "" and cfdi_emisor_nombre != CFDI_EMISOR_NOMBRE:
            emisor_nombre_no_coincide.append(archivo_nombre)
            continue

        # Si el Emisor Regimen Fiscal no coincide con CFDI_EMISOR_REGIMEN_FISCAL, se agrega a la lista de errores y se omite
        if CFDI_EMISOR_REGFIS != "" and cfdi_emisor_regimen_fiscal != CFDI_EMISOR_REGFIS:
            emisor_regfis_no_coincide.append(archivo_nombre)
            continue

        # Si nomina12_nomina_total_percepciones no se encuentra, se agrega a la lista de errores y se omite
        if nomina_total_percepciones_no_encontrado is None:
            nomina_total_percepciones_no_encontrado.append(archivo_nombre)
            continue

        # Si nomina12_nomina_total_deducciones no se encuentra, se agrega a la lista de errores y se omite
        if nomina_total_deducciones_no_encontrado is None:
            nomina_total_deducciones_no_encontrado.append(archivo_nombre)
            continue

        # Consultar las nominas del RFC del Receptor, de la quincena, del tipo y sin timbrado_id
        nominas = (
            Nomina.query.join(Persona)
            .join(Quincena)
            .filter(Persona.rfc == cfdi_receptor_rfc)
            .filter(Quincena.clave == quincena_clave)
            .filter(Nomina.tipo == tipo)
        )

        # Si sobreescribir es falso, se filtra por los registros con timbrado_id igual a CERO
        if sobreescribir is False:
            nominas = nominas.filter(Nomina.timbrado_id == 0)

        # Si viene desde_clave, se filtra
        if desde_clave != "":
            nominas = nominas.filter(Nomina.desde_clave == desde_clave)

        # Si viene hasta_clave, se filtra
        if hasta_clave != "":
            nominas = nominas.filter(Nomina.hasta_clave == hasta_clave)

        # Consultar las nominas, ordenar
        nominas = nominas.filter(Nomina.estatus == "A").order_by(Persona.rfc, Nomina.desde_clave).all()

        # Si NO se encuentra registro en Nomina
        if len(nominas) == 0:
            nomina_no_encontrada.append(cfdi_receptor_rfc)
            continue

        # Bucle por las nominas encontradas
        nomina = None
        for nomina_a_revisar in nominas:
            # Si nomina.importe es CERO, se omite esta nomina
            if nomina_a_revisar.importe == 0:
                continue

            # Si esta nomina coincide con nomina12_nomina_total_deducciones
            if nomina_a_revisar.deduccion == nomina12_nomina_total_deducciones:
                nomina = nomina_a_revisar
                break

        # Si NO hubo coincidencia con nomina12_nomina_total_deducciones
        if nomina is None:
            # Si la consulta de nominas tiene resultados
            if len(nominas) > 0:
                # Se toma la primera nomina de la consulta
                nomina = nominas[0]
            else:
                # Agregar a timbrados_sin_nominas porque NO hay nomina que relacionar
                timbrados_sin_nominas.append(archivo_nombre)

        # Inicializar bandera hay_cambios
        hay_cambios = False

        # Puede existir el registro de Timbrado, consultar por el UUID
        timbrado = Timbrado.query.filter(Timbrado.tfd_uuid == tfd_uuid).first()

        # Si NO existe el registro de Timbrado, se crea
        es_nuevo = False
        if timbrado is None:
            timbrado = Timbrado(nomina=nomina, estado="TIMBRADO", archivo_pdf="", url_pdf="", archivo_xml="", url_xml="")
            es_nuevo = True
            hay_cambios = True

        # Si cfdi_emisor_rfc es diferente
        if cfdi_emisor_rfc is not None and timbrado.cfdi_emisor_rfc != cfdi_emisor_rfc:
            timbrado.cfdi_emisor_rfc = cfdi_emisor_rfc
            hay_cambios = True

        # Si cfdi_emisor_nombre es diferente
        if cfdi_emisor_nombre is not None and timbrado.cfdi_emisor_nombre != cfdi_emisor_nombre:
            timbrado.cfdi_emisor_nombre = cfdi_emisor_nombre
            hay_cambios = True

        # Si cfdi_emisor_regimen_fiscal es diferente
        if cfdi_emisor_regimen_fiscal is not None and timbrado.cfdi_emisor_regimen_fiscal != cfdi_emisor_regimen_fiscal:
            timbrado.cfdi_emisor_regimen_fiscal = cfdi_emisor_regimen_fiscal
            hay_cambios = True

        # Si cfdi_receptor_rfc es diferente
        if cfdi_receptor_rfc is not None and timbrado.cfdi_receptor_rfc != cfdi_receptor_rfc:
            timbrado.cfdi_receptor_rfc = cfdi_receptor_rfc
            hay_cambios = True

        # Si cfdi_receptor_nombre es diferente
        if cfdi_receptor_nombre is not None and timbrado.cfdi_receptor_nombre != cfdi_receptor_nombre:
            timbrado.cfdi_receptor_nombre = cfdi_receptor_nombre
            hay_cambios = True

        # Si tfd_version es diferente
        if tfd_version is not None and timbrado.tfd_version != tfd_version:
            timbrado.tfd_version = tfd_version
            hay_cambios = True

        # Si tfd_uuid es diferente
        if tfd_uuid is not None and timbrado.tfd_uuid != tfd_uuid:
            timbrado.tfd_uuid = tfd_uuid
            hay_cambios = True

        # Para comparar tfd_fecha_timbrado hay que convertir el datetime a string como 2024-01-17T14:19:16
        tfd_fecha_timbrado_str = ""
        if timbrado.tfd_fecha_timbrado is not None:
            tfd_fecha_timbrado_str = timbrado.tfd_fecha_timbrado.strftime("%Y-%m-%dT%H:%M:%S")

        # Si tfd_fecha_timbrado es diferente
        if tfd_fecha_timbrado is not None and tfd_fecha_timbrado_str != tfd_fecha_timbrado:
            timbrado.tfd_fecha_timbrado = tfd_fecha_timbrado
            hay_cambios = True

        # Si tfd_sello_cfd es diferente
        if tfd_sello_cfd is not None and timbrado.tfd_sello_cfd != tfd_sello_cfd:
            timbrado.tfd_sello_cfd = tfd_sello_cfd
            hay_cambios = True

        # Si tfd_num_cert_sat es diferente
        if tfd_num_cert_sat is not None and timbrado.tfd_num_cert_sat != tfd_num_cert_sat:
            timbrado.tfd_num_cert_sat = tfd_num_cert_sat
            hay_cambios = True

        # Si tfd_sello_sat es diferente
        if tfd_sello_sat is not None and timbrado.tfd_sello_sat != tfd_sello_sat:
            timbrado.tfd_sello_sat = tfd_sello_sat
            hay_cambios = True

        # Si nomina12_nomina_version es diferente
        if nomina12_nomina_version is not None and timbrado.nomina12_nomina_version != nomina12_nomina_version:
            timbrado.nomina12_nomina_version = nomina12_nomina_version
            hay_cambios = True

        # Si nomina12_nomina_tipo_nomina es diferente
        if nomina12_nomina_tipo_nomina is not None and timbrado.nomina12_nomina_tipo_nomina != nomina12_nomina_tipo_nomina:
            timbrado.nomina12_nomina_tipo_nomina = nomina12_nomina_tipo_nomina
            hay_cambios = True

        # Para comparar nomina12_nomina_fecha_pago hay que convertir el datetime a string como 2024-01-17T14:19:16
        nomina12_nomina_fecha_pago_str = ""
        if timbrado.nomina12_nomina_fecha_pago is not None:
            nomina12_nomina_fecha_pago_str = timbrado.nomina12_nomina_fecha_pago.strftime("%Y-%m-%dT%H:%M:%S")

        # Si nomina12_nomina_fecha_pago es diferente
        if nomina12_nomina_fecha_pago is not None and nomina12_nomina_fecha_pago_str != nomina12_nomina_fecha_pago:
            timbrado.nomina12_nomina_fecha_pago = nomina12_nomina_fecha_pago
            hay_cambios = True

        # Para comparar nomina12_nomina_fecha_inicial_pago hay que convertir el datetime a string como 2024-01-17T14:19:16
        nomina12_nomina_fecha_inicial_pago_str = ""
        if timbrado.nomina12_nomina_fecha_inicial_pago is not None:
            nomina12_nomina_fecha_inicial_pago_str = timbrado.nomina12_nomina_fecha_inicial_pago.strftime("%Y-%m-%dT%H:%M:%S")

        # Si nomina12_nomina_fecha_inicial_pago es diferente
        if (
            nomina12_nomina_fecha_inicial_pago is not None
            and nomina12_nomina_fecha_inicial_pago_str != nomina12_nomina_fecha_inicial_pago
        ):
            timbrado.nomina12_nomina_fecha_inicial_pago = nomina12_nomina_fecha_inicial_pago
            hay_cambios = True

        # Para comparar nomina12_nomina_fecha_final_pago hay que convertir el datetime a string como 2024-01-17T14:19:16
        nomina12_nomina_fecha_final_pago_str = ""
        if timbrado.nomina12_nomina_fecha_final_pago is not None:
            nomina12_nomina_fecha_final_pago_str = timbrado.nomina12_nomina_fecha_final_pago.strftime("%Y-%m-%dT%H:%M:%S")

        # Si nomina12_nomina_fecha_final_pago es diferente
        if (
            nomina12_nomina_fecha_final_pago is not None
            and nomina12_nomina_fecha_final_pago_str != nomina12_nomina_fecha_final_pago
        ):
            timbrado.nomina12_nomina_fecha_final_pago = nomina12_nomina_fecha_final_pago
            hay_cambios = True

        # Si nomina12_nomina_total_percepciones es diferente
        if (
            nomina12_nomina_total_percepciones is not None
            and timbrado.nomina12_nomina_total_percepciones != nomina12_nomina_total_percepciones
        ):
            timbrado.nomina12_nomina_total_percepciones = nomina12_nomina_total_percepciones
            hay_cambios = True

        # Si nomina12_nomina_total_deducciones es diferente
        if (
            nomina12_nomina_total_deducciones is not None
            and timbrado.nomina12_nomina_total_deducciones != nomina12_nomina_total_deducciones
        ):
            timbrado.nomina12_nomina_total_deducciones = nomina12_nomina_total_deducciones
            hay_cambios = True

        # Si nomina12_nomina_total_otros_pagos es diferente
        if (
            nomina12_nomina_total_otros_pagos is not None
            and timbrado.nomina12_nomina_total_otros_pagos != nomina12_nomina_total_otros_pagos
        ):
            timbrado.nomina12_nomina_total_otros_pagos = nomina12_nomina_total_otros_pagos
            hay_cambios = True

        # Definir valores por defecto
        archivo_xml = timbrado.archivo_xml
        url_xml = timbrado.url_xml
        archivo_pdf = timbrado.archivo_pdf
        url_pdf = timbrado.url_pdf

        # Si esta definido el deposito GCS
        if CLOUD_STORAGE_DEPOSITO != "":
            # Bloque try-except para contar errores en subida de archivos XML
            try:
                # Definir el nombre de descarga del archivo XML
                if archivo_sufijo == "":
                    archivo_xml = f"{cfdi_receptor_rfc}-{quincena_clave}.xml"
                else:
                    archivo_xml = f"{cfdi_receptor_rfc}-{quincena_clave}-{archivo_sufijo}.xml"
                # Definir la ruta del archivo XML en el deposito GCS
                blob_nombre_xml = f"{CARPETA}/{directorio}/{tfd_uuid}.xml"
                # Si existe el archivo XML en el deposito GCS
                if check_file_exists_from_gcs(CLOUD_STORAGE_DEPOSITO, blob_nombre_xml):
                    # Obtener la URL del archivo XML
                    url_xml = get_public_url_from_gcs(CLOUD_STORAGE_DEPOSITO, blob_nombre_xml)
                # De lo contrario, NO existe el archivo XML en el deposito GCS
                else:
                    # Si NO existe el archivo XML, causa error
                    if not ruta_xml.is_file():
                        raise MyFileNotFoundError
                    # Cargar el contenido del archivo XML
                    with open(ruta_xml, "r", encoding="utf8") as f:
                        data_xml = f.read()
                    # Subir el archivo XML
                    url_xml = upload_file_to_gcs(
                        bucket_name=CLOUD_STORAGE_DEPOSITO,
                        blob_name=blob_nombre_xml,
                        content_type="application/xml",
                        data=data_xml,
                    )
                    click.echo(click.style("(XML)", fg="green"), nl=False)
            except Exception:
                archivo_xml = ""
                url_xml = ""
                errores_cargas_xml_contador += 1
                click.echo(click.style("(XML)", fg="red"), nl=False)

            # Bloque try-except para contar errores en subida de archivos PDF
            try:
                # Definir el nombre de descarga del archivo PDF
                if archivo_sufijo == "":
                    archivo_pdf = f"{cfdi_receptor_rfc}-{quincena_clave}.pdf"
                else:
                    archivo_pdf = f"{cfdi_receptor_rfc}-{quincena_clave}-{archivo_sufijo}.pdf"
                # Definir la ruta del archivo PDF en el deposito GCS
                blob_nombre_pdf = f"{CARPETA}/{directorio}/{tfd_uuid}.pdf"
                # Si existe el archivo PDF en el deposito GCS
                if check_file_exists_from_gcs(CLOUD_STORAGE_DEPOSITO, blob_nombre_pdf):
                    # Obtener la URL del archivo PDF
                    url_pdf = get_public_url_from_gcs(CLOUD_STORAGE_DEPOSITO, blob_nombre_pdf)
                # De lo contrario, NO existe el archivo PDF en el deposito GCS
                else:
                    # Si NO existe el archivo XML, causa error
                    if not ruta_pdf.is_file():
                        raise MyFileNotFoundError
                    # Cargar el contenido del archivo PDF
                    with open(ruta_pdf, "rb") as f:
                        data_pdf = f.read()
                    # Subir el archivo PDF
                    url_pdf = upload_file_to_gcs(
                        bucket_name=CLOUD_STORAGE_DEPOSITO,
                        blob_name=blob_nombre_pdf,
                        content_type="application/pdf",
                        data=data_pdf,
                    )
                    click.echo(click.style("(PDF)", fg="green"), nl=False)
            except (MyBucketNotFoundError, MyFileNotAllowedError, MyFileNotFoundError, MyUploadError):
                archivo_pdf = ""
                url_pdf = ""
                errores_cargas_pdf_contador += 1
                click.echo(click.style("(PDF)", fg="red"), nl=False)

        # Si archivo_xml es diferente
        if timbrado.archivo_xml != archivo_xml:
            timbrado.archivo_xml = archivo_xml
            hay_cambios = True

        # Si url_xml es diferente
        if timbrado.url_xml != url_xml:
            timbrado.url_xml = url_xml
            hay_cambios = True

        # Si archivo_pdf es diferente
        if timbrado.archivo_pdf != archivo_pdf:
            timbrado.archivo_pdf = archivo_pdf
            hay_cambios = True

        # Si url_pdf es diferente
        if timbrado.url_pdf != url_pdf:
            timbrado.url_pdf = url_pdf
            hay_cambios = True

        # Si hay_cambios
        if hay_cambios:
            # Cargar el contenido XML
            with open(ruta_xml, "r", encoding="utf8") as f:
                timbrado.tfd = f.read()

            # Guardar timbrado
            timbrado.save()

            # Si nomina.timbrado_id tiene un valor diferente a CERO
            if nomina and nomina.timbrado_id:
                timbrado_por_eliminar = Timbrado.query.get(nomina.timbrado_id)
                if timbrado_por_eliminar and timbrado_por_eliminar.estatus == "A":
                    # Eliminar el timbrado anterior
                    timbrado_por_eliminar.delete()
                    click.echo(click.style("x", fg="red"), nl=False)

            # Actualizar nomina con el ID del timbrado
            nomina.timbrado_id = timbrado.id
            nomina.save()

            # Si es_nuevo, incrementar agregados_contador
            if es_nuevo:
                agregados_contador += 1
                click.echo(click.style("+", fg="green"), nl=False)
            else:
                actualizados_contador += 1
                click.echo(click.style("u", fg="cyan"), nl=False)

        # Incrementar procesados_contador
        procesados_contador += 1

        # Mostrar un punto en la terminal
        if not hay_cambios:
            click.echo(click.style("-", fg="yellow"), nl=False)

    # Poner avance de linea
    click.echo("")

    # Si hubo nomina_no_encontrada, se muestran
    if len(nomina_no_encontrada) > 0:
        click.echo(click.style(f"  NO se encontraron nominas para {len(nomina_no_encontrada)} archivos XML", fg="yellow"))
        click.echo(click.style(f"  {', '.join(nomina_no_encontrada)}", fg="yellow"))

    # Si hubo timbrados sin nominas, se muestran
    if len(timbrados_sin_nominas) > 0:
        click.echo(click.style(f"  Hubo {len(timbrados_sin_nominas)} Timbrados cuyos totales NO coinciden", fg="yellow"))
        click.echo(click.style(f"  {', '.join(timbrados_sin_nominas)}", fg="yellow"))

    # Si hubo errores en archivos_pdf_no_encontrados, se muestran
    if len(archivos_pdf_no_encontrados) > 0:
        click.echo(click.style(f"  Faltan {len(archivos_pdf_no_encontrados)} archivos PDF", fg="yellow"))
        click.echo(click.style(f"  {', '.join(archivos_pdf_no_encontrados)}", fg="yellow"))

    # Si hubo errores en emisor_rfc_no_coincide, se muestran
    if len(emisor_rfc_no_coincide) > 0:
        click.echo(click.style(f"  En {len(emisor_rfc_no_coincide)} Emisor RFC NO es {CFDI_EMISOR_RFC}", fg="yellow"))
        click.echo(click.style(f"  {', '.join(emisor_rfc_no_coincide)}", fg="yellow"))

    # Si hubo errores en emisor_nombre_no_coincide, se muestran
    if len(emisor_nombre_no_coincide) > 0:
        click.echo(click.style(f"  En {len(emisor_nombre_no_coincide)} Emisor Nombre NO es {CFDI_EMISOR_NOMBRE}", fg="yellow"))
        click.echo(click.style(f"  {', '.join(emisor_nombre_no_coincide)}", fg="yellow"))

    # Si hubo errores en emisor_regimen_fiscal_no_coincide, se muestran
    if len(emisor_regfis_no_coincide) > 0:
        click.echo(click.style(f"  En {len(emisor_regfis_no_coincide)} Emisor RegFis NO es {CFDI_EMISOR_REGFIS}", fg="yellow"))
        click.echo(click.style(f"  {', '.join(emisor_regfis_no_coincide)}", fg="yellow"))

    # Si hubo errores en receptor_rfc_no_encontrado, se muestran
    if len(receptor_rfc_no_encontrado) > 0:
        click.echo(click.style(f"  En {len(receptor_rfc_no_encontrado)} Receptor RFC NO se encuentra", fg="yellow"))
        click.echo(click.style(f"  {', '.join(receptor_rfc_no_encontrado)}", fg="yellow"))

    # Si hubo errores en receptor_rfc_no_coincide, se muestran
    if len(receptor_rfc_no_coincide) > 0:
        click.echo(click.style(f"  En {len(receptor_rfc_no_coincide)} Receptor RFC NO coincide", fg="yellow"))
        click.echo(click.style(f"  {', '.join(receptor_rfc_no_coincide)}", fg="yellow"))

    # Si hubo errores_cargas_xml, se muestra el contador
    if errores_cargas_xml_contador > 0:
        click.echo(click.style(f"  Hubo {errores_cargas_xml_contador} errores en cargas XML", fg="yellow"))

    # Si hubo errores_cargas_pdf, se muestra el contador
    if errores_cargas_pdf_contador > 0:
        click.echo(click.style(f"  Hubo {errores_cargas_pdf_contador} errores en cargas PDF", fg="yellow"))

    # Si se actualizaron registros en Timbrados, se muestra el contador
    if actualizados_contador > 0:
        click.echo(click.style(f"  Se actualizaron {actualizados_contador} timbrados.", fg="green"))

    # Si se agregaron registros en Timbrados, se muestra el contador
    if agregados_contador > 0:
        click.echo(click.style(f"  Se agregaron {agregados_contador} timbrados.", fg="green"))

    # Mostrar la cantidad de archivos XML procesados
    click.echo(click.style(f"  Se procesaron {procesados_contador} archivos XML.", fg="green"))


@click.command()
@click.argument("quincena_clave", type=str)
@click.argument("nomina_tipo", type=str)
def exportar_xlsx(quincena_clave, nomina_tipo):
    """Exportar Timbrados (con datos particulares dentro de los XML) a un archivo XLSX"""

    # Ejecutar la tarea
    try:
        mensaje_termino, _, _ = task_exportar_xlsx(quincena_clave, nomina_tipo)
    except Exception as error:
        click.echo(click.style(str(error), fg="red"))
        sys.exit(1)

    # Mensaje de termino
    click.echo(click.style(mensaje_termino, fg="green"))


@click.command()
@click.argument("auditoria_csv", type=str)
def exportar_auditoria_xlsx(auditoria_csv):
    """Exportar Timbrados leyendo un archivo CSV con quincenas y RFCs a un archivo XLSX"""

    # Validar archivo CSV
    ruta = Path(auditoria_csv)
    if not ruta.exists():
        click.echo(f"ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        click.echo(f"ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)

    # Iniciar el archivo XLSX
    libro = Workbook()

    # Tomar la hoja del libro XLSX
    hoja = libro.active
    if hoja is None:
        click.echo("ERROR: No se pudo iniciar el archivo XLSX.")
        sys.exit(1)

    # Agregar la fila con las cabeceras de las columnas
    hoja.append(
        [
            "QUINCENA",
            "RFC",
            "NOMBRE_COMPLETO",
            "NUM_EMPLEADO",
            "MODELO",
            "NOMINA_TIPO",
            "TIMBRE_ESTADO",
            "TFD_UUID",
            "FECHA_PAGO",
            "FECHA_INICIAL_PAGO",
            "FECHA_FINAL_PAGO",
            "TOTAL_PERCEPCIONES",
            "TOTAL_DEDUCCIONES",
            "TOTAL_OTROS_PAGOS",
        ]
    )

    # Determinar el directorio y el nombre del archivo XLSX
    ahora = datetime.now(tz=pytz.timezone(TIMEZONE))
    auditoria = f"auditoria_{ahora.strftime('%Y-%m-%d_%H%M%S')}"
    nombre_archivo_xlsx = f"{auditoria}.xlsx"

    # Inicializar contadores
    quincenas_no_validas = []
    nominas_multiples_encontradas = []
    nominas_no_encontradas = []
    nominas_sin_timbrado = []
    personas_no_encontradas = []
    rfc_no_validos = []
    timbrados_no_encontrados = []
    tipos_no_validos = []
    contador = 0

    # Leer el archivo CSV
    click.echo("Leyendo archivo CSV con quincenas y RFCs: ", nl=False)
    with open(ruta, newline="", encoding="utf8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Validar QUINCENA
            quincena_clave = row.get("QUINCENA", "").strip()
            if re.match(QUINCENA_REGEXP, quincena_clave) is None:
                quincenas_no_validas.append(quincena_clave)
                click.echo(click.style("X", fg="yellow"), nl=False)
                continue

            # Validar RFC
            rfc = row.get("RFC", "").strip().upper()
            if re.match(RFC_REGEXP, rfc) is None:
                rfc_no_validos.append(rfc)
                click.echo(click.style("X", fg="yellow"), nl=False)
                continue

            # Validar TIPO_NOMINA_PERSEO
            tipo = row.get("TIPO_NOMINA_PERSEO", "").strip().upper()
            if tipo not in Nomina.TIPOS:
                tipos_no_validos.append(tipo)
                click.echo(click.style("X", fg="yellow"), nl=False)
                continue

            # Consultar la nomina, filtrando por la persona con su RFC, el tipo y la quincena
            nominas = (
                Nomina.query.join(Persona)
                .join(Quincena)
                .filter(Nomina.tipo == tipo)
                .filter(Persona.rfc == rfc)
                .filter(Quincena.clave == quincena_clave)
                .filter(Nomina.estatus == "A")
                .order_by(Persona.rfc, Nomina.desde_clave)
                .all()
            )

            # Si NO se encontraron nominas, se agrega a la lista de no encontradas y se omite
            if len(nominas) == 0:
                # Consultar en personas si existe el RFC
                persona = Persona.query.filter(Persona.rfc == rfc).filter(Persona.estatus == "A").first()
                if persona is None:
                    personas_no_encontradas.append(rfc)
                    click.echo(click.style("P", fg="yellow"), nl=False)
                    continue
                # De lo contrario, la persona si existe, pero no tiene nominas en la quincena y tipo indicados
                nominas_no_encontradas.append(f"{rfc} ({quincena_clave} {tipo})")
                click.echo(click.style("N", fg="yellow"), nl=False)
                continue

            # Si se encontraron múltiples nominas, se agrega a la lista de multiples encontradas, PERO se sigue procesando
            if len(nominas) > 1:
                nominas_multiples_encontradas.append(f"{rfc} ({quincena_clave} {tipo})")
                click.echo(click.style("M", fg="cyan"), nl=False)

            # Consultar el (o los) timbrado(s)
            for nomina in nominas:
                # Si NO tiene timbrado_id
                if not nomina.timbrado_id:
                    nominas_sin_timbrado.append(f"{rfc} ({quincena_clave} {tipo})")
                    click.echo(click.style("0", fg="yellow"), nl=False)
                    continue
                # Consultar el (o los) timbrado(s)
                try:
                    timbrado = Timbrado.query.filter(Timbrado.id == nomina.timbrado_id).filter(Timbrado.estatus == "A").one()
                except (MultipleResultsFound, NoResultFound):
                    timbrados_no_encontrados.append(f"{rfc} ({quincena_clave} {tipo})")
                    click.echo(click.style("T", fg="yellow"), nl=False)
                    continue

                # Agregar la fila
                hoja.append(
                    [
                        nomina.quincena.clave,
                        nomina.persona.rfc,
                        nomina.persona.nombre_completo,
                        nomina.persona.num_empleado,
                        nomina.persona.modelo,
                        nomina.tipo,
                        timbrado.estado,
                        timbrado.tfd_uuid,
                        timbrado.nomina12_nomina_fecha_pago,
                        timbrado.nomina12_nomina_fecha_inicial_pago,
                        timbrado.nomina12_nomina_fecha_final_pago,
                        timbrado.nomina12_nomina_total_percepciones,
                        timbrado.nomina12_nomina_total_deducciones,
                        timbrado.nomina12_nomina_total_otros_pagos,
                    ]
                )

                # Incrementar el contador
                contador += 1

                # Definir el subdirectorio segun el tipo de nomina
                subdir = quincena_clave
                if nomina.tipo == "AGUINALDO":
                    subdir = f"{quincena_clave}Aguinaldos"
                elif nomina.tipo == "APOYO ANUAL":
                    subdir = f"{quincena_clave}ApoyosAnuales"
                elif nomina.tipo == "APOYO DIA DE LA MADRE":
                    subdir = f"{quincena_clave}ApoyosDiaDeLaMadre"
                elif nomina.tipo == "PRIMA VACACIONAL":
                    subdir = f"{quincena_clave}PrimasVacacionales"

                # Definir la ruta a los archivos XML y PDF
                ruta_pdf = Path(f"{TIMBRADOS_BASE_DIR}/{subdir}/{timbrado.tfd_uuid}.pdf")
                ruta_xml = Path(f"{TIMBRADOS_BASE_DIR}/{subdir}/{timbrado.tfd_uuid}.xml")

                # Si ambos archivos existen, copiarlos
                if ruta_pdf.is_file() and ruta_xml.is_file():
                    try:
                        # Crear el directorio auditoria si no existe
                        auditoria_dir = Path(auditoria)
                        auditoria_dir.mkdir(parents=True, exist_ok=True)
                        # Copiar los archivos XML y PDF si existen
                        destino_pdf = Path(auditoria, f"{nomina.persona.rfc}_{timbrado.tfd_uuid}.pdf")
                        destino_xml = Path(auditoria, f"{nomina.persona.rfc}_{timbrado.tfd_uuid}.xml")
                        destino_pdf.write_bytes(ruta_pdf.read_bytes())
                        destino_xml.write_bytes(ruta_xml.read_bytes())
                        click.echo(click.style("+", fg="green"), nl=False)
                    except Exception:
                        click.echo(click.style("E", fg="red"), nl=False)
                else:
                    click.echo(click.style(".", fg="green"), nl=False)

    # Guardar el archivo XLSX
    libro.save(nombre_archivo_xlsx)

    # Mensaje de termino
    click.echo()
    if len(quincenas_no_validas) > 0:
        click.echo(click.style(f"Quincenas NO válidas {len(quincenas_no_validas)}: ", fg="white"), nl=False)
        click.echo(click.style({", ".join(quincenas_no_validas)}, fg="yellow"))
    if len(rfc_no_validos) > 0:
        click.echo(click.style(f"RFCs NO válidos {len(rfc_no_validos)}: ", fg="white"), nl=False)
        click.echo(click.style(", ".join(rfc_no_validos), fg="yellow"))
    if len(tipos_no_validos) > 0:
        click.echo(click.style(f"Tipos de nómina NO válidos {len(tipos_no_validos)}: ", fg="white"), nl=False)
        click.echo(click.style(", ".join(tipos_no_validos), fg="yellow"))
    if len(personas_no_encontradas) > 0:
        click.echo(click.style(f"Personas NO encontradas {len(personas_no_encontradas)}: ", fg="white"), nl=False)
        click.echo(click.style(", ".join(personas_no_encontradas), fg="yellow"))
    if len(nominas_multiples_encontradas) > 0:
        click.echo(click.style(f"Nóminas múltiples encontradas {len(nominas_multiples_encontradas)}: ", fg="white"), nl=False)
        click.echo(click.style(", ".join(nominas_multiples_encontradas), fg="cyan"))
    if len(nominas_no_encontradas) > 0:
        click.echo(click.style(f"Nóminas NO encontradas {len(nominas_no_encontradas)}: ", fg="white"), nl=False)
        click.echo(click.style(", ".join(nominas_no_encontradas), fg="yellow"))
    if len(nominas_sin_timbrado) > 0:
        click.echo(click.style(f"Nóminas SIN timbrado {len(nominas_sin_timbrado)}: ", fg="white"), nl=False)
        click.echo(click.style(", ".join(nominas_sin_timbrado), fg="yellow"))
    if len(timbrados_no_encontrados) > 0:
        click.echo(click.style(f"Timbrados NO encontrados {len(timbrados_no_encontrados)}: ", fg="yellow"), nl=False)
        click.echo(click.style(", ".join(timbrados_no_encontrados), fg="yellow"))
    click.echo(click.style(f"Archivo XLSX generado con {contador} filas: {nombre_archivo_xlsx}", fg="green"))


@click.command()
@click.argument("aguinaldos_csv", type=str)
def exportar_aguinaldos_xlsx(aguinaldos_csv):
    """Exportar Timbrados de aguinaldos y crear un reporte XLSX leyendo un archivo CSV"""

    # Validar archivo CSV
    ruta = Path(aguinaldos_csv)
    if not ruta.exists():
        click.echo(f"ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        click.echo(f"ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)

    # Iniciar el archivo XLSX
    libro = Workbook()

    # Tomar la hoja del libro XLSX
    hoja = libro.active
    if hoja is None:
        click.echo("ERROR: No se pudo iniciar el archivo XLSX.")
        sys.exit(1)

    # Agregar la fila con las cabeceras de las columnas
    hoja.append(
        [
            "QUINCENA",
            "RFC",
            "NOMBRE_COMPLETO",
            "NUM_EMPLEADO",
            "MODELO",
            "NOMINA_TIPO",
            "QUINCENA DESDE",
            "QUINCENA HASTA",
            "TIMBRE_ESTADO",
            "TFD_UUID",
            "FECHA_PAGO",
            "FECHA_INICIAL_PAGO",
            "FECHA_FINAL_PAGO",
            "TOTAL_PERCEPCIONES",
            "TOTAL_DEDUCCIONES",
            "TOTAL_OTROS_PAGOS",
            "IMPORTE EXENTO P22",
            "IMPORTE GRAVADO PGA",
            "GCS TIMBRADOS URL PDF",
            "GCS TIMBRADOS URL XML",
        ]
    )

    # Determinar el nombre del archivo XLSX
    ahora = datetime.now(tz=pytz.timezone(TIMEZONE))
    exportar_aguinaldos_str = f"aguinaldos_{ahora.strftime('%Y-%m-%d_%H%M%S')}"
    nombre_archivo_xlsx = f"{exportar_aguinaldos_str}.xlsx"

    # Inicializar contadores
    errores_al_parsear_xml = []
    nominas_multiples_encontradas = []
    nominas_no_encontradas = []
    nominas_sin_timbrado = []
    personas_no_encontradas = []
    quincenas_no_validas = []
    rfc_no_validos = []
    timbrados_no_encontrados = []
    tipos_no_validos = []
    contador = 0

    # Listado de RFCs consultados para evitar repetidos
    rfcs_consultados = []

    # Leer el archivo CSV
    click.echo("Leyendo archivo CSV: ", nl=False)
    with open(ruta, newline="", encoding="utf8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Validar QUINCENA
            quincena_clave = row.get("QUINCENA", "").strip()
            if re.match(QUINCENA_REGEXP, quincena_clave) is None:
                quincenas_no_validas.append(quincena_clave)
                click.echo(click.style("X", fg="yellow"), nl=False)
                continue

            # Validar RFC
            rfc = row.get("RFC", "").strip().upper()
            if re.match(RFC_REGEXP, rfc) is None:
                rfc_no_validos.append(rfc)
                click.echo(click.style("X", fg="yellow"), nl=False)
                continue

            # Validar TIPO_NOMINA_PERSEO
            tipo = row.get("TIPO_NOMINA_PERSEO", "").strip().upper()
            if tipo not in Nomina.TIPOS:
                tipos_no_validos.append(tipo)
                click.echo(click.style("X", fg="yellow"), nl=False)
                continue

            # Si ya se consultó este RFC, se omite
            if rfc in rfcs_consultados:
                continue

            # Consultar la nomina, filtrando por la persona con su RFC, el tipo y la quincena
            nominas = (
                Nomina.query.join(Persona)
                .join(Quincena)
                .filter(Nomina.tipo == tipo)
                .filter(Persona.rfc == rfc)
                .filter(Quincena.clave == quincena_clave)
                .filter(Nomina.estatus == "A")
                .order_by(Persona.rfc, Nomina.desde_clave)
                .all()
            )

            # Agregar el RFC a los consultados
            rfcs_consultados.append(rfc)

            # Si NO se encontraron nominas, se agrega a la lista de no encontradas y se omite
            if len(nominas) == 0:
                # Consultar en personas si existe el RFC
                persona = Persona.query.filter(Persona.rfc == rfc).filter(Persona.estatus == "A").first()
                if persona is None:
                    personas_no_encontradas.append(rfc)
                    click.echo(click.style("P", fg="yellow"), nl=False)
                    continue
                # De lo contrario, la persona si existe, pero no tiene nominas en la quincena y tipo indicados
                nominas_no_encontradas.append(f"{rfc} ({quincena_clave} {tipo})")
                click.echo(click.style("N", fg="yellow"), nl=False)
                continue

            # Si se encontraron múltiples nominas, se agrega a la lista de multiples encontradas, PERO se sigue procesando
            if len(nominas) > 1:
                nominas_multiples_encontradas.append(f"{rfc} ({quincena_clave} {tipo})")
                click.echo(click.style("M", fg="cyan"), nl=False)

            # Consultar el (o los) timbrado(s)
            for nomina in nominas:
                # Si NO tiene timbrado_id
                if not nomina.timbrado_id:
                    nominas_sin_timbrado.append(f"{rfc} ({quincena_clave} {tipo})")
                    click.echo(click.style("0", fg="yellow"), nl=False)
                    continue

                # Consultar el (o los) timbrado(s)
                try:
                    timbrado = Timbrado.query.filter(Timbrado.id == nomina.timbrado_id).filter(Timbrado.estatus == "A").one()
                except (MultipleResultsFound, NoResultFound):
                    timbrados_no_encontrados.append(f"{rfc} ({quincena_clave} {tipo})")
                    click.echo(click.style("T", fg="yellow"), nl=False)
                    continue

                # Parsear el contenido XML del timbrado
                tree = ET.ElementTree(ET.fromstring(timbrado.tfd))
                root = tree.getroot()

                # Validar que el tag raiz sea cfdi:Comprobante
                if root is None or root.tag != f"{XML_TAG_CFD_PREFIX}Comprobante":
                    errores_al_parsear_xml.append(f"{rfc} ({quincena_clave} {tipo})")
                    click.echo(click.style("E", fg="yellow"), nl=False)
                    continue

                # Estructura del CFDI version 4.0
                # - cfdi:Comprobante [xmlns:xsi, xmlns:nomina12, xmlns:cfdi, Version, Serie, Folio, Fecha, SubTotal, Descuento, Moneda,
                #     Total, TipoDeComprobante, Exportacion, MetodoPago, LugarExpedicion, Sello, Certificado, NoCertificado]
                #   - cfdi:Complemento
                #     - nomina12:Nomina [Version, TipoNomina, FechaPago, FechaInicialPago, FechaFinalPago, NumDiasPagados,
                #         TotalPercepciones, TotalDeducciones, TotalOtrosPagos]
                #       - nomina12:Percepciones [TotalSueldos, TotalGravado, TotalExento]
                #         - nomina12:Percepcion [TipoPercepcion, Clave, Concepto, ImporteGravado, ImporteExento]

                # Inicializar variables para los importes del aguinaldo
                importe_exento_aguinaldo = "0.00"
                importe_gravado_aguinaldo = "0.00"

                # Bucle por los elementos de root
                for element in root.iter():
                    # Si es Percepcion
                    if element.tag == f"{XML_TAG_NOMINA_PREFIX}Percepcion":
                        # Obtener el importe exento del aguinaldo
                        if (
                            "Clave" in element.attrib
                            and element.attrib["Clave"] == "P22"
                            and "Concepto" in element.attrib
                            and element.attrib["Concepto"] == "AGUINALDO EXCENTO"
                        ):
                            importe_exento_aguinaldo = element.attrib.get("ImporteExento", "0.00")
                        # Obtener el importe gravado del aguinaldo
                        if (
                            "Clave" in element.attrib
                            and element.attrib["Clave"] == "PGA"
                            and "Concepto" in element.attrib
                            and element.attrib["Concepto"] == "AGUINALDO GRAVABLE"
                        ):
                            importe_gravado_aguinaldo = element.attrib.get("ImporteGravado", "0.00")

                # Definir el subdirectorio segun el tipo de nomina
                subdir = quincena_clave
                if nomina.tipo == "AGUINALDO":
                    subdir = f"{quincena_clave}Aguinaldos"
                elif nomina.tipo == "APOYO ANUAL":
                    subdir = f"{quincena_clave}ApoyosAnuales"
                elif nomina.tipo == "APOYO DIA DE LA MADRE":
                    subdir = f"{quincena_clave}ApoyosDiaDeLaMadre"
                elif nomina.tipo == "PRIMA VACACIONAL":
                    subdir = f"{quincena_clave}PrimasVacacionales"

                # Agregar la fila
                hoja.append(
                    [
                        nomina.quincena.clave,
                        nomina.persona.rfc,
                        nomina.persona.nombre_completo,
                        nomina.persona.num_empleado,
                        nomina.persona.modelo,
                        nomina.tipo,
                        nomina.desde_clave,
                        nomina.hasta_clave,
                        timbrado.estado,
                        timbrado.tfd_uuid,
                        timbrado.nomina12_nomina_fecha_pago,
                        timbrado.nomina12_nomina_fecha_inicial_pago,
                        timbrado.nomina12_nomina_fecha_final_pago,
                        timbrado.nomina12_nomina_total_percepciones,
                        timbrado.nomina12_nomina_total_deducciones,
                        timbrado.nomina12_nomina_total_otros_pagos,
                        float(importe_exento_aguinaldo),
                        float(importe_gravado_aguinaldo),
                        f"{GCS_TIMBRADOS_URL_BASE}/{exportar_aguinaldos_str}/{nomina.persona.rfc}_{timbrado.tfd_uuid}.pdf",
                        f"{GCS_TIMBRADOS_URL_BASE}/{exportar_aguinaldos_str}/{nomina.persona.rfc}_{timbrado.tfd_uuid}.xml",
                    ]
                )

                # Incrementar el contador
                contador += 1

                # Definir la ruta a los archivos XML y PDF
                ruta_pdf = Path(f"{TIMBRADOS_BASE_DIR}/{subdir}/{timbrado.tfd_uuid}.pdf")
                ruta_xml = Path(f"{TIMBRADOS_BASE_DIR}/{subdir}/{timbrado.tfd_uuid}.xml")

                # Si ambos archivos existen, copiarlos
                if ruta_pdf.is_file() and ruta_xml.is_file():
                    try:
                        # Crear el directorio si no existe
                        exportar_aguinaldos_dir = Path(exportar_aguinaldos_str)
                        exportar_aguinaldos_dir.mkdir(parents=True, exist_ok=True)
                        # Copiar los archivos
                        destino_pdf = Path(exportar_aguinaldos_str, f"{nomina.persona.rfc}_{timbrado.tfd_uuid}.pdf")
                        destino_xml = Path(exportar_aguinaldos_str, f"{nomina.persona.rfc}_{timbrado.tfd_uuid}.xml")
                        destino_pdf.write_bytes(ruta_pdf.read_bytes())
                        destino_xml.write_bytes(ruta_xml.read_bytes())
                        click.echo(click.style("+", fg="green"), nl=False)
                    except Exception:
                        click.echo(click.style("F", fg="red"), nl=False)
                else:
                    click.echo(click.style(".", fg="green"), nl=False)

    # Guardar el archivo XLSX
    libro.save(nombre_archivo_xlsx)

    # Mensaje de termino
    click.echo()
    if len(errores_al_parsear_xml) > 0:
        click.echo(click.style(f"Errores al parsear el XML {len(errores_al_parsear_xml)}: ", fg="white"), nl=False)
        click.echo(click.style({", ".join(errores_al_parsear_xml)}, fg="yellow"))
    if len(quincenas_no_validas) > 0:
        click.echo(click.style(f"Quincenas NO válidas {len(quincenas_no_validas)}: ", fg="white"), nl=False)
        click.echo(click.style({", ".join(quincenas_no_validas)}, fg="yellow"))
    if len(rfc_no_validos) > 0:
        click.echo(click.style(f"RFCs NO válidos {len(rfc_no_validos)}: ", fg="white"), nl=False)
        click.echo(click.style(", ".join(rfc_no_validos), fg="yellow"))
    if len(tipos_no_validos) > 0:
        click.echo(click.style(f"Tipos de nómina NO válidos {len(tipos_no_validos)}: ", fg="white"), nl=False)
        click.echo(click.style(", ".join(tipos_no_validos), fg="yellow"))
    if len(personas_no_encontradas) > 0:
        click.echo(click.style(f"Personas NO encontradas {len(personas_no_encontradas)}: ", fg="white"), nl=False)
        click.echo(click.style(", ".join(personas_no_encontradas), fg="yellow"))
    if len(nominas_multiples_encontradas) > 0:
        click.echo(click.style(f"Nóminas múltiples encontradas {len(nominas_multiples_encontradas)}: ", fg="white"), nl=False)
        click.echo(click.style(", ".join(nominas_multiples_encontradas), fg="cyan"))
    if len(nominas_no_encontradas) > 0:
        click.echo(click.style(f"Nóminas NO encontradas {len(nominas_no_encontradas)}: ", fg="white"), nl=False)
        click.echo(click.style(", ".join(nominas_no_encontradas), fg="yellow"))
    if len(nominas_sin_timbrado) > 0:
        click.echo(click.style(f"Nóminas SIN timbrado {len(nominas_sin_timbrado)}: ", fg="white"), nl=False)
        click.echo(click.style(", ".join(nominas_sin_timbrado), fg="yellow"))
    if len(timbrados_no_encontrados) > 0:
        click.echo(click.style(f"Timbrados NO encontrados {len(timbrados_no_encontrados)}: ", fg="yellow"), nl=False)
        click.echo(click.style(", ".join(timbrados_no_encontrados), fg="yellow"))
    click.echo(click.style(f"Archivo XLSX generado con {contador} filas: {nombre_archivo_xlsx}", fg="green"))


@click.command()
@click.argument("quincena_clave", type=str)
@click.option("--tipo", type=str, default="SALARIO")
@click.option("--probar", is_flag=True, help="Solo probar sin cambiar la base de datos.")
def actualizar_timbrados_nominas(quincena_clave: str, tipo: str, probar: bool = False):
    """Actualizar los nominas_ids de los timbrados de una quincena"""

    # Validar quincena
    if re.match(QUINCENA_REGEXP, quincena_clave) is None:
        click.echo("ERROR: Quincena inválida.")
        sys.exit(1)

    # Validar tipo
    tipo = safe_string(tipo)
    if tipo not in Nomina.TIPOS:
        click.echo("ERROR: Tipo inválido.")
        sys.exit(1)

    # Consultar la nomina
    nominas = (
        Nomina.query.join(Quincena)
        .filter(Nomina.tipo == tipo)
        .filter(Quincena.clave == quincena_clave)
        .filter(Nomina.estatus == "A")
        .all()
    )

    # Inicializar el contador
    contador = 0

    # Bucle por las nominas
    for nomina in nominas:
        # Si nomina.tibrado_id es nulo, se omite
        if not nomina.timbrado_id:
            continue

        # Consultar el timbrado
        timbrado = Timbrado.query.get(nomina.timbrado_id)

        # Si timbrado no existe, se omite
        if not timbrado:
            click.echo(click.style("?", fg="yellow"), nl=False)
            continue

        # Si timbrado.nomina_id es igual a nomina.id, se omite
        if timbrado.nomina_id == nomina.id:
            click.echo(click.style("-", fg="green"), nl=False)
            continue

        # Si NO esta en modo probar, se actualiza
        if not probar:
            # Actualizar timbrado.nomina_id
            timbrado.nomina_id = nomina.id
            timbrado.save()

        # Incrementar el contador
        contador += 1
        click.echo(click.style(f"[{nomina.id}]", fg="cyan"), nl=False)

    # Mensaje de termino
    click.echo()
    if probar:
        click.echo(
            click.style(
                f"Se encontraron {contador} timbrados para actualizar en la quincena {quincena_clave} y tipo {tipo}.",
                fg="green",
            )
        )
    else:
        click.echo(
            click.style(f"Se actualizaron {contador} timbrados para la quincena {quincena_clave} y tipo {tipo}.", fg="green")
        )


cli.add_command(actualizar)
cli.add_command(exportar_xlsx)
cli.add_command(exportar_auditoria_xlsx)
cli.add_command(exportar_aguinaldos_xlsx)
cli.add_command(actualizar_timbrados_nominas)
