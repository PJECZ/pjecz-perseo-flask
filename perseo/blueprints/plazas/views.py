"""
Plazas, vistas
"""
import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message, safe_string
from perseo.blueprints.bitacoras.models import Bitacora
from perseo.blueprints.modulos.models import Modulo
from perseo.blueprints.permisos.models import Permiso
from perseo.blueprints.plazas.models import Plaza
from perseo.blueprints.usuarios.decorators import permission_required

MODULO = "PLAZAS"

plazas = Blueprint("plazas", __name__, template_folder="templates")


@plazas.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@plazas.route("/plazas/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Plazas"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Plaza.query
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    registros = consulta.order_by(Plaza.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "clave": resultado.clave,
                    "url": url_for("plazas.detail", plaza_id=resultado.id),
                },
                "descripcion": resultado.descripcion,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@plazas.route("/plazas")
def list_active():
    """Listado de Plazas activas"""
    return render_template(
        "plazas/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Plazas",
        estatus="A",
    )


@plazas.route("/plazas/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Plazas inactivas"""
    return render_template(
        "plazas/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Plazas inactivas",
        estatus="B",
    )
