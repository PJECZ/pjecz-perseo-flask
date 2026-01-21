"""
Distritos
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ...lib.datatables import get_datatable_parameters, output_datatable_json
from ...lib.safe_string import safe_clave, safe_message, safe_string
from ..bitacoras.models import Bitacora
from ..modulos.models import Modulo
from ..permisos.models import Permiso
from ..usuarios.decorators import permission_required
from .forms import DistritoForm
from .models import Distrito

MODULO = "DISTRITOS"

distritos = Blueprint("distritos", __name__, template_folder="templates")


@distritos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@distritos.route("/distritos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Distritos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Distrito.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "clave" in request.form:
        clave = safe_clave(request.form["clave"])
        if clave != "":
            consulta = consulta.filter(Distrito.clave.contains(clave))
    if "nombre" in request.form:
        nombre = safe_string(request.form["nombre"], save_enie=True)
        if nombre != "":
            consulta = consulta.filter(Distrito.nombre.contains(nombre))
    # Ordenar y paginar
    registros = consulta.order_by(Distrito.clave).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "clave": resultado.clave,
                    "url": url_for("distritos.detail", distrito_id=resultado.id),
                },
                "nombre": resultado.nombre,
                "nombre_corto": resultado.nombre_corto,
                "es_distrito": resultado.es_distrito,
                "es_jurisdiccional": resultado.es_jurisdiccional,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@distritos.route("/distritos")
def list_active():
    """Lista de distritos activos"""
    return render_template("distritos/list.jinja2", estatus="A", filtros={"estatus": "A"}, titulo="Distritos")


@distritos.route("/distritos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de distritos inactivos"""
    return render_template("distritos/list.jinja2", estatus="B", filtros={"estatus": "B"}, titulo="distritos inactivos")


@distritos.route("/distritos/<distrito_id>")
def detail(distrito_id):
    """Detalle de distrito"""
    distrito = Distrito.query.get_or_404(distrito_id)
    return render_template("distritos/detail.jinja2", distrito=distrito)


@distritos.route("/distritos/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo Distrito"""
    form = DistritoForm()
    if form.validate_on_submit():
        es_valido = True
        # Validar que la clave no se repita
        clave = safe_clave(form.clave.data)
        if Distrito.query.filter_by(clave=clave).first():
            flash("La clave ya está en uso. Debe de ser única.", "warning")
            es_valido = False
        # Validar que el nombre no se repita
        nombre = safe_string(form.nombre.data, save_enie=True)
        if Distrito.query.filter_by(nombre=nombre).first():
            flash("La nombre ya está en uso. Debe de ser único.", "warning")
            es_valido = False
        # Si es válido, guardar
        if es_valido is True:
            distrito = Distrito(
                clave=clave,
                nombre=nombre,
                nombre_corto=safe_string(form.nombre_corto.data, save_enie=True),
                es_distrito=form.es_distrito.data,
                es_jurisdiccional=form.es_jurisdiccional.data,
            )
            distrito.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nuevo Distrito {distrito.clave}"),
                url=url_for("distritos.detail", distrito_id=distrito.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    return render_template("distritos/new.jinja2", form=form)


@distritos.route("/distritos/edicion/<distrito_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(distrito_id):
    """Editar Distrito"""

    distrito = Distrito.query.get_or_404(distrito_id)
    form = DistritoForm()
    if form.validate_on_submit():
        es_valido = True
        # Si cambia la clave verificar que no este en uso
        clave = safe_clave(form.clave.data)
        if distrito.clave != clave:
            distrito_existente = Distrito.query.filter_by(clave=clave).first()
            if distrito_existente and distrito_existente.id != distrito.id:
                es_valido = False
                flash("La clave ya está en uso. Debe de ser única.", "warning")
        # Si cambia el nombre verificar que no este en uso
        nombre = safe_string(form.nombre.data, save_enie=True)
        if distrito.nombre != nombre:
            distrito_existente = Distrito.query.filter_by(nombre=nombre).first()
            if distrito_existente and distrito_existente.id != distrito.id:
                es_valido = False
                flash("El nombre ya está en uso. Debe de ser único.", "warning")
        # Si es válido, actualizar
        if es_valido:
            distrito.clave = clave
            distrito.nombre = nombre
            distrito.nombre_corto = safe_string(form.nombre_corto.data, save_enie=True)
            distrito.es_distrito = form.es_distrito.data
            distrito.es_jurisdiccional = form.es_jurisdiccional.data
            distrito.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado Distrito {distrito.clave}"),
                url=url_for("distritos.detail", distrito_id=distrito.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    form.clave.data = distrito.clave
    form.nombre.data = distrito.nombre
    form.nombre_corto.data = distrito.nombre_corto
    form.es_distrito.data = distrito.es_distrito
    form.es_jurisdiccional.data = distrito.es_jurisdiccional
    return render_template("distritos/edit.jinja2", form=form, distrito=distrito)


@distritos.route("/distritos/eliminar/<distrito_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(distrito_id):
    """Eliminar Distrito"""

    distrito = Distrito.query.get_or_404(distrito_id)
    if distrito.estatus == "A":
        distrito.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Distrito {distrito.clave}"),
            url=url_for("distritos.detail", distrito_id=distrito.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("distritos.detail", distrito_id=distrito.id))


@distritos.route("/distritos/recuperar/<distrito_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(distrito_id):
    """Recuperar Distrito"""

    distrito = Distrito.query.get_or_404(distrito_id)
    if distrito.estatus == "B":
        distrito.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Distrito {distrito.clave}"),
            url=url_for("distritos.detail", distrito_id=distrito.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("distritos.detail", distrito_id=distrito.id))


@distritos.route("/distritos/select_json", methods=["GET", "POST"])
def select_json():
    """Proporcionar el JSON de distritos para elegir con un select"""
    consulta = Distrito.query.filter_by(estatus="A").order_by(Distrito.clave)
    data = []
    for resultado in consulta.all():
        data.append({"id": str(resultado.id), "texto": f"{resultado.clave}: {resultado.nombre}"})
    return json.dumps(data)


@distritos.route("/distritos/toggle_es_activo_json/<distrito_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.ADMINISTRAR)
def toggle_es_activo_json(distrito_id):
    """Cambiar es_activo a su opuesto al dar clic a su boton en datatable"""

    # Consultar

    distrito = Distrito.query.get_or_404(distrito_id)
    if distrito is None:
        return {"success": False, "message": "No encontrado"}

    # Cambiar es_activo a su opuesto y guardar
    distrito.es_activo = not distrito.es_activo
    distrito.save()

    # Entregar JSON
    return {
        "success": True,
        "message": "Activo" if distrito.es_activo == "A" else "Inactivo",
        "es_activo": distrito.es_activo,
        "id": distrito.id,
    }
