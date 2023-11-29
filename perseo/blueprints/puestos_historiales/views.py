"""
Puestos Historiales, vistas
"""
import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message, safe_string
from perseo.blueprints.bitacoras.models import Bitacora
from perseo.blueprints.modulos.models import Modulo
from perseo.blueprints.permisos.models import Permiso
from perseo.blueprints.puestos_historiales.models import PuestoHistorial
from perseo.blueprints.usuarios.decorators import permission_required

MODULO = "PUESTOS HISTORIALES"

puestos_historiales = Blueprint("puestos_historiales", __name__, template_folder="templates")


@puestos_historiales.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@puestos_historiales.route("/puestos_historiales/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Puestos Historiales"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = PuestoHistorial.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    # if "persona_id" in request.form:
    #     consulta = consulta.filter_by(persona_id=request.form["persona_id"])
    # Luego filtrar por columnas de otras tablas
    # if "persona_rfc" in request.form:
    #     consulta = consulta.join(Persona)
    #     consulta = consulta.filter(Persona.rfc.contains(safe_rfc(request.form["persona_rfc"], search_fragment=True)))
    # Ordenar y paginar
    registros = consulta.order_by(PuestoHistorial.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "nombre": resultado.nombre,
                    "url": url_for("puestos_historiales.detail", puesto_historial_id=resultado.id),
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@puestos_historiales.route("/puestos_historiales")
def list_active():
    """Listado de Puestos Historiales activos"""
    return render_template(
        "puestos_historiales/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Puestos Historiales",
        estatus="A",
    )


@puestos_historiales.route("/puestos_historiales/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Puestos Historiales inactivos"""
    return render_template(
        "puestos_historiales/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Puestos Historiales inactivos",
        estatus="B",
    )


@puestos_historiales.route("/puestos_historiales/<int:puesto_historial_id>")
def detail(puesto_historial_id):
    """Detalle de un Puesto Historial"""
    puesto_historial = PuestoHistorial.query.get_or_404(puesto_historial_id)
    return render_template("puestos_historiales/detail.jinja2", puesto_historial=puesto_historial)
