"""
Percepciones Deducciones, vistas
"""
import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message, safe_string
from perseo.blueprints.bitacoras.models import Bitacora
from perseo.blueprints.modulos.models import Modulo
from perseo.blueprints.percepciones_deducciones.models import PercepcionDeduccion
from perseo.blueprints.permisos.models import Permiso
from perseo.blueprints.usuarios.decorators import permission_required

MODULO = "PERCEPCIONES DEDUCCIONES"

percepciones_deducciones = Blueprint("percepciones_deducciones", __name__, template_folder="templates")


@percepciones_deducciones.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@percepciones_deducciones.route("/percepciones_deducciones/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Percepciones Deducciones"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = PercepcionDeduccion.query
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    registros = consulta.order_by(PercepcionDeduccion.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "quincena": resultado.quincena,
                "importe": resultado.importe,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@percepciones_deducciones.route("/percepciones_deducciones")
def list_active():
    """Listado de Percepciones Deducciones activos"""
    return render_template(
        "percepciones_deducciones/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Percepciones Deducciones",
        estatus="A",
    )
