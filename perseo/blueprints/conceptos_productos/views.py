"""
Conceptos-Productos, vistas
"""
import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message, safe_string
from perseo.blueprints.bitacoras.models import Bitacora
from perseo.blueprints.conceptos_productos.models import ConceptoProducto
from perseo.blueprints.modulos.models import Modulo
from perseo.blueprints.permisos.models import Permiso
from perseo.blueprints.usuarios.decorators import permission_required

MODULO = "CONCEPTOS PRODUCTOS"

conceptos_productos = Blueprint("conceptos_productos", __name__, template_folder="templates")


@conceptos_productos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@conceptos_productos.route("/conceptos_productos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Conceptos-Productos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = ConceptoProducto.query
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    registros = consulta.order_by(ConceptoProducto.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("conceptos_productos.detail", concepto_producto_id=resultado.id),
                },
                "concepto": {
                    "clave": resultado.concepto.clave,
                    "url": url_for("conceptos.detail", concepto_id=resultado.concepto_id),
                },
                "producto": {
                    "clave": resultado.producto.clave,
                    "url": url_for("productos.detail", producto_id=resultado.producto_id),
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@conceptos_productos.route("/conceptos_productos")
def list_active():
    """Listado de Conceptos-Productos activos"""
    return render_template(
        "conceptos_productos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Conceptos-Productos",
        estatus="A",
    )


@conceptos_productos.route("/conceptos_productos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Conceptos-Productos inactivos"""
    return render_template(
        "conceptos_productos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Conceptos-Productos inactivos",
        estatus="B",
    )
