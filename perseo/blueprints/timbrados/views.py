"""
Timbrados, vistas
"""

import json

from flask import Blueprint, current_app, flash, make_response, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.exceptions import MyAnyError
from lib.google_cloud_storage import get_blob_name_from_url, get_file_from_gcs
from lib.safe_string import safe_message, safe_quincena, safe_rfc
from perseo.blueprints.bitacoras.models import Bitacora
from perseo.blueprints.modulos.models import Modulo
from perseo.blueprints.nominas.models import Nomina
from perseo.blueprints.permisos.models import Permiso
from perseo.blueprints.personas.models import Persona
from perseo.blueprints.quincenas.models import Quincena
from perseo.blueprints.timbrados.models import Timbrado
from perseo.blueprints.usuarios.decorators import permission_required

MODULO = "TIMBRADOS"

timbrados = Blueprint("timbrados", __name__, template_folder="templates")


@timbrados.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@timbrados.route("/timbrados/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Timbrados"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Timbrado.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "nomina_id" in request.form:
        consulta = consulta.filter_by(nomina_id=request.form["nomina_id"])
    if "estado" in request.form and request.form["estado"] != "":
        consulta = consulta.filter_by(estado=request.form["estado"])
    # Luego filtrar por columnas de otras tablas
    if "quincena_clave" in request.form or "persona_rfc" in request.form:
        consulta = consulta.join(Nomina)
    if "quincena_clave" in request.form:
        try:
            quincena_clave = safe_quincena(request.form["quincena_clave"])
            consulta = consulta.join(Quincena)
            consulta = consulta.filter(Quincena.clave == quincena_clave)
        except ValueError:
            pass
    if "persona_rfc" in request.form:
        consulta = consulta.join(Persona)
        consulta = consulta.filter(Persona.rfc.contains(safe_rfc(request.form["persona_rfc"], search_fragment=True)))
    # Ordenar y paginar
    registros = consulta.order_by(Timbrado.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "tfd_uuid": resultado.tfd_uuid,
                    "url": url_for("timbrados.detail", timbrado_id=resultado.id),
                },
                "quincena_clave": resultado.nomina.quincena.clave,
                "persona_rfc": resultado.nomina.persona.rfc,
                "persona_nombre_completo": resultado.nomina.persona.nombre_completo,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@timbrados.route("/timbrados")
def list_active():
    """Listado de Timbrados activos"""
    return render_template(
        "timbrados/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Timbrados",
        estatus="A",
    )


@timbrados.route("/timbrados/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Timbrados inactivos"""
    return render_template(
        "timbrados/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Timbrados inactivos",
        estatus="B",
    )


@timbrados.route("/timbrados/<int:timbrado_id>")
def detail(timbrado_id):
    """Detalle de un Timbrado"""
    timbrado = Timbrado.query.get_or_404(timbrado_id)
    return render_template("timbrados/detail.jinja2", timbrado=timbrado)


@timbrados.route("/timbrados/<int:timbrado_id>/pdf")
def download_pdf(timbrado_id):
    """Descargar el archivo PDF de un Timbrado"""

    # Consultar el Timbrado
    timbrado = Timbrado.query.get_or_404(timbrado_id)

    # Si no tiene URL, regidir a la página de detalle
    if timbrado.url_pdf == "":
        flash("El Timbrado no tiene un archivo PDF", "warning")
        return redirect(url_for("timbrados.detail", nomina_id=timbrado.id))

    # Si no tiene nombre para el archivo en archivo_pdf, elaborar uno con el UUID
    descarga_nombre = timbrado.archivo_pdf
    if descarga_nombre == "":
        descarga_nombre = f"{timbrado.tfd_uuid}.pdf"

    # Obtener el contenido del archivo desde Google Storage
    try:
        descarga_contenido = get_file_from_gcs(
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO"],
            blob_name=get_blob_name_from_url(timbrado.url_pdf),
        )
    except MyAnyError as error:
        flash(str(error), "danger")
        return redirect(url_for("timbrados.detail", timbrado_id=timbrado.id))

    # Descargar un archivo PDF
    response = make_response(descarga_contenido)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"attachment; filename={descarga_nombre}"
    return response


@timbrados.route("/timbrados/<int:timbrado_id>/xml")
def download_xml(timbrado_id):
    """Descargar el archivo XML de un Timbrado"""

    # Consultar el Timbrado
    timbrado = Timbrado.query.get_or_404(timbrado_id)

    # Si no tiene URL, regidir a la página de detalle
    if timbrado.url_xml == "":
        flash("El Timbrado no tiene un archivo XML", "warning")
        return redirect(url_for("timbrados.detail", nomina_id=timbrado.id))

    # Si no tiene nombre para el archivo en archivo_xml, elaborar uno con el UUID
    descarga_nombre = timbrado.archivo_xml
    if descarga_nombre == "":
        descarga_nombre = f"{timbrado.tfd_uuid}.xml"

    # Obtener el contenido del archivo desde Google Storage
    try:
        descarga_contenido = get_file_from_gcs(
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO"],
            blob_name=get_blob_name_from_url(timbrado.url_xml),
        )
    except MyAnyError as error:
        flash(str(error), "danger")
        return redirect(url_for("timbrados.detail", timbrado_id=timbrado.id))

    # Descargar un archivo XML
    response = make_response(descarga_contenido)
    response.headers["Content-Type"] = "text/xml"
    response.headers["Content-Disposition"] = f"attachment; filename={descarga_nombre}"
    return response


@timbrados.route("/timbrados/eliminar/<int:timbrado_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(timbrado_id):
    """Eliminar un Timbrado"""
    timbrado = Timbrado.query.get_or_404(timbrado_id)
    if timbrado.estatus == "A":
        timbrado.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Timbrado {timbrado.id}"),
            url=url_for("timbrados.detail", timbrado_id=timbrado.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("timbrados.detail", timbrado_id=timbrado.id))


@timbrados.route("/timbrados/recuperar/<int:timbrado_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(timbrado_id):
    """Recuperar un Timbrado"""
    timbrado = Timbrado.query.get_or_404(timbrado_id)
    if timbrado.estatus == "B":
        timbrado.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Timbrado {timbrado.id}"),
            url=url_for("timbrados.detail", timbrado_id=timbrado.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("timbrados.detail", timbrado_id=timbrado.id))
