"""
Usuarios, vistas
"""

import json
import re
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from google.auth.transport.requests import Request
from google.oauth2.id_token import verify_firebase_token
from pytz import timezone

from ...config.firebase import get_firebase_settings
from ...lib.datatables import get_datatable_parameters, output_datatable_json
from ...lib.pwgen import generar_contrasena
from ...lib.safe_string import CONTRASENA_REGEXP, EMAIL_REGEXP, safe_email, safe_message, safe_string
from ...lib.safe_url import safe_next_url
from ..autoridades.models import Autoridad
from ..bitacoras.models import Bitacora
from ..distritos.models import Distrito
from ..modulos.models import Modulo
from ..permisos.models import Permiso
from .decorators import anonymous_required, permission_required
from .forms import AccesoForm, FirebaseForm, UsuarioForm
from .models import Usuario

MODULO = "USUARIOS"

usuarios = Blueprint("usuarios", __name__, template_folder="templates")


@usuarios.route("/login", methods=["GET", "POST"])
@anonymous_required()
def login():
    """Acceso al Sistema"""
    firebase_settings = get_firebase_settings()

    # Si está configurado Firebase, usar formulario identidad-contraseña
    if firebase_settings.APIKEY != "":
        form = FirebaseForm()
        # Si se recibe el formulario
        if form.validate_on_submit():
            identidad = str(form.identidad.data).strip()
            token = form.token.data
            siguiente = str(form.siguiente.data)
            # Si es válido el email
            if re.fullmatch(EMAIL_REGEXP, identidad) is not None:
                http_request = Request()
                try:
                    id_info = verify_firebase_token(token, http_request)
                except Exception as error:
                    id_info = None
                    flash(f"Error al verificar el token: {error}", "warning")
                # Si es válido el token y el email coincide con la identidad
                if id_info and id_info["email"] == identidad:
                    usuario = Usuario.find_by_identity(identidad)
                    # Si el usuario existe y está activo, hacer login
                    if usuario and usuario.estatus == "A" and login_user(usuario, remember=True):
                        if siguiente != "":
                            return redirect(safe_next_url(siguiente))
                        return redirect(url_for("sistemas.start"))
                    else:
                        flash("No está activa esa cuenta", "warning")
            else:
                flash("No es válido el correo electrónico o el token.", "warning")
        # Si viene el parámetro siguiente en la URL, agregarlo al formulario
        siguiente = request.args.get("siguiente")
        if siguiente is not None:
            form.siguiente.data = siguiente
        # Entregar formulario
        return render_template(
            "usuarios/login.jinja2",
            form=form,
            title="Plataforma Perseo",
            firebase_settings=firebase_settings,
        )
    else:
        form = AccesoForm(siguiente=request.args.get("siguiente"))
        # Si se recibe el formulario
        if form.validate_on_submit():
            correo_electronico = str(form.correo_electronico.data).strip()
            contrasena = str(form.contrasena.data).strip()
            siguiente = str(form.siguiente.data)
            # Si son válidos el email y la contraseña
            if re.fullmatch(EMAIL_REGEXP, correo_electronico) is None:
                flash("No es válido el correo electrónico.", "warning")
            elif re.fullmatch(CONTRASENA_REGEXP, contrasena) is None:
                flash("No es válida la contraseña.", "warning")
            else:
                usuario = Usuario.find_by_identity(correo_electronico)
                # Si el usuario existe y está activo, hacer login
                if usuario and usuario.authenticated(password=contrasena):
                    if usuario.estatus == "A" and login_user(usuario, remember=True):
                        if siguiente:
                            return redirect(safe_next_url(siguiente))
                        return redirect(url_for("sistemas.start"))
                    else:
                        flash("No está activa esa cuenta", "warning")
                else:
                    flash("Correo electrónico o contraseña incorrectos.", "warning")
        # Si viene el parámetro siguiente en la URL, agregarlo al formulario
        siguiente = request.args.get("siguiente")
        if siguiente is not None:
            form.siguiente.data = siguiente
        # Entregar formulario
        return render_template(
            "usuarios/login.jinja2",
            form=form,
            title="Plataforma Perseo",
            firebase_settings=None,
        )


@usuarios.route("/logout")
@login_required
def logout():
    """Salir del Sistema"""
    logout_user()
    flash("Ha salido del sistema.", "info")
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


