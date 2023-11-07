"""
Beneficiarios, vistas
"""
import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message, safe_rfc, safe_string
from perseo.blueprints.beneficiarios.models import Beneficiario
from perseo.blueprints.bitacoras.models import Bitacora
from perseo.blueprints.modulos.models import Modulo
from perseo.blueprints.permisos.models import Permiso
from perseo.blueprints.usuarios.decorators import permission_required

MODULO = "BENEFICIARIOS"

beneficiarios = Blueprint("beneficiarios", __name__, template_folder="templates")


@beneficiarios.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@beneficiarios.route("/beneficiarios/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Beneficiarios"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Beneficiario.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "rfc" in request.form:
        try:
            consulta = consulta.filter(Beneficiario.rfc.contains(safe_rfc(request.form["rfc"], search_fragment=True)))
        except ValueError:
            pass
    if "nombres" in request.form:
        consulta = consulta.filter(Beneficiario.nombres.contains(safe_string(request.form["nombres"])))
    if "apellido_primero" in request.form:
        consulta = consulta.filter(Beneficiario.apellido_primero.contains(safe_string(request.form["apellido_primero"])))
    if "apellido_segundo" in request.form:
        consulta = consulta.filter(Beneficiario.apellido_segundo.contains(safe_string(request.form["apellido_segundo"])))
    # Ordenar y paginar
    registros = consulta.order_by(Beneficiario.rfc).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "rfc": resultado.rfc,
                    "url": url_for("beneficiarios.detail", beneficiario_id=resultado.id),
                },
                "nombres": resultado.nombres,
                "apellido_primero": resultado.apellido_primero,
                "apellido_segundo": resultado.apellido_segundo,
                "curp": resultado.curp,
                "modelo": resultado.modelo,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@beneficiarios.route("/beneficiarios")
def list_active():
    """Listado de Beneficiarios activos"""
    return render_template(
        "beneficiarios/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Beneficiarios",
        estatus="A",
    )


@beneficiarios.route("/beneficiarios/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Beneficiarios inactivos"""
    return render_template(
        "beneficiarios/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Beneficiarios inactivos",
        estatus="B",
    )


@beneficiarios.route("/beneficiarios/<int:beneficiario_id>")
def detail(beneficiario_id):
    """Detalle de un Beneficiario"""
    beneficiario = Beneficiario.query.get_or_404(beneficiario_id)
    return render_template("beneficiarios/detail.jinja2", beneficiario=beneficiario)
