"""
Puestos, vistas
"""
import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_clave, safe_message, safe_string
from perseo.blueprints.bitacoras.models import Bitacora
from perseo.blueprints.modulos.models import Modulo
from perseo.blueprints.permisos.models import Permiso
from perseo.blueprints.puestos.models import Puesto
from perseo.blueprints.usuarios.decorators import permission_required

MODULO = "PUESTOS"

puestos = Blueprint("puestos", __name__, template_folder="templates")


@puestos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@puestos.route("/puestos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Puestos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Puesto.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "clave" in request.form:
        consulta = consulta.filter(Puesto.clave.contains(safe_clave(request.form["clave"], max_len=24)))
    if "descripcion" in request.form:
        consulta = consulta.filter(Puesto.descripcion.contains(safe_string(request.form["descripcion"])))
    # Ordenar y paginar
    registros = consulta.order_by(Puesto.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "clave": resultado.clave,
                    "url": url_for("puestos.detail", puesto_id=resultado.id),
                },
                "descripcion": resultado.descripcion,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@puestos.route("/puestos")
def list_active():
    """Listado de Puestos activos"""
    return render_template(
        "puestos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Puestos",
        estatus="A",
    )


@puestos.route("/puestos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Puestos inactivos"""
    return render_template(
        "puestos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Puestos inactivos",
        estatus="B",
    )


@puestos.route("/puestos/<int:puesto_id>")
def detail(puesto_id):
    """Detalle de un Puesto"""
    puesto = Puesto.query.get_or_404(puesto_id)
    return render_template("puestos/detail.jinja2", puesto=puesto)
