"""
Usuarios, vistas
"""
import json
import os
import re
from datetime import datetime

import google.auth.transport.requests
import google.oauth2.id_token
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from pytz import timezone

from lib.firebase_auth import firebase_auth
from lib.safe_next_url import safe_next_url
from lib.safe_string import CONTRASENA_REGEXP, EMAIL_REGEXP, TOKEN_REGEXP
from perseo.blueprints.entradas_salidas.models import EntradaSalida
from perseo.blueprints.permisos.models import Permiso
from perseo.blueprints.usuarios.decorators import anonymous_required, permission_required
from perseo.blueprints.usuarios.forms import AccesoForm
from perseo.blueprints.usuarios.models import Usuario

HTTP_REQUEST = google.auth.transport.requests.Request()

MODULO = "USUARIOS"

usuarios = Blueprint("usuarios", __name__, template_folder="templates")


@usuarios.route("/login", methods=["GET", "POST"])
@anonymous_required()
def login():
    """Acceso al Sistema"""
    form = AccesoForm(siguiente=request.args.get("siguiente"))
    if form.validate_on_submit():
        # Tomar valores del formulario
        identidad = request.form.get("identidad")
        contrasena = request.form.get("contrasena")
        token = request.form.get("token")
        siguiente_url = request.form.get("siguiente")
        # Si esta definida la variable de entorno FIREBASE_APIKEY
        if os.environ.get("FIREBASE_APIKEY", "") != "":
            # Entonces debe ingresar con Google/Microsoft/GitHub
            if re.fullmatch(TOKEN_REGEXP, token) is not None:
                # Acceso por Firebase Auth
                claims = google.oauth2.id_token.verify_firebase_token(token, HTTP_REQUEST)
                if claims:
                    email = claims.get("email", "Unknown")
                    usuario = Usuario.find_by_identity(email)
                    if usuario and usuario.authenticated(with_password=False):
                        if login_user(usuario, remember=True) and usuario.is_active:
                            EntradaSalida(
                                usuario_id=usuario.id,
                                tipo="INGRESO",
                                direccion_ip=request.remote_addr,
                            ).save()
                            if siguiente_url:
                                return redirect(safe_next_url(siguiente_url))
                            return redirect(url_for("sistemas.start"))
                        else:
                            flash("No está activa esa cuenta.", "warning")
                    else:
                        flash("No existe esa cuenta.", "warning")
                else:
                    flash("Falló la autentificación.", "warning")
            else:
                flash("Token incorrecto.", "warning")
        else:
            # De lo contrario, el ingreso es con username/password
            if re.fullmatch(EMAIL_REGEXP, identidad) is None:
                flash("Correo electrónico no válido.", "warning")
            elif re.fullmatch(CONTRASENA_REGEXP, contrasena) is None:
                flash("Contraseña no válida.", "warning")
            else:
                usuario = Usuario.find_by_identity(identidad)
                if usuario and usuario.authenticated(password=contrasena):
                    if login_user(usuario, remember=True) and usuario.is_active:
                        EntradaSalida(
                            usuario_id=usuario.id,
                            tipo="INGRESO",
                            direccion_ip=request.remote_addr,
                        ).save()
                        if siguiente_url:
                            return redirect(safe_next_url(siguiente_url))
                        return redirect(url_for("sistemas.start"))
                    else:
                        flash("No está activa esa cuenta", "warning")
                else:
                    flash("Usuario o contraseña incorrectos.", "warning")
    return render_template("usuarios/login.jinja2", form=form, firebase_auth=firebase_auth, title="Plataforma Web")


@usuarios.route("/logout")
@login_required
def logout():
    """Salir del Sistema"""
    EntradaSalida(
        usuario_id=current_user.id,
        tipo="SALIO",
        direccion_ip=request.remote_addr,
    ).save()
    logout_user()
    flash("Ha salido de este sistema.", "success")
    return redirect(url_for("usuarios.login"))


@usuarios.route("/perfil")
@login_required
def profile():
    """Mostrar el Perfil"""
    ahora_utc = datetime.now(timezone("UTC"))
    ahora_mx_coah = ahora_utc.astimezone(timezone("America/Mexico_City"))
    formato_fecha = "%Y-%m-%d %H:%M %p"
    return render_template(
        "usuarios/profile.jinja2",
        ahora_utc_str=ahora_utc.strftime(formato_fecha),
        ahora_mx_coah_str=ahora_mx_coah.strftime(formato_fecha),
    )


@usuarios.route("/usuarios")
@login_required
@permission_required(MODULO, Permiso.VER)
def list_active():
    """Listado de Usuarios activos"""
    return render_template(
        "usuarios/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Usuarios",
        estatus="A",
    )


@usuarios.route("/usuarios/inactivos")
@login_required
@permission_required(MODULO, Permiso.MODIFICAR)
def list_inactive():
    """Listado de Usuarios inactivos"""
    return render_template(
        "usuarios/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Usuarios inactivos",
        estatus="B",
    )
