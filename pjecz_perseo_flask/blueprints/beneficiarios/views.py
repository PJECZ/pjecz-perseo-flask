"""
Beneficiarios, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ...lib.datatables import get_datatable_parameters, output_datatable_json
from ...lib.safe_string import safe_curp, safe_message, safe_rfc, safe_string
from ..bitacoras.models import Bitacora
from ..modulos.models import Modulo
from ..permisos.models import Permiso
from ..usuarios.decorators import permission_required
from .forms import BeneficiarioForm
from .models import Beneficiario

MODULO = "BENEFICIARIOS"

beneficiarios = Blueprint("beneficiarios", __name__, template_folder="templates")


@beneficiarios.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@beneficiarios.route("/beneficiarios/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Beneficiarios"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Beneficiario.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "rfc" in request.form:
        consulta = consulta.filter(Beneficiario.rfc.contains(safe_rfc(request.form["rfc"], search_fragment=True)))
    if "nombres" in request.form:
        consulta = consulta.filter(Beneficiario.nombres.contains(safe_string(request.form["nombres"])))
    if "apellido_primero" in request.form:
        consulta = consulta.filter(Beneficiario.apellido_primero.contains(safe_string(request.form["apellido_primero"])))
    if "apellido_segundo" in request.form:
        consulta = consulta.filter(Beneficiario.apellido_segundo.contains(safe_string(request.form["apellido_segundo"])))
    # Ordenar y paginar
    registros = consulta.order_by(Beneficiario.rfc).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "rfc": resultado.rfc,
                    "url": url_for("beneficiarios.detail", beneficiario_id=resultado.id),
                },
                "nombres": resultado.nombres,
                "apellido_primero": resultado.apellido_primero,
                "apellido_segundo": resultado.apellido_segundo,
                "curp": resultado.curp,
                "modelo": resultado.modelo,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@beneficiarios.route("/beneficiarios")
def list_active():
    """Listado de Beneficiarios activos"""
    return render_template(
        "beneficiarios/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Beneficiarios",
        estatus="A",
    )


@beneficiarios.route("/beneficiarios/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Beneficiarios inactivos"""
    return render_template(
        "beneficiarios/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Beneficiarios inactivos",
        estatus="B",
    )


@beneficiarios.route("/beneficiarios/<int:beneficiario_id>")
def detail(beneficiario_id):
    """Detalle de un Beneficiario"""
    beneficiario = Beneficiario.query.get_or_404(beneficiario_id)
    return render_template("beneficiarios/detail.jinja2", beneficiario=beneficiario)


