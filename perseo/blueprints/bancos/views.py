"""
Bancos, vistas
"""
import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message, safe_string
from perseo.blueprints.bancos.models import Banco
from perseo.blueprints.bitacoras.models import Bitacora
from perseo.blueprints.modulos.models import Modulo
from perseo.blueprints.permisos.models import Permiso
from perseo.blueprints.usuarios.decorators import permission_required

MODULO = "BANCO"

bancos = Blueprint("bancos", __name__, template_folder="templates")


@bancos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@bancos.route("/bancos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de bancos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Banco.query
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    registros = consulta.order_by(Banco.nombre).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "nombre": resultado.nombre,
                    "url": url_for("bancos.detail", banco_id=resultado.id),
                },
                "clave": resultado.clave,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@bancos.route("/bancos")
def list_active():
    """Listado de bancos activos"""
    return render_template(
        "bancos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="bancos",
        estatus="A",
    )


@bancos.route("/bancos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de bancos inactivos"""
    return render_template(
        "bancos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="bancos inactivos",
        estatus="B",
    )


@bancos.route("/bancos/<int:banco_id>")
def detail(banco_id):
    """Detalle de un banco"""
    banco = Banco.query.get_or_404(banco_id)
    return render_template("bancos/detail.jinja2", banco=banco)