@usuarios.route("/usuarios/datatable_json", methods=["GET", "POST"])
@login_required
@permission_required(MODULO, Permiso.VER)
def datatable_json():
    """DataTable JSON para listado de Usuarios"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Usuario.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(Usuario.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(Usuario.estatus == "A")
    if "autoridad_id" in request.form:
        consulta = consulta.filter(Usuario.autoridad_id == request.form["autoridad_id"])
    if "nombres" in request.form:
        nombres = safe_string(request.form["nombres"], save_enie=True)
        if nombres != "":
            consulta = consulta.filter(Usuario.nombres.contains(nombres))
    if "apellido_primero" in request.form:
        apellido_primero = safe_string(request.form["apellido_primero"], save_enie=True)
        if apellido_primero != "":
            consulta = consulta.filter(Usuario.apellido_primero.contains(apellido_primero))
    if "apellido_segundo" in request.form:
        apellido_segundo = safe_string(request.form["apellido_segundo"], save_enie=True)
        if apellido_segundo != "":
            consulta = consulta.filter(Usuario.apellido_segundo.contains(apellido_segundo))
    if "puesto" in request.form:
        puesto = safe_string(request.form["puesto"], save_enie=True)
        if puesto != "":
            consulta = consulta.filter(Usuario.puesto.contains(puesto))
    if "email" in request.form:
        email = safe_email(request.form["email"], search_fragment=True)
        if email != "":
            consulta = consulta.filter(Usuario.email.contains(email))
    # Ordenar y paginar
    registros = consulta.order_by(Usuario.email).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "email": resultado.email,
                    "url": url_for("usuarios.detail", usuario_id=resultado.id),
                },
                "nombre": resultado.nombre,
                "puesto": resultado.puesto,
                "autoridad": {
                    "clave": resultado.autoridad.clave,
                    "url": url_for("autoridades.detail", autoridad_id=resultado.autoridad_id),
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@usuarios.route("/usuarios")
@login_required
@permission_required(MODULO, Permiso.VER)
def list_active():
    """Lista de usuarios activos"""
    return render_template("usuarios/list.jinja2", estatus="A", filtros={"estatus": "A"}, titulo="Usuarios")


@usuarios.route("/usuarios/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de usuarios inactivos"""
    return render_template("usuarios/list.jinja2", estatus="B", filtros={"estatus": "B"}, titulo="Usuarios inactivos")


@usuarios.route("/usuarios/<usuario_id>")
@login_required
@permission_required(MODULO, Permiso.VER)
def detail(usuario_id):
    """Detalle de usuario"""

    usuario = Usuario.query.get_or_404(usuario_id)
    return render_template("usuarios/detail.jinja2", usuario=usuario)