@beneficiarios.route("/beneficiarios/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo Beneficiario"""
    form = BeneficiarioForm()
    if form.validate_on_submit():
        es_valido = True
        # Validar el RFC
        try:
            rfc = safe_rfc(form.rfc.data, is_optional=False)
        except ValueError:
            es_valido = False
            flash(safe_message("El RFC no es válido."), "warning")
        # Validar el CURP
        try:
            curp = safe_curp(form.curp.data, is_optional=True)
        except ValueError:
            es_valido = False
            flash(safe_message("El CURP no es válido."), "warning")
        # Validar que el RFC no se repita
        if Beneficiario.query.filter_by(rfc=rfc).first():
            es_valido = False
            flash(safe_message("El RFC ya está en uso. Debe de ser único."), "warning")
        # Validar que el CURP no se repita
        if curp != "" and Beneficiario.query.filter_by(curp=curp).first():
            es_valido = False
            flash(safe_message("El CURP ya está en uso. Debe de ser único."), "warning")
        # Si es válido, guardar
        if es_valido:
            beneficiario = Beneficiario(
                rfc=rfc,
                nombres=safe_string(form.nombres.data, save_enie=True),
                apellido_primero=safe_string(form.apellido_primero.data, save_enie=True),
                apellido_segundo=safe_string(form.apellido_segundo.data, save_enie=True),
                curp=curp,
                nacimiento_fecha=form.nacimiento_fecha.data,
                modelo=form.modelo.data,
            )
            beneficiario.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nuevo Beneficiario {beneficiario.rfc}"),
                url=url_for("beneficiarios.detail", beneficiario_id=beneficiario.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    return render_template("beneficiarios/new.jinja2", form=form)


@beneficiarios.route("/beneficiarios/edicion/<int:beneficiario_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(beneficiario_id):
    """Editar Beneficiario"""
    beneficiario = Beneficiario.query.get_or_404(beneficiario_id)
    form = BeneficiarioForm()
    if form.validate_on_submit():
        es_valido = True
        # Validar el RFC
        try:
            rfc = safe_rfc(form.rfc.data, is_optional=False)
        except ValueError:
            es_valido = False
            flash(safe_message("El RFC no es válido."), "warning")
        # Validar el CURP
        try:
            curp = safe_curp(form.curp.data, is_optional=True)
        except ValueError:
            es_valido = False
            flash(safe_message("El CURP no es válido."), "warning")
        # Si cambia el RFC verificar que no este en uso
        if beneficiario.rfc != rfc:
            beneficiario_existente = Beneficiario.query.filter_by(rfc=rfc).first()
            if beneficiario_existente and beneficiario_existente.id != beneficiario.id:
                es_valido = False
                flash("El RFC ya está en uso. Debe de ser único.", "warning")
        # Si cambia el CURP verificar que no este en uso
        if beneficiario.curp != curp and curp != "":
            beneficiario_existente = Beneficiario.query.filter_by(curp=curp).first()
            if beneficiario_existente and beneficiario_existente.id != beneficiario.id:
                es_valido = False
                flash("El CURP ya está en uso. Debe de ser único.", "warning")
        # Si es válido, guardar
        if es_valido:
            beneficiario.rfc = rfc
            beneficiario.nombres = safe_string(form.nombres.data, save_enie=True)
            beneficiario.apellido_primero = safe_string(form.apellido_primero.data, save_enie=True)
            beneficiario.apellido_segundo = safe_string(form.apellido_segundo.data, save_enie=True)
            beneficiario.curp = curp
            beneficiario.nacimiento_fecha = form.nacimiento_fecha.data
            beneficiario.modelo = form.modelo.data
            beneficiario.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado Beneficiario {beneficiario.rfc}"),
                url=url_for("beneficiarios.detail", beneficiario_id=beneficiario.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    form.rfc.data = beneficiario.rfc
    form.nombres.data = beneficiario.nombres
    form.apellido_primero.data = beneficiario.apellido_primero
    form.apellido_segundo.data = beneficiario.apellido_segundo
    form.curp.data = beneficiario.curp
    form.nacimiento_fecha.data = beneficiario.nacimiento_fecha
    form.modelo.data = beneficiario.modelo
    return render_template("beneficiarios/edit.jinja2", form=form, beneficiario=beneficiario)


@beneficiarios.route("/beneficiarios/eliminar/<int:beneficiario_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(beneficiario_id):
    """Eliminar Beneficiario"""
    beneficiario = Beneficiario.query.get_or_404(beneficiario_id)
    if beneficiario.estatus == "A":
        beneficiario.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Beneficiario {beneficiario.rfc}"),
            url=url_for("beneficiarios.detail", beneficiario_id=beneficiario.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("beneficiarios.detail", beneficiario_id=beneficiario.id))


@beneficiarios.route("/beneficiarios/recuperar/<int:beneficiario_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(beneficiario_id):
    """Recuperar Beneficiario"""
    beneficiario = Beneficiario.query.get_or_404(beneficiario_id)
    if beneficiario.estatus == "B":
        beneficiario.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Beneficiario {beneficiario.rfc}"),
            url=url_for("beneficiarios.detail", beneficiario_id=beneficiario.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("beneficiarios.detail", beneficiario_id=beneficiario.id))
