"""
CLI Timbrados
"""
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import click
from dotenv import load_dotenv

from lib.exceptions import MyBucketNotFoundError, MyFileNotAllowedError, MyFileNotFoundError, MyUploadError
from lib.google_cloud_storage import check_file_exists_from_gcs, get_public_url_from_gcs, upload_file_to_gcs
from lib.safe_string import QUINCENA_REGEXP, safe_string
from perseo.app import create_app
from perseo.blueprints.nominas.models import Nomina
from perseo.blueprints.personas.models import Persona
from perseo.blueprints.quincenas.models import Quincena
from perseo.blueprints.timbrados.models import Timbrado
from perseo.extensions import database

CARPETA = "timbrados"
XML_TAG_CFD_PREFIX = "{http://www.sat.gob.mx/cfd/4}"
XML_TAG_TFD_PREFIX = "{http://www.sat.gob.mx/TimbreFiscalDigital}"
XML_TAG_NOMINA_PREFIX = "{http://www.sat.gob.mx/nomina12}"

load_dotenv()

CFDI_EMISOR_RFC = os.environ.get("CFDI_EMISOR_RFC", "")
CFDI_EMISOR_NOMBRE = os.environ.get("CFDI_EMISOR_NOMBRE", "")
CFDI_EMISOR_REGFIS = os.environ.get("CFDI_EMISOR_REGFIS", "")
CLOUD_STORAGE_DEPOSITO = os.environ.get("CLOUD_STORAGE_DEPOSITO", "")
TIMBRADOS_BASE_DIR = os.environ.get("TIMBRADOS_BASE_DIR", "")

app = create_app()
app.app_context().push()
database.app = app


@click.group()
def cli():
    """Timbrados"""


