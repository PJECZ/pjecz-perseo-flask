"""
Bitácoras
"""
from flask import Blueprint, render_template, request, url_for
from flask_login import login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from perseo.blueprints.bitacoras.models import Bitacora
from perseo.blueprints.permisos.models import Permiso
from perseo.blueprints.usuarios.decorators import permission_required

MODULO = "BITACORAS"

bitacoras = Blueprint("bitacoras", __name__, template_folder="templates")


@bitacoras.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@bitacoras.route("/bitacoras/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Bitacoras"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Bitacora.query
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    registros = consulta.order_by(Bitacora.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "creado": resultado.creado.strftime("%Y-%m-%d %H:%M:%S"),
                "usuario": {
                    "email": resultado.usuario.email,
                    "url": url_for("usuarios.detail", usuario_id=resultado.usuario_id),
                },
                "vinculo": {
                    "descripcion": resultado.descripcion,
                    "url": resultado.url,
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@bitacoras.route("/bitacoras")
def list_active():
    """Listado de Bitácoras activas"""
    return render_template("bitacoras/list.jinja2")
