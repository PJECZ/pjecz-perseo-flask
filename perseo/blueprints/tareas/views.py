"""
Tareas, vistas
"""
import json

from flask import Blueprint, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from perseo.blueprints.permisos.models import Permiso
from perseo.blueprints.tareas.models import Tarea
from perseo.blueprints.usuarios.decorators import permission_required

MODULO = "TAREAS"

tareas = Blueprint("tareas", __name__, template_folder="templates")


@tareas.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@tareas.route("/tareas/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Tareas"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Tarea.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "comando" in request.form:
        consulta = consulta.filter_by(comando=request.form["comando"])
    if "usuario_id" in request.form:
        consulta = consulta.filter_by(usuario_id=request.form["usuario_id"])
    # Ordenar y paginar
    registros = consulta.order_by(Tarea.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "creado": resultado.creado.strftime("%Y-%m-%d %H:%M:%S"),
                "usuario": {
                    "email": resultado.usuario.email,
                    "url": url_for("usuarios.detail", usuario_id=resultado.usuario_id)
                    if current_user.can_view("USUARIOS")
                    else "",
                },
                "comando": resultado.comando,
                "mensaje": resultado.mensaje,
                "ha_terminado": resultado.ha_terminado,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@tareas.route("/tareas")
def list_active():
    """Listado de Tareas activos"""
    return render_template(
        "tareas/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Tareas",
        estatus="A",
    )


@tareas.route("/tareas/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Tareas inactivos"""
    return render_template(
        "tareas/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Tareas inactivos",
        estatus="B",
    )
