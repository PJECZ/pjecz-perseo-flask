"""
Sistemas
"""
from flask import Blueprint, redirect, render_template, send_from_directory
from flask_login import current_user

from perseo.blueprints.quincenas.models import Quincena
from perseo.blueprints.quincenas_productos.models import QuincenaProducto
from perseo.extensions import socketio

sistemas = Blueprint("sistemas", __name__, template_folder="templates")


@socketio.on("connect")
def socketio_connect():
    """SocketIO Conexión"""
    print("Cliente conectado")


@socketio.on("test")
def socketio_test(data):
    """SocketIO Conexión"""
    print("Datos recibidos: " + str(data))


@sistemas.route("/")
def start():
    """Pagina Inicial"""
    # Si el usuario está autenticado
    if current_user.is_authenticated:
        # Consultar la ultima quincena
        quincena = Quincena.query.order_by(Quincena.id.desc()).first()

        # Inicializar variables
        quincena_producto_nominas = None
        quincena_producto_monederos = None
        quincena_producto_pensionados = None
        quincena_producto_dispersiones_pensionados = None

        # Si existe la ultima quincena
        if quincena:
            # Consultar el ultimo producto de quincenas con fuente NOMINAS
            quincena_producto_nominas = (
                QuincenaProducto.query.filter_by(quincena_id=quincena.id, fuente="NOMINAS", estatus="A")
                .order_by(QuincenaProducto.id.desc())
                .first()
            )

            # Consultar el ultimo producto de quincenas con fuente MONEDEROS
            quincena_producto_monederos = (
                QuincenaProducto.query.filter_by(quincena_id=quincena.id, fuente="MONEDEROS", estatus="A")
                .order_by(QuincenaProducto.id.desc())
                .first()
            )

            # Consultar el ultimo producto de quincenas con fuente PENSIONADOS
            quincena_producto_pensionados = (
                QuincenaProducto.query.filter_by(quincena_id=quincena.id, fuente="PENSIONADOS", estatus="A")
                .order_by(QuincenaProducto.id.desc())
                .first()
            )

            # Consultar el ultimo producto de quincenas con fuente DISPERSIONES PENSIONADOS
            quincena_producto_dispersiones_pensionados = (
                QuincenaProducto.query.filter_by(quincena_id=quincena.id, fuente="DISPERSIONES PENSIONADOS", estatus="A")
                .order_by(QuincenaProducto.id.desc())
                .first()
            )

        # Mostrar start.jinja2
        return render_template(
            "sistemas/start.jinja2",
            quincena=quincena,
            quincena_producto_nominas=quincena_producto_nominas,
            quincena_producto_monederos=quincena_producto_monederos,
            quincena_producto_pensionados=quincena_producto_pensionados,
            quincena_producto_dispersiones_pensionados=quincena_producto_dispersiones_pensionados,
        )

    # No está autenticado, debe de iniciar sesión
    return redirect("/login")


@sistemas.route("/favicon.ico")
def favicon():
    """Favicon"""
    return send_from_directory("static/img", "favicon.ico", mimetype="image/vnd.microsoft.icon")


@sistemas.app_errorhandler(400)
def bad_request(error):
    """Solicitud errónea"""
    return render_template("sistemas/403.jinja2", error=error), 403


@sistemas.app_errorhandler(403)
def forbidden(error):
    """Acceso no autorizado"""
    return render_template("sistemas/403.jinja2"), 403


@sistemas.app_errorhandler(404)
def page_not_found(error):
    """Error página no encontrada"""
    return render_template("sistemas/404.jinja2"), 404


@sistemas.app_errorhandler(500)
def internal_server_error(error):
    """Error del servidor"""
    return render_template("sistemas/500.jinja2"), 500