@usuarios.route("/usuarios/nuevo", methods=["GET", "POST"])
@login_required
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo Usuario"""
    form = UsuarioForm()
    if form.validate_on_submit():
        es_valido = True
        # Validar que el email no se repita
        email = safe_email(form.email.data)
        if Usuario.query.filter_by(email=email).first():
            flash("El e-mail ya está en uso. Debe de ser único.", "warning")
            es_valido = False
        # Guardar
        if es_valido:
            usuario = Usuario(
                autoridad_id=form.autoridad.data,
                email=email,
                nombres=safe_string(form.nombres.data, save_enie=True),
                apellido_primero=safe_string(form.apellido_primero.data, save_enie=True),
                apellido_segundo=safe_string(form.apellido_segundo.data, save_enie=True),
                puesto=safe_string(form.puesto.data),
                api_key="",
                api_key_expiracion=datetime(year=2000, month=1, day=1, hour=0, minute=0, second=0),
                contrasena=generar_contrasena(),
            )
            usuario.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nuevo Usuario {usuario.email}"),
                url=url_for("usuarios.detail", usuario_id=usuario.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    # Consultar el distrito NO DEFINIDO
    distrito_no_definido_id = None
    distrito_no_definido = Distrito.query.filter_by(clave="ND").first()
    if distrito_no_definido:
        distrito_no_definido_id = str(distrito_no_definido.id)  # Es un SelectField
    # Consultar la autoridad NO DEFINIDO
    autoridad_no_definida_id = None
    autoridad_no_definida = Autoridad.query.filter_by(clave="ND").first()
    if autoridad_no_definida:
        autoridad_no_definida_id = str(autoridad_no_definida.id)  # Es un SelectField
    # Entregar formulario
    return render_template(
        "usuarios/new.jinja2",
        form=form,
        distrito_no_definido_id=distrito_no_definido_id,
        autoridad_no_definida_id=autoridad_no_definida_id,
    )


@usuarios.route("/usuarios/edicion/<usuario_id>", methods=["GET", "POST"])
@login_required
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(usuario_id):
    """Editar Usuario"""

    usuario = Usuario.query.get_or_404(usuario_id)
    form = UsuarioForm()
    if form.validate_on_submit():
        es_valido = True
        # Si cambia el e-mail verificar que no este en uso
        email = safe_email(form.email.data)
        if usuario.email != email:
            usuario_existente = Usuario.query.filter_by(email=email).first()
            if usuario_existente and usuario_existente.id != usuario.id:
                es_valido = False
                flash("La e-mail ya está en uso. Debe de ser único.", "warning")
        # Si es valido actualizar
        if es_valido:
            usuario.autoridad_id = form.autoridad.data  # Combo select distrito-autoridad
            usuario.email = email
            usuario.nombres = safe_string(form.nombres.data, save_enie=True)
            usuario.apellido_primero = safe_string(form.apellido_primero.data, save_enie=True)
            usuario.apellido_segundo = safe_string(form.apellido_segundo.data, save_enie=True)
            usuario.puesto = safe_string(form.puesto.data)
            usuario.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado Usuario {usuario.email}"),
                url=url_for("usuarios.detail", usuario_id=usuario.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    # No es necesario pasar autoridad_id porque se va a tomar de usuario con JS
    # Tampoco es necesario pasar oficina_id porque se va a tomar de usuario con JS
    form.email.data = usuario.email
    form.nombres.data = usuario.nombres
    form.apellido_primero.data = usuario.apellido_primero
    form.apellido_segundo.data = usuario.apellido_segundo
    form.puesto.data = usuario.puesto
    return render_template("usuarios/edit.jinja2", form=form, usuario=usuario)


@usuarios.route("/usuarios/eliminar/<usuario_id>")
@login_required
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(usuario_id):
    """Eliminar Usuario"""

    usuario = Usuario.query.get_or_404(usuario_id)
    if usuario.estatus == "A":
        # Dar de baja al usuario
        usuario.delete()
        # Dar de baja los roles del usuario
        for usuario_rol in usuario.usuarios_roles:
            usuario_rol.delete()
        # Guardar en la bitacora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Usuario {usuario.email}"),
            url=url_for("usuarios.detail", usuario_id=usuario.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("usuarios.detail", usuario_id=usuario.id))


@usuarios.route("/usuarios/recuperar/<usuario_id>")
@login_required
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(usuario_id):
    """Recuperar Usuario"""

    usuario = Usuario.query.get_or_404(usuario_id)
    if usuario.estatus == "B":
        # Recuperar al usuario
        usuario.recover()
        # Recuperar los roles del usuario
        for usuario_rol in usuario.usuarios_roles:
            usuario_rol.recover()
        # Guardar en la bitacora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Usuario {usuario.email}"),
            url=url_for("usuarios.detail", usuario_id=usuario.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("usuarios.detail", usuario_id=usuario.id))


@usuarios.route("/usuarios/select_json", methods=["GET", "POST"])
def select_json():
    """Proporcionar el JSON de usuarios para elegir con un select"""
    consulta = Usuario.query.filter_by(estatus="A").order_by(Usuario.email)
    data = []
    for resultado in consulta.all():
        data.append({"id": str(resultado.id), "texto": resultado.email})
    return json.dumps(data)


@usuarios.route("/usuarios/select2_json", methods=["POST"])
def select2_json():
    """Proporcionar el JSON de usuarios para elegir con un Select2, puede recibir parte del email a buscar"""
    consulta = Usuario.query.filter(Usuario.estatus == "A")
    if "searchString" in request.form:
        email = safe_email(request.form["searchString"], search_fragment=True)
        if email != "":
            consulta = consulta.filter(Usuario.email.contains(email))
    data = []
    for usuario in consulta.order_by(Usuario.email).limit(10).all():
        data.append({"id": str(usuario.id), "text": f"{usuario.email}: {usuario.nombre}"})
    return {"results": data, "pagination": {"more": False}}
