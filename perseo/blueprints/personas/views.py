"""
Personas, vistas
"""
import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message, safe_string
from perseo.blueprints.bitacoras.models import Bitacora
from perseo.blueprints.modulos.models import Modulo
from perseo.blueprints.permisos.models import Permiso
from perseo.blueprints.personas.models import Persona
from perseo.blueprints.usuarios.decorators import permission_required

MODULO = "PERSONAS"

personas = Blueprint("personas", __name__, template_folder="templates")


@personas.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@personas.route("/personas/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Personas"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Persona.query
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    registros = consulta.order_by(Persona.rfc).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "nombres": resultado.nombres,
                "apellido_primero": resultado.apellido_primero,
                "apellido_segundo": resultado.apellido_segundo,
                "rfc": resultado.rfc,
                "curp": resultado.curp,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@personas.route("/personas")
def list_active():
    """Listado de Personas activas"""
    return render_template(
        "personas/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Personas",
        estatus="A",
    )
