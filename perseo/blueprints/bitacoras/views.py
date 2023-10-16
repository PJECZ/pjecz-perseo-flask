"""
Bitácoras
"""
import json

from flask import Blueprint, render_template

MODULO = "BITACORAS"

bitacoras = Blueprint("bitacoras", __name__, template_folder="templates")


@bitacoras.route("/bitacoras")
def list_active():
    """Listado de Bitácoras activas"""
    return render_template(
        "bitacoras/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Bitácoras",
        estatus="A",
    )
