"""
Permisos
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ...lib.datatables import get_datatable_parameters, output_datatable_json
from ...lib.safe_string import safe_message, safe_string
from ..bitacoras.models import Bitacora
from ..modulos.models import Modulo
from ..roles.models import Rol
from ..usuarios.decorators import permission_required
from .forms import PermisoEditForm, PermisoNewWithModuloForm, PermisoNewWithRolForm
from .models import Permiso

MODULO = "PERMISOS"

permisos = Blueprint("permisos", __name__, template_folder="templates")


@permisos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@permisos.route("/permisos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Permisos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Permiso.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(Permiso.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(Permiso.estatus == "A")
    if "modulo_id" in request.form:
        consulta = consulta.filter(Permiso.modulo_id == request.form["modulo_id"])
    if "rol_id" in request.form:
        consulta = consulta.filter(Permiso.rol_id == request.form["rol_id"])
    if "nombre" in request.form:
        nombre = safe_string(request.form["nombre"], save_enie=True)
        if nombre != "":
            consulta = consulta.filter(Permiso.nombre.contains(nombre))
    # Ordenar y paginar
    registros = consulta.order_by(Permiso.nombre).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "nombre": resultado.nombre,
                    "url": url_for("permisos.detail", permiso_id=resultado.id),
                },
                "nivel": resultado.nivel_descrito,
                "modulo": {
                    "nombre": resultado.modulo.nombre,
                    "url": url_for("modulos.detail", modulo_id=resultado.modulo_id),
                },
                "rol": {
                    "nombre": resultado.rol.nombre,
                    "url": url_for("roles.detail", rol_id=resultado.rol_id),
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@permisos.route("/permisos")
def list_active():
    """Lista de permisos activos"""
    return render_template("permisos/list.jinja2", estatus="A", filtros={"estatus": "A"}, titulo="Permisos")


@permisos.route("/permisos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de permisos inactivos"""
    return render_template("permisos/list.jinja2", estatus="B", filtros={"estatus": "B"}, titulo="Permisos inactivos")


@permisos.route("/permisos/<permiso_id>")
def detail(permiso_id):
    """Detalle de permiso"""

    permiso = Permiso.query.get_or_404(permiso_id)
    return render_template("permisos/detail.jinja2", permiso=permiso)


@permisos.route("/permisos/nuevo_con_rol/<rol_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new_with_rol(rol_id):
    """Nuevo Permiso con Rol"""

    rol = Rol.query.get_or_404(rol_id)
    form = PermisoNewWithRolForm()
    if form.validate_on_submit():
        modulo = Modulo.query.get_or_404(form.modulo.data)
        nivel = form.nivel.data
        nombre = f"{rol.nombre} puede {Permiso.NIVELES[nivel]} en {modulo.nombre}"
        permiso_existente = Permiso.query.filter(Permiso.modulo == modulo).filter(Permiso.rol == rol).first()
        if permiso_existente is not None:
            if permiso_existente.estatus == "B":
                permiso_existente.nivel = nivel
                permiso_existente.estatus = "A"
                permiso_existente.save()
                flash(f"Se ha recuperado {nombre}.", "success")
            else:
                flash(f"Ya existe {nombre}. Nada por hacer.", "warning")
            return redirect(url_for("permisos.detail", permiso_id=permiso_existente.id))
        permiso = Permiso(
            modulo=modulo,
            rol=rol,
            nombre=nombre,
            nivel=nivel,
        )
        permiso.save()
        flash(safe_message(f"Nuevo permiso {nombre}"), "success")
        return redirect(url_for("roles.detail", rol_id=rol.id))
    form.rol.data = rol.nombre  # Solo lectura
    return render_template(
        "permisos/new_with_rol.jinja2",
        form=form,
        rol=rol,
        titulo=f"Agregar permiso al rol {rol.nombre}",
    )


@permisos.route("/permisos/nuevo_con_modulo/<modulo_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new_with_modulo(modulo_id):
    """Nuevo Permiso con Modulo"""

    modulo = Modulo.query.get_or_404(modulo_id)
    form = PermisoNewWithModuloForm()
    if form.validate_on_submit():
        rol = Rol.query.get_or_404(form.rol.data)
        nivel = form.nivel.data
        nombre = f"{rol.nombre} puede {Permiso.NIVELES[nivel]} en {modulo.nombre}"
        permiso_existente = Permiso.query.filter(Permiso.modulo == modulo).filter(Permiso.rol == rol).first()
        if permiso_existente is not None:
            if permiso_existente.estatus == "B":
                permiso_existente.nivel = nivel
                permiso_existente.estatus = "A"
                permiso_existente.save()
                flash(f"Se ha recuperado {nombre}.", "success")
            else:
                flash(f"Ya existe {nombre}. Nada por hacer.", "warning")
            return redirect(url_for("permisos.detail", permiso_id=permiso_existente.id))
        permiso = Permiso(
            modulo=modulo,
            rol=rol,
            nombre=nombre,
            nivel=nivel,
        )
        permiso.save()
        flash(safe_message(f"Nuevo permiso {nombre}"), "success")
        return redirect(url_for("modulos.detail", modulo_id=modulo.id))
    form.modulo.data = modulo.nombre  # Solo lectura
    return render_template(
        "permisos/new_with_modulo.jinja2",
        form=form,
        modulo=modulo,
        titulo=f"Agregar permiso al módulo {modulo.nombre}",
    )


@permisos.route("/permisos/edicion/<permiso_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(permiso_id):
    """Editar Permiso"""

    permiso = Permiso.query.get_or_404(permiso_id)
    form = PermisoEditForm()
    if form.validate_on_submit():
        permiso.nivel = form.nivel.data
        permiso.nombre = f"{permiso.rol.nombre} puede {Permiso.NIVELES[permiso.nivel]} en {permiso.modulo.nombre}"
        permiso.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Editado Permiso {permiso.nombre}"),
            url=url_for("permisos.detail", permiso_id=permiso.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    form.modulo.data = permiso.modulo.nombre  # Solo lectura
    form.rol.data = permiso.rol.nombre  # Solo lectura
    form.nivel.data = permiso.nivel
    return render_template("permisos/edit.jinja2", form=form, permiso=permiso)


@permisos.route("/permisos/eliminar/<permiso_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(permiso_id):
    """Eliminar Permiso"""

    permiso = Permiso.query.get_or_404(permiso_id)
    if permiso.estatus == "A":
        permiso.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Permiso {permiso.nombre}"),
            url=url_for("permisos.detail", permiso_id=permiso.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("permisos.detail", permiso_id=permiso.id))


@permisos.route("/permisos/recuperar/<permiso_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(permiso_id):
    """Recuperar Permiso"""

    permiso = Permiso.query.get_or_404(permiso_id)
    if permiso.estatus == "B":
        permiso.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Permiso {permiso.nombre}"),
            url=url_for("permisos.detail", permiso_id=permiso.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("permisos.detail", permiso_id=permiso.id))
