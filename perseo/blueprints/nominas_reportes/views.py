"""
Nominas Reportes, vistas
"""
import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message, safe_string
from perseo.blueprints.bitacoras.models import Bitacora
from perseo.blueprints.modulos.models import Modulo
from perseo.blueprints.nominas_reportes.models import NominaReporte
from perseo.blueprints.permisos.models import Permiso
from perseo.blueprints.usuarios.decorators import permission_required

MODULO = "NOMINAS REPORTES"

nominas_reportes = Blueprint("nominas_reportes", __name__, template_folder="templates")


@nominas_reportes.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@nominas_reportes.route("/nominas_reportes/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Nominas Reportes"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = NominaReporte.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "nomina_id" in request.form:
        consulta = consulta.filter_by(nomina_id=request.form["nomina_id"])
    # Ordenar y paginar
    registros = consulta.order_by(NominaReporte.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "descripcion": resultado.descripcion,
                    "url": url_for("nominas_reportes.detail", nomina_reporte_id=resultado.id),
                },
                "mensaje": resultado.mensaje,
                "generado": {
                    "archivo": resultado.archivo,
                    "url": resultado.url,
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@nominas_reportes.route("/nominas_reportes")
def list_active():
    """Listado de Nominas Reportes activas"""
    return render_template(
        "nominas_reportes/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Nominas Reportes",
        estatus="A",
    )


@nominas_reportes.route("/nominas_reportes/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Nominas Reportes inactivas"""
    return render_template(
        "nominas_reportes/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Nominas Reportes inactivas",
        estatus="B",
    )


@nominas_reportes.route("/nominas_reportes/<int:nomina_reporte_id>")
def detail(nomina_reporte_id):
    """Detalle de una Nomina Reporte"""
    nomina_reporte = NominaReporte.query.get_or_404(nomina_reporte_id)
    return render_template("nominas_reportes/detail.jinja2", nomina_reporte=nomina_reporte)
