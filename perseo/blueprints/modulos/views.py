"""
Modulos, vistas
"""
import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message
from perseo.blueprints.bitacoras.models import Bitacora
from perseo.blueprints.modulos.models import Modulo
from perseo.blueprints.permisos.models import Permiso
from perseo.blueprints.usuarios.decorators import permission_required

MODULO = "MODULOS"

modulos = Blueprint("modulos", __name__, template_folder="templates")


@modulos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@modulos.route("/modulos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Modulos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Modulo.query
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    registros = consulta.order_by(Modulo.nombre).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "nombre": resultado.nombre,
                    "url": url_for("modulos.detail", modulo_id=resultado.id),
                },
                "icono": resultado.icono,
                "en_navegacion": resultado.en_navegacion,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@modulos.route("/modulos")
def list_active():
    """Listado de Modulos activos"""
    return render_template(
        "modulos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Módulos",
        estatus="A",
    )


@modulos.route("/modulos/inactivos")
@permission_required(MODULO, Permiso.MODIFICAR)
def list_inactive():
    """Listado de Modulos inactivos"""
    return render_template(
        "modulos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Módulos inactivos",
        estatus="B",
    )


@modulos.route("/modulos/<int:modulo_id>")
def detail(modulo_id):
    """Detalle de un Modulo"""
    modulo = Modulo.query.get_or_404(modulo_id)
    return render_template("modulos/detail.jinja2", modulo=modulo)


@modulos.route("/modulos/eliminar/<int:modulo_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(modulo_id):
    """Eliminar Modulo"""
    este_modulo = Modulo.query.get_or_404(modulo_id)
    if este_modulo.estatus == "A":
        este_modulo.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Modulo {este_modulo.nombre}"),
            url=url_for("modulos.detail", modulo_id=este_modulo.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("modulos.detail", modulo_id=este_modulo.id))


@modulos.route("/modulos/recuperar/<int:modulo_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(modulo_id):
    """Recuperar Modulo"""
    este_modulo = Modulo.query.get_or_404(modulo_id)
    if este_modulo.estatus == "B":
        este_modulo.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Modulo {este_modulo.nombre}"),
            url=url_for("modulos.detail", modulo_id=este_modulo.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("modulos.detail", modulo_id=este_modulo.id))
