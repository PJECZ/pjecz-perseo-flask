"""
Roles
"""
import json

from flask import Blueprint, render_template

MODULO = "ROLES"

roles = Blueprint("roles", __name__, template_folder="templates")


@roles.route("/roles")
def list_active():
    """Listado de Roles activos"""
    return render_template(
        "roles/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Roles",
        estatus="A",
    )
