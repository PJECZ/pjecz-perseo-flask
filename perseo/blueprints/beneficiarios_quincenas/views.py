"""
Beneficiarios Quincenas, vistas
"""
import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message, safe_string
from perseo.blueprints.beneficiarios_quincenas.models import BeneficiarioQuincena
from perseo.blueprints.bitacoras.models import Bitacora
from perseo.blueprints.modulos.models import Modulo
from perseo.blueprints.permisos.models import Permiso
from perseo.blueprints.usuarios.decorators import permission_required

MODULO = "BENEFICIARIOS QUINCENAS"

beneficiarios_quincenas = Blueprint("beneficiarios_quincenas", __name__, template_folder="templates")


@beneficiarios_quincenas.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@beneficiarios_quincenas.route("/beneficiarios_quincenas/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Beneficiarios Quincenas"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = BeneficiarioQuincena.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "beneficiario_id" in request.form:
        consulta = consulta.filter_by(beneficiario_id=request.form["beneficiario_id"])
    # Ordenar y paginar
    registros = consulta.order_by(BeneficiarioQuincena.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("beneficiarios_quincenas.detail", beneficiario_quincena_id=resultado.id),
                },
                "quincena": resultado.quincena,
                "beneficiario_rfc": resultado.beneficiario.rfc,
                "beneficiario_nombre_completo": resultado.beneficiario.nombre_completo,
                "importe": resultado.importe,
                "num_cheque": resultado.num_cheque,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@beneficiarios_quincenas.route("/beneficiarios_quincenas")
def list_active():
    """Listado de Beneficiarios Quincenas activos"""
    return render_template(
        "beneficiarios_quincenas/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Beneficiarios Quincenas",
        estatus="A",
    )


@beneficiarios_quincenas.route("/beneficiarios_quincenas/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Beneficiarios Quincenas inactivos"""
    return render_template(
        "beneficiarios_quincenas/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Beneficiarios Quincenas inactivos",
        estatus="B",
    )


@beneficiarios_quincenas.route("/beneficiarios_quincenas/<int:beneficiario_quincena_id>")
def detail(beneficiario_quincena_id):
    """Detalle de un Beneficiario Quincena"""
    beneficiario_quincena = BeneficiarioQuincena.query.get_or_404(beneficiario_quincena_id)
    return render_template("beneficiarios_quincenas/detail.jinja2", beneficiario_quincena=beneficiario_quincena)
