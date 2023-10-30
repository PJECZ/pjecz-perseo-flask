"""
Cuentas, vistas
"""
import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message, safe_string
from perseo.blueprints.bitacoras.models import Bitacora
from perseo.blueprints.cuentas.models import Cuenta
from perseo.blueprints.modulos.models import Modulo
from perseo.blueprints.permisos.models import Permiso
from perseo.blueprints.usuarios.decorators import permission_required

MODULO = "CUENTAS"

cuentas = Blueprint("cuentas", __name__, template_folder="templates")


@cuentas.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@cuentas.route("/cuentas/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de cuentas"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Cuenta.query
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    registros = consulta.order_by(Cuenta.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "nombre": resultado.nombre,
                    "url": url_for("cuentas.detail", cuenta_id=resultado.id),
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@cuentas.route("/cuentas")
def list_active():
    """Listado de cuentas activos"""
    return render_template(
        "cuentas/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="cuentas",
        estatus="A",
    )


@cuentas.route("/cuentas/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de cuentas inactivos"""
    return render_template(
        "cuentas/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="cuentas inactivos",
        estatus="B",
    )


@cuentas.route("/cuentas/<int:cuenta_id>")
def detail(cuenta_id):
    """Detalle de un cuenta"""
    cuenta = Cuenta.query.get_or_404(cuenta_id)
    return render_template("cuentas/detail.jinja2", cuenta=cuenta)
