"""
Usuarios
"""
import json

from flask import Blueprint, render_template

MODULO = "USUARIOS"

usuarios = Blueprint("usuarios", __name__, template_folder="templates")


@usuarios.route("/usuarios")
def list_active():
    """Listado de Usuarios activos"""
    return render_template(
        "usuarios/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Usuarios",
        estatus="A",
    )
