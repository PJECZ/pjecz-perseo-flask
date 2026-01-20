"""
Usuarios-Roles
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ...lib.datatables import get_datatable_parameters, output_datatable_json
from ...lib.safe_string import safe_message
from ..bitacoras.models import Bitacora
from ..modulos.models import Modulo
from ..permisos.models import Permiso
from ..roles.models import Rol
from ..usuarios.decorators import permission_required
from ..usuarios.models import Usuario
from .forms import UsuarioRolNewWithRolForm, UsuarioRolNewWithUsuarioForm
from .models import UsuarioRol

MODULO = "USUARIOS ROLES"

usuarios_roles = Blueprint("usuarios_roles", __name__, template_folder="templates")


@usuarios_roles.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@usuarios_roles.route("/usuarios_roles/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Usuarios-Roles"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = UsuarioRol.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(UsuarioRol.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(UsuarioRol.estatus == "A")
    if "usuario_id" in request.form:
        consulta = consulta.filter(UsuarioRol.usuario_id == request.form["usuario_id"])
    if "rol_id" in request.form:
        consulta = consulta.filter(UsuarioRol.rol_id == request.form["rol_id"])
    # Paginar
    registros = consulta.offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": str(resultado.id),
                    "url": url_for("usuarios_roles.detail", usuario_rol_id=resultado.id),
                },
                "usuario": {
                    "email": resultado.usuario.email,
                    "url": url_for("usuarios.detail", usuario_id=resultado.usuario_id),
                },
                "usuario_nombre": resultado.usuario.nombre,
                "usuario_puesto": resultado.usuario.puesto,
                "rol": {
                    "nombre": resultado.rol.nombre,
                    "url": url_for("roles.detail", rol_id=resultado.rol_id),
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@usuarios_roles.route("/usuarios_roles")
def list_active():
    """Lista de usuarios-roles activos"""
    return render_template("usuarios_roles/list.jinja2", estatus="A", filtros={"estatus": "A"}, titulo="Usuarios-Roles")


@usuarios_roles.route("/usuarios_roles/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de usuarios-roles inactivos"""
    return render_template(
        "usuarios_roles/list.jinja2", estatus="B", filtros={"estatus": "B"}, titulo="Usuarios-Roles inactivos"
    )


@usuarios_roles.route("/usuarios_roles/<usuario_rol_id>")
def detail(usuario_rol_id):
    """Detalle de usuario-rol"""

    usuario_rol = UsuarioRol.query.get_or_404(usuario_rol_id)
    return render_template("usuarios_roles/detail.jinja2", usuario_rol=usuario_rol)


