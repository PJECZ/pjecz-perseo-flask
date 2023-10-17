"""
Roles, vistas
"""
import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message
from perseo.blueprints.bitacoras.models import Bitacora
from perseo.blueprints.modulos.models import Modulo
from perseo.blueprints.permisos.models import Permiso
from perseo.blueprints.roles.models import Rol
from perseo.blueprints.usuarios.decorators import permission_required

MODULO = "ROLES"

roles = Blueprint("roles", __name__, template_folder="templates")


@roles.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@roles.route("/roles/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Roles"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Rol.query
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    registros = consulta.order_by(Rol.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "nombre": resultado.nombre,
                    "url": url_for("roles.detail", rol_id=resultado.id),
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@roles.route("/roles")
def list_active():
    """Listado de Roles activos"""
    return render_template(
        "roles/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Roles",
        estatus="A",
    )


@roles.route("/roles/inactivos")
@permission_required(MODULO, Permiso.MODIFICAR)
def list_inactive():
    """Listado de Roles inactivos"""
    return render_template(
        "roles/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Roles inactivos",
        estatus="B",
    )


@roles.route("/roles/<int:rol_id>")
def detail(rol_id):
    """Detalle de un Rol"""
    rol = Rol.query.get_or_404(rol_id)
    return render_template("roles/detail.jinja2", rol=rol)


@roles.route("/roles/eliminar/<int:rol_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(rol_id):
    """Eliminar Rol"""
    rol = Rol.query.get_or_404(rol_id)
    if rol.estatus == "A":
        rol.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Rol {rol.nombre}"),
            url=url_for("roles.detail", rol_id=rol.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("roles.detail", rol_id=rol.id))


@roles.route("/roles/recuperar/<int:rol_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(rol_id):
    """Recuperar Rol"""
    rol = Rol.query.get_or_404(rol_id)
    if rol.estatus == "B":
        rol.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Rol {rol.nombre}"),
            url=url_for("roles.detail", rol_id=rol.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("roles.detail", rol_id=rol.id))
