"""
Cuentas, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ...lib.datatables import get_datatable_parameters, output_datatable_json
from ...lib.safe_string import safe_clave, safe_message, safe_rfc, safe_string
from ..bancos.models import Banco
from ..bitacoras.models import Bitacora
from ..modulos.models import Modulo
from ..permisos.models import Permiso
from ..personas.models import Persona
from ..usuarios.decorators import permission_required
from .forms import CuentaEditForm, CuentaNewWithPersonaForm
from .models import Cuenta

MODULO = "CUENTAS"

cuentas = Blueprint("cuentas", __name__, template_folder="templates")


@cuentas.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@cuentas.route("/cuentas/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de cuentas"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Cuenta.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "banco_id" in request.form:
        consulta = consulta.filter_by(banco_id=request.form["banco_id"])
    if "persona_id" in request.form:
        consulta = consulta.filter_by(persona_id=request.form["persona_id"])
    if "num_cuenta" in request.form:
        consulta = consulta.filter(Cuenta.num_cuenta.contains(safe_string(request.form["num_cuenta"])))
    # Luego filtrar por columnas de otras tablas
    if (
        "persona_rfc" in request.form
        or "persona_nombres" in request.form
        or "persona_apellido_primero" in request.form
        or "persona_apellido_segundo" in request.form
    ):
        consulta = consulta.join(Persona)
    if "persona_rfc" in request.form:
        consulta = consulta.filter(Persona.rfc.contains(safe_rfc(request.form["persona_rfc"], search_fragment=True)))
    if "persona_nombres" in request.form:
        consulta = consulta.filter(Persona.nombres.contains(safe_string(request.form["persona_nombres"], save_enie=True)))
    if "persona_apellido_primero" in request.form:
        consulta = consulta.filter(
            Persona.apellido_primero.contains(safe_string(request.form["persona_apellido_primero"], save_enie=True))
        )
    if "persona_apellido_segundo" in request.form:
        consulta = consulta.filter(
            Persona.apellido_segundo.contains(safe_string(request.form["persona_apellido_segundo"], save_enie=True))
        )
    # Ordenar y paginar
    registros = consulta.order_by(Cuenta.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("cuentas.detail", cuenta_id=resultado.id),
                },
                "persona_rfc": resultado.persona.rfc,
                "persona_nombre_completo": resultado.persona.nombre_completo,
                "banco_nombre": resultado.banco.nombre,
                "num_cuenta": resultado.num_cuenta,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@cuentas.route("/cuentas")
def list_active():
    """Listado de cuentas activos"""
    return render_template(
        "cuentas/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Cuentas",
        estatus="A",
    )


@cuentas.route("/cuentas/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de cuentas inactivos"""
    return render_template(
        "cuentas/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Cuentas inactivos",
        estatus="B",
    )


@cuentas.route("/cuentas/<int:cuenta_id>")
def detail(cuenta_id):
    """Detalle de un cuenta"""
    cuenta = Cuenta.query.get_or_404(cuenta_id)
    return render_template("cuentas/detail.jinja2", cuenta=cuenta)


@cuentas.route("/cuentas/exportar_xlsx")
@permission_required(MODULO, Permiso.VER)
def exportar_xlsx():
    """Lanzar tarea en el fondo para exportar las Cuentas a un archivo XLSX"""
    tarea = current_user.launch_task(
        comando="cuentas.tasks.lanzar_exportar_xlsx",
        mensaje="Exportando las Cuentas a un archivo XLSX...",
    )
    flash("Se ha lanzado esta tarea en el fondo. Esta página se va a recargar en 30 segundos...", "info")
    return redirect(url_for("tareas.detail", tarea_id=tarea.id))


@cuentas.route("/cuentas/nuevo_con_persona/<int:persona_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new_with_persona(persona_id):
    """Nueva Cuenta con Persona"""
    persona = Persona.query.get_or_404(persona_id)
    form = CuentaNewWithPersonaForm()
    if form.validate_on_submit():
        banco = Banco.query.get_or_404(form.banco.data)
        cuenta = Cuenta(
            banco=banco,
            persona=persona,
            num_cuenta=safe_clave(form.num_cuenta.data, max_len=24, only_digits=True, separator=""),
        )
        cuenta.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nueva Cuenta de {persona.rfc} en {banco.nombre} - {cuenta.num_cuenta}"),
            url=url_for("cuentas.detail", cuenta_id=cuenta.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    form.persona_rfc.data = persona.rfc  # Solo lectura
    form.persona_nombre.data = persona.nombre_completo  # Solo lectura
    return render_template(
        "cuentas/new_with_persona.jinja2",
        form=form,
        persona=persona,
        titulo=f"Nueva Cuenta para {persona.rfc}",
    )


@cuentas.route("/cuentas/edicion/<int:cuenta_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(cuenta_id):
    """Editar Cuenta"""
    cuenta = Cuenta.query.get_or_404(cuenta_id)
    form = CuentaEditForm()
    if form.validate_on_submit():
        cuenta.num_cuenta = safe_clave(form.num_cuenta.data, max_len=24, only_digits=True, separator="")
        cuenta.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Editada Cuenta de {cuenta.persona.rfc} en {cuenta.banco.nombre} {cuenta.num_cuenta}"),
            url=url_for("cuentas.detail", cuenta_id=cuenta.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    form.banco_nombre.data = cuenta.banco.nombre  # Solo lectura
    form.persona_rfc.data = cuenta.persona.rfc  # Solo lectura
    form.persona_nombre.data = cuenta.persona.nombre_completo  # Solo lectura
    form.num_cuenta.data = cuenta.num_cuenta
    return render_template("cuentas/edit.jinja2", form=form, cuenta=cuenta)


@cuentas.route("/cuentas/eliminar/<int:cuenta_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(cuenta_id):
    """Eliminar Cuenta"""
    cuenta = Cuenta.query.get_or_404(cuenta_id)
    if cuenta.estatus == "A":
        cuenta.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Cuenta de {cuenta.persona.rfc} en {cuenta.banco.nombre} {cuenta.num_cuenta}"),
            url=url_for("cuentas.detail", cuenta_id=cuenta.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("cuentas.detail", cuenta_id=cuenta.id))


@cuentas.route("/cuentas/recuperar/<int:cuenta_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(cuenta_id):
    """Recuperar Cuenta"""
    cuenta = Cuenta.query.get_or_404(cuenta_id)
    if cuenta.estatus == "B":
        cuenta.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperada Cuenta de {cuenta.persona.rfc} en {cuenta.banco.nombre} {cuenta.num_cuenta}"),
            url=url_for("cuentas.detail", cuenta_id=cuenta.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("cuentas.detail", cuenta_id=cuenta.id))
