"""
Página inicial
"""

from flask import Blueprint, redirect, render_template, send_from_directory
from flask_login import current_user

sistemas = Blueprint("sistemas", __name__, template_folder="templates")


@sistemas.route("/")
def start():
    """Página inicial"""

    # Si el usuario está autenticado
    if current_user.is_authenticated:
        # Mostrar start.jinja2
        return render_template("sistemas/start.jinja2")

    # No está autenticado, debe de iniciar sesión
    return redirect("/login")


@sistemas.route("/favicon.ico")
def favicon():
    """Favicon"""
    return send_from_directory("static/img", "estrella.ico", mimetype="image/vnd.microsoft.icon")


@sistemas.app_errorhandler(400)
def bad_request(error):
    """Solicitud errónea"""
    return render_template("sistemas/403.jinja2", error=error), 403


@sistemas.app_errorhandler(401)
def unauthorized(error):
    """No autorizado"""
    return render_template("sistemas/403.jinja2"), 403


@sistemas.app_errorhandler(403)
def forbidden(error):
    """Acceso denegado"""
    return render_template("sistemas/403.jinja2"), 403


@sistemas.app_errorhandler(404)
def page_not_found(error):
    """Página no encontrada"""
    return render_template("sistemas/404.jinja2"), 404


@sistemas.app_errorhandler(413)
def request_entity_too_large(error):
    """Lo que se recibe sobrepasa la capacidad"""
    return render_template("sistemas/413.jinja2"), 413


@sistemas.app_errorhandler(500)
def internal_server_error(error):
    """Error del servidor"""
    return render_template("sistemas/500.jinja2"), 500
