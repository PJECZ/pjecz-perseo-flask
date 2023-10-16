"""
Autoridades
"""
import json

from flask import Blueprint, render_template

MODULO = "AUTORIDADES"

autoridades = Blueprint("autoridades", __name__, template_folder="templates")


@autoridades.route("/autoridades")
def list_active():
    """Listado de Autoridades activas"""
    return render_template(
        "autoridades/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Autoridades",
        estatus="A",
    )
