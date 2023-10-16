"""
Permisos
"""
import json

from flask import Blueprint, render_template

MODULO = "PERMISOS"

permisos = Blueprint("permisos", __name__, template_folder="templates")


@permisos.route("/permisos")
def list_active():
    """Listado de Permisos activos"""
    return render_template(
        "permisos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Permisos",
        estatus="A",
    )
