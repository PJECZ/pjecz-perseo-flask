"""
Entradas-Salidas
"""
import json

from flask import Blueprint, render_template

MODULO = "ENTRADAS SALIDAS"

entradas_salidas = Blueprint("entradas_salidas", __name__, template_folder="templates")


@entradas_salidas.route("/entradas_salidas")
def list_active():
    """Listado de Entradas-Salidas activos"""
    return render_template(
        "entradas_salidas/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Entradas-Salidas",
        estatus="A",
    )
