"""
Nominas, vistas
"""
import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message, safe_quincena, safe_rfc, safe_string
from perseo.blueprints.bitacoras.models import Bitacora
from perseo.blueprints.modulos.models import Modulo
from perseo.blueprints.nominas.models import Nomina
from perseo.blueprints.permisos.models import Permiso
from perseo.blueprints.personas.models import Persona
from perseo.blueprints.usuarios.decorators import permission_required

MODULO = "NOMINAS"

nominas = Blueprint("nominas", __name__, template_folder="templates")


@nominas.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@nominas.route("/nominas/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de nominas"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Nomina.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "quincena" in request.form:
        try:
            consulta = consulta.filter_by(quincena=safe_quincena(request.form["quincena"]))
        except ValueError:
            pass
    if "persona_id" in request.form:
        consulta = consulta.filter_by(persona_id=request.form["persona_id"])
    # Luego filtrar por columnas de otras tablas
    if "persona_rfc" in request.form:
        consulta = consulta.join(Persona)
        consulta = consulta.filter(Persona.rfc.contains(safe_rfc(request.form["persona_rfc"], search_fragment=True)))
    # Ordenar y paginar
    registros = consulta.order_by(Nomina.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("nominas.detail", nomina_id=resultado.id),
                },
                "quincena": resultado.quincena,
                "persona_rfc": resultado.persona.rfc,
                "persona_nombre_completo": resultado.persona.nombre_completo,
                "centro_trabajo_clave": resultado.centro_trabajo.clave,
                "plaza_clave": resultado.plaza.clave,
                "percepcion": resultado.percepcion,
                "deduccion": resultado.deduccion,
                "importe": resultado.importe,
                "tipo": resultado.tipo,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@nominas.route("/nominas")
def list_active():
    """Listado de Nominas activos"""
    return render_template(
        "nominas/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Nominas",
        estatus="A",
    )


@nominas.route("/nominas/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Nominas inactivos"""
    return render_template(
        "nominas/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Nominas inactivos",
        estatus="B",
    )


@nominas.route("/nominas/<int:nomina_id>")
def detail(nomina_id):
    """Detalle de un Nomina"""
    nomina = Nomina.query.get_or_404(nomina_id)
    return render_template("nominas/detail.jinja2", nomina=nomina)
