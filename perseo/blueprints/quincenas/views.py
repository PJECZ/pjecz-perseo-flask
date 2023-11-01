"""
Quincenas, vistas
"""
import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_quincena
from perseo.blueprints.permisos.models import Permiso
from perseo.blueprints.quincenas.models import Quincena
from perseo.blueprints.usuarios.decorators import permission_required

MODULO = "QUINCENAS"

quincenas = Blueprint("quincenas", __name__, template_folder="templates")


@quincenas.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@quincenas.route("/quincenas/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Quincenas"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Quincena.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "quincena" in request.form:
        try:
            consulta = consulta.filter_by(quincena=safe_quincena(request.form["quincena"]))
        except ValueError:
            pass
    # Ordenar y paginar
    registros = consulta.order_by(Quincena.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "quincena": resultado.quincena,
                    "url": url_for("quincenas.detail", quincena_id=resultado.id),
                },
                "estado": resultado.estado,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@quincenas.route("/quincenas")
def list_active():
    """Listado de Quincenas activas"""
    return render_template(
        "quincenas/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Quincenas",
        estatus="A",
    )


@quincenas.route("/quincenas/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Quincenas inactivas"""
    return render_template(
        "quincenas/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Quincenas inactivas",
        estatus="B",
    )


@quincenas.route("/quincenas/<int:quincena_id>")
def detail(quincena_id):
    """Detalle de una Quincena"""
    quincena = Quincena.query.get_or_404(quincena_id)
    return render_template("quincenas/detail.jinja2", quincena=quincena)


@quincenas.route("/quincenas/cerrar")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def close():
    """Lanzar tarea en el fondo para cerrar las quincenas pasadas, menos la ultima"""
    current_user.launch_task(comando="quincenas.tasks.cerrar", mensaje="Lanzando cerrar quincenas...")
    flash("Se ha lanzado la tarea en el fondo. Esta página se va a recargar en 10 segundos...", "info")
    return redirect(url_for("quincenas.list_active"))
