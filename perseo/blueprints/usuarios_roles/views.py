"""
Usuarios-Roles
"""
import json

from flask import Blueprint, render_template

MODULO = "USUARIOS ROLES"

usuarios_roles = Blueprint("usuarios_roles", __name__, template_folder="templates")


@usuarios_roles.route("/usuarios_roles")
def list_active():
    """Listado de Usuarios-Roles activos"""
    return render_template(
        "usuarios_roles/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Usuarios-Roles",
        estatus="A",
    )
