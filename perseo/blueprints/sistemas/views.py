"""
Sistemas
"""
from flask import Blueprint, redirect, render_template, send_from_directory
from flask_login import current_user

sistemas = Blueprint("sistemas", __name__, template_folder="templates")


@sistemas.route("/")
def start():
    """Pagina Inicial"""
    # Si el usuario está autenticado, mostrar inicio
    if current_user.is_authenticated:
        return render_template("sistemas/start.jinja2")

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