@usuarios_roles.route("/usuarios_roles/nuevo_con_rol/<rol_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new_with_rol(rol_id):
    """Nuevo Usuario-Rol con el rol como parametro"""

    rol = Rol.query.get_or_404(rol_id)
    form = UsuarioRolNewWithRolForm()
    if form.validate_on_submit():
        usuario = Usuario.query.get_or_404(form.usuario.data)
        descripcion = f"{usuario.email} en {rol.nombre}"
        usuario_rol_existente = UsuarioRol.query.filter(UsuarioRol.usuario == usuario).filter(UsuarioRol.rol == rol).first()
        if usuario_rol_existente is not None:
            if usuario_rol_existente.estatus == "B":
                usuario_rol_existente.estatus = "A"
                usuario_rol_existente.save()
                flash(f"Se ha recuperado {rol.nombre} en {usuario.email}.", "success")
            else:
                flash(f"Ya existe {rol.nombre} en {usuario.email}. Nada por hacer.", "warning")
            return redirect(url_for("usuarios_roles.detail", usuario_rol_id=usuario_rol_existente.id))
        usuario_rol = UsuarioRol(
            rol=rol,
            usuario=usuario,
            descripcion=descripcion,
        )
        usuario_rol.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo Usuario-Rol {usuario_rol.descripcion}"),
            url=url_for("roles.detail", rol_id=rol.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    form.rol_nombre.data = rol.nombre  # Solo lectura
    return render_template(
        "usuarios_roles/new_with_rol.jinja2",
        form=form,
        rol=rol,
        titulo=f"Agregar usuario al rol {rol.nombre}",
    )


@usuarios_roles.route("/usuarios_roles/nuevo_con_usuario/<usuario_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new_with_usuario(usuario_id):
    """Nuevo Usuario-Rol con el usuario como parametro"""

    usuario = Usuario.query.get_or_404(usuario_id)
    form = UsuarioRolNewWithUsuarioForm()
    if form.validate_on_submit():
        rol = Rol.query.get_or_404(form.rol.data)
        descripcion = f"{usuario.email} en {rol.nombre}"
        usuario_rol_existente = UsuarioRol.query.filter(UsuarioRol.usuario == usuario).filter(UsuarioRol.rol == rol).first()
        if usuario_rol_existente is not None:
            if usuario_rol_existente.estatus == "B":
                usuario_rol_existente.estatus = "A"
                usuario_rol_existente.save()
                flash(f"Se ha recuperado {rol.nombre} en {usuario.email}.", "success")
            else:
                flash(f"Ya existe {rol.nombre} en {usuario.email}. Nada por hacer.", "warning")
            return redirect(url_for("usuarios_roles.detail", usuario_rol_id=usuario_rol_existente.id))
        usuario_rol = UsuarioRol(
            rol=rol,
            usuario=usuario,
            descripcion=descripcion,
        )
        usuario_rol.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo Usuario-Rol {usuario_rol.descripcion}"),
            url=url_for("usuarios.detail", usuario_id=usuario.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    form.usuario_email.data = usuario.email  # Solo lectura
    form.usuario_nombre.data = usuario.nombre  # Solo lectura
    form.usuario_puesto.data = usuario.puesto  # Solo lectura
    return render_template(
        "usuarios_roles/new_with_usuario.jinja2",
        form=form,
        usuario=usuario,
        titulo=f"Agregar rol al usuario {usuario.email}",
    )


@usuarios_roles.route("/usuarios_roles/eliminar/<usuario_rol_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(usuario_rol_id):
    """Eliminar Usuario-Rol"""

    usuario_rol = UsuarioRol.query.get_or_404(usuario_rol_id)
    if usuario_rol.estatus == "A":
        usuario_rol.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Usuario-Rol {usuario_rol.descripcion}"),
            url=url_for("usuarios_roles.detail", usuario_rol_id=usuario_rol.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("usuarios_roles.detail", usuario_rol_id=usuario_rol.id))


@usuarios_roles.route("/usuarios_roles/recuperar/<usuario_rol_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(usuario_rol_id):
    """Recuperar Usuario-Rol"""

    usuario_rol = UsuarioRol.query.get_or_404(usuario_rol_id)
    if usuario_rol.estatus == "B":
        usuario_rol.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Usuario-Rol {usuario_rol.descripcion}"),
            url=url_for("usuarios_roles.detail", usuario_rol_id=usuario_rol.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("usuarios_roles.detail", usuario_rol_id=usuario_rol.id))


@usuarios_roles.route("/usuarios_roles/toggle_estatus_json/<usuario_rol_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.ADMINISTRAR)
def toggle_estatus_json(usuario_rol_id):
    """Cambiar el estatus de un usuario-rol por solicitud de botón en datatable"""

    # Consultar usuario-rol

    usuario_rol = UsuarioRol.query.get_or_404(usuario_rol_id)
    if usuario_rol is None:
        return {"success": False, "message": "No encontrado"}

    # Cambiar estatus a su opuesto
    if usuario_rol.estatus == "A":
        usuario_rol.estatus = "B"
    else:
        usuario_rol.estatus = "A"

    # Guardar
    usuario_rol.save()

    # Entregar JSON
    return {
        "success": True,
        "message": "Activo" if usuario_rol.estatus == "A" else "Inactivo",
        "estatus": usuario_rol.estatus,
        "id": usuario_rol.id,
    }
