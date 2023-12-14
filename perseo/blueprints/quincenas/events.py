"""
Quincenas, eventos
"""
from flask import Blueprint
from flask_socketio import emit

from perseo.extensions import socketio

quincenas = Blueprint("quincenas_eventos", __name__, url_prefix="/quincenas_eventos")


@socketio.on("quincenas")
def handle_close_all(data):
    """Transmitir los datos de la tarea en el fondo para cerrar todas las quincenas"""
    print("Quincenas: ", data)


@quincenas.route("/cerrar_todas_json", methods=["GET", "POST"])
def recieve_close_all():
    """Recibir desde la tarea en el fondo para cerrar todas las quincenas"""
    print("Quincenas: received close all")
    data = {
        "success": True,
        "message": "Tarea finalizada",
    }
    emit("quincenas", data)
    return data
