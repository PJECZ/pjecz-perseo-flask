"""
Distritos
"""
import json

from flask import Blueprint, render_template

MODULO = "DISTRITOS"

distritos = Blueprint("distritos", __name__, template_folder="templates")


@distritos.route("/distritos")
def list_active():
    """Listado de Distritos activos"""
    return render_template(
        "distritos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Distritos",
        estatus="A",
    )
