"""
Tabuladores, vistas
"""
import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_clave, safe_message, safe_string
from perseo.blueprints.bitacoras.models import Bitacora
from perseo.blueprints.modulos.models import Modulo
from perseo.blueprints.permisos.models import Permiso
from perseo.blueprints.puestos.models import Puesto
from perseo.blueprints.tabuladores.models import Tabulador
from perseo.blueprints.usuarios.decorators import permission_required

MODULO = "TABULADORES"

tabuladores = Blueprint("tabuladores", __name__, template_folder="templates")


@tabuladores.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@tabuladores.route("/tabuladores/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Tabuladores"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Tabulador.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "puesto_id" in request.form:
        consulta = consulta.filter_by(puesto_id=request.form["puesto_id"])
    if "modelo" in request.form:
        consulta = consulta.filter_by(modelo=request.form["modelo"])
    if "nivel" in request.form:
        consulta = consulta.filter_by(nivel=request.form["nivel"])
    if "quinquenio" in request.form:
        consulta = consulta.filter_by(quinquenio=request.form["quinquenio"])
    # Luego filtrar por columnas de otras tablas
    if "puesto_clave" in request.form:
        try:
            puesto_clave = safe_clave(request.form["puesto_clave"], max_len=24)
            if puesto_clave != "":
                consulta = consulta.join(Puesto)
                consulta = consulta.filter(Puesto.clave.contains(puesto_clave))
        except ValueError:
            pass
    # Ordenar y paginar
    registros = consulta.order_by(Tabulador.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("tabuladores.detail", tabulador_id=resultado.id),
                },
                "puesto": {
                    "clave": resultado.puesto.clave,
                    "url": url_for("puestos.detail", puesto_id=resultado.puesto_id),
                },
                "modelo": resultado.modelo,
                "nivel": resultado.nivel,
                "quinquenio": resultado.quinquenio,
                "fecha": resultado.fecha.strftime("%Y-%m-%d"),
                "sueldo_base": resultado.sueldo_base,
                "monedero": resultado.monedero,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@tabuladores.route("/tabuladores")
def list_active():
    """Listado de Tabuladores activos"""
    return render_template(
        "tabuladores/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Tabuladores",
        estatus="A",
    )


@tabuladores.route("/tabuladores/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Tabuladores inactivos"""
    return render_template(
        "tabuladores/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Tabuladores inactivos",
        estatus="B",
    )


@tabuladores.route("/tabuladores/<int:tabulador_id>")
def detail(tabulador_id):
    """Detalle de un Tabulador"""
    tabulador = Tabulador.query.get_or_404(tabulador_id)
    return render_template("tabuladores/detail.jinja2", tabulador=tabulador)