@click.command()
@click.argument("quincena_clave", type=str)
@click.argument("tipo", type=str, default="SALARIO")
@click.option("--subdir", type=str, default=None)
def actualizar(quincena_clave: str, tipo: str, subdir: str):
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
    if tipo not in ["AGUINALDO", "SALARIO", "APOYO ANUAL"]:
        click.echo("ERROR: Tipo inválido.")
        sys.exit(1)

    # Por defecto, el directorio es <quincena_clave>
    directorio = quincena_clave
    archivo_sufijo = ""

    # Si el tipo es APOYO ANUAL, el directorio es <quincena_clave>ApoyoAnual
    if tipo == "APOYO ANUAL":
        directorio = f"{quincena_clave}ApoyosAnuales"
        archivo_sufijo = "apoyo-anual"

    # Si el tipo es AGUINALDO, el directorio es <quincena_clave>Aguinaldo
    if tipo == "AGUINALDO":
        directorio = f"{quincena_clave}Aguinaldos"
        archivo_sufijo = "aguinaldo"

    # Validar que exista el directorio
    if subdir == "":
        timbrados_dir = Path(TIMBRADOS_BASE_DIR, directorio)
    else:
        timbrados_dir = Path(TIMBRADOS_BASE_DIR, directorio, subdir)
    if not timbrados_dir.exists():
        click.echo(f"ERROR: No existe el directorio {timbrados_dir}")
        sys.exit(1)

    # Inicializar listas de errores
    archivos_pdf_no_encontrados = []
    emisor_rfc_no_coincide = []
    emisor_nombre_no_coincide = []
    emisor_regfis_no_coincide = []
    receptor_rfc_no_encontrado = []
    receptor_rfc_no_coincide = []
    nomina_no_encontrada = []

    # Inicializar contadores
    actualizados_contador = 0
    agregados_contador = 0
    errores_cargas_xml_contador = 0
    errores_cargas_pdf_contador = 0
    errores_xml = 0
    procesados_contador = 0

    # Recorrer los archivos con extension xml
    click.echo(f"Actualizar los timbrados de {quincena_clave}: ", nl=False)
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
        #         TotalDeducciones, TotalOtrosPagos]
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
        cfdi_emisor_rfc = None
        cfdi_emisor_nombre = None
        cfdi_emisor_regimen_fiscal = None
        cfdi_receptor_rfc = None
        cfdi_receptor_nombre = None
        tfd_version = None
        tfd_uuid = None
        tfd_fecha_timbrado = None
        tfd_sello_cfd = None
        tfd_num_cert_sat = None
        tfd_sello_sat = None

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

        # Consultar la Nomina
        nomina = (
            Nomina.query.join(Persona)
            .join(Quincena)
            .filter(Persona.rfc == cfdi_receptor_rfc)
            .filter(Quincena.clave == quincena_clave)
            .filter(Nomina.tipo == tipo)
            .filter(Nomina.estatus == "A")
            .order_by(Nomina.id.desc())
            .first()
        )

        # Si NO se encuentra registro en Nomina
        if nomina is None:
            nomina_no_encontrada.append(cfdi_receptor_rfc)
            continue

        # Inicializar bandera hay_cambios
        hay_cambios = False

        # Puede existir el registro de Timbrado
        timbrado = Timbrado.query.filter(Timbrado.nomina == nomina).filter_by(estatus="A").order_by(Timbrado.id.desc()).first()

        # Si NO existe el registro de Timbrado, se crea
        es_nuevo = False
        if timbrado is None:
            timbrado = Timbrado(nomina=nomina, estado="TIMBRADO", archivo_pdf="", url_pdf="", archivo_xml="", url_xml="")
            es_nuevo = True
            hay_cambios = True

        # Si tfd_version es diferente, hay_cambios sera verdadero
        if tfd_version is not None and timbrado.tfd_version != tfd_version:
            timbrado.tfd_version = tfd_version
            hay_cambios = True

        # Si tfd_uuid es diferente, hay_cambios sera verdadero
        if tfd_uuid is not None and timbrado.tfd_uuid != tfd_uuid:
            timbrado.tfd_uuid = tfd_uuid
            hay_cambios = True

        # Para comparar tfd_fecha_timbrado hay que convertir el datetime a string como 2024-01-17T14:19:16
        tfd_fecha_timbrado_str = ""
        if timbrado.tfd_fecha_timbrado is not None:
            tfd_fecha_timbrado_str = timbrado.tfd_fecha_timbrado.strftime("%Y-%m-%dT%H:%M:%S")

        # Si tfd_fecha_timbrado es diferente, hay_cambios sera verdadero
        if tfd_fecha_timbrado is not None and tfd_fecha_timbrado_str != tfd_fecha_timbrado:
            timbrado.tfd_fecha_timbrado = tfd_fecha_timbrado
            hay_cambios = True

        # Si tfd_sello_cfd es diferente, hay_cambios sera verdadero
        if tfd_sello_cfd is not None and timbrado.tfd_sello_cfd != tfd_sello_cfd:
            timbrado.tfd_sello_cfd = tfd_sello_cfd
            hay_cambios = True

        # Si tfd_num_cert_sat es diferente, hay_cambios sera verdadero
        if tfd_num_cert_sat is not None and timbrado.tfd_num_cert_sat != tfd_num_cert_sat:
            timbrado.tfd_num_cert_sat = tfd_num_cert_sat
            hay_cambios = True

        # Si tfd_sello_sat es diferente, hay_cambios sera verdadero
        if tfd_sello_sat is not None and timbrado.tfd_sello_sat != tfd_sello_sat:
            timbrado.tfd_sello_sat = tfd_sello_sat
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
            except (MyBucketNotFoundError, MyFileNotAllowedError, MyFileNotFoundError, MyUploadError):
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

        # Si archivo_xml es diferente, hay_cambios sera verdadero
        if timbrado.archivo_xml != archivo_xml:
            timbrado.archivo_xml = archivo_xml
            hay_cambios = True

        # Si url_xml es diferente, hay_cambios sera verdadero
        if timbrado.url_xml != url_xml:
            timbrado.url_xml = url_xml
            hay_cambios = True

        # Si archivo_pdf es diferente, hay_cambios sera verdadero
        if timbrado.archivo_pdf != archivo_pdf:
            timbrado.archivo_pdf = archivo_pdf
            hay_cambios = True

        # Si url_pdf es diferente, hay_cambios sera verdadero
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

            # Actualizar nomina con el ID del timbrado
            nomina.timbrado_id = timbrado.id
            nomina.save()

            # Si es_nuevo, incrementar agregados_contador
            if es_nuevo:
                agregados_contador += 1
                click.echo(click.style("+", fg="green"), nl=False)
            else:
                actualizados_contador += 1
                click.echo(click.style("u", fg="green"), nl=False)

        # Incrementar procesados_contador
        procesados_contador += 1

        # Mostrar un punto en la terminal
        click.echo(click.style(".", fg="cyan"), nl=False)

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

    # Mostrar mensaje de termino
    click.echo(click.style(f"  Se procesaron {procesados_contador} archivos XML.", fg="green"))
    click.echo(click.style(f"  Se actualizaron {actualizados_contador} registros en Timbrados.", fg="green"))
    click.echo(click.style(f"  Se agregaron {agregados_contador} registros en Timbrados.", fg="green"))


cli.add_command(actualizar)
