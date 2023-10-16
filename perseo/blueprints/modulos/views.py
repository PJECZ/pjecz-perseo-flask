"""
Modulos
"""
import json

from flask import Blueprint, render_template

MODULO = "MODULOS"

modulos = Blueprint("modulos", __name__, template_folder="templates")


@modulos.route("/modulos")
def list_active():
    """Listado de Modulos activos"""
    return render_template(
        "modulos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Módulos",
        estatus="A",
    )
