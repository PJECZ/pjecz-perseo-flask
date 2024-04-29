"""
Bitácoras
"""

from flask import Blueprint, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_email, safe_string
from perseo.blueprints.bitacoras.models import Bitacora
from perseo.blueprints.modulos.models import Modulo
from perseo.blueprints.permisos.models import Permiso
from perseo.blueprints.usuarios.decorators import permission_required
from perseo.blueprints.usuarios.models import Usuario

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
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "modulo_id" in request.form:
        consulta = consulta.filter_by(modulo_id=request.form["modulo_id"])
    if "usuario_id" in request.form:
        consulta = consulta.filter_by(usuario_id=request.form["usuario_id"])
    # Luego filtrar por columnas de otras tablas
    if "modulo_nombre" in request.form:
        modulo_nombre = safe_string(request.form["modulo_nombre"], save_enie=True)
        if modulo_nombre != "":
            consulta = consulta.join(Modulo).filter(Modulo.nombre.contains(modulo_nombre))
    if "usuario_email" in request.form:
        try:
            usuario_email = safe_email(request.form["usuario_email"], search_fragment=True)
            if usuario_email != "":
                consulta = consulta.join(Usuario).filter(Usuario.email.contains(usuario_email))
        except ValueError:
            pass
    # Ordenar y paginar
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
                    "url": (
                        url_for("usuarios.detail", usuario_id=resultado.usuario_id) if current_user.can_view("USUARIOS") else ""
                    ),
                },
                "modulo": {
                    "nombre": resultado.modulo.nombre,
                    "url": url_for("modulos.detail", modulo_id=resultado.modulo_id) if current_user.can_view("MODULOS") else "",
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
