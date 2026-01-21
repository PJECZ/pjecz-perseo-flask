"""
Autoridades
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ...lib.datatables import get_datatable_parameters, output_datatable_json
from ...lib.safe_string import safe_clave, safe_message, safe_string
from ..bitacoras.models import Bitacora
from ..distritos.models import Distrito
from ..modulos.models import Modulo
from ..permisos.models import Permiso
from ..usuarios.decorators import permission_required
from .forms import AutoridadForm
from .models import Autoridad

MODULO = "AUTORIDADES"

autoridades = Blueprint("autoridades", __name__, template_folder="templates")


@autoridades.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@autoridades.route("/autoridades/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Autoridades"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Autoridad.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(Autoridad.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(Autoridad.estatus == "A")
    if "distrito_id" in request.form:
        consulta = consulta.filter(Autoridad.distrito_id == request.form["distrito_id"])
    if "clave" in request.form:
        clave = safe_clave(request.form["clave"])
        if clave != "":
            consulta = consulta.filter(Autoridad.clave.contains(clave))
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"], save_enie=True)
        if descripcion != "":
            consulta = consulta.filter(Autoridad.descripcion.contains(descripcion))
    # Ordenar y paginar
    registros = consulta.order_by(Autoridad.clave).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "clave": resultado.clave,
                    "url": url_for("autoridades.detail", autoridad_id=resultado.id),
                },
                "descripcion": resultado.descripcion,
                "descripcion_corta": resultado.descripcion_corta,
                "distrito_clave": resultado.distrito.clave,
                "es_activo": "Sí" if resultado.es_activo else "No",
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@autoridades.route("/autoridades")
def list_active():
    """Lista de autoridades activas"""
    return render_template("autoridades/list.jinja2", estatus="A", filtros={"estatus": "A"}, titulo="Autoridades")


@autoridades.route("/autoridades/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de autoridades inactivas"""
    return render_template("autoridades/list.jinja2", estatus="B", filtros={"estatus": "B"}, titulo="autoridades inactivas")


@autoridades.route("/autoridades/<autoridad_id>")
def detail(autoridad_id):
    """Detalle de autoridad"""

    autoridad = Autoridad.query.get_or_404(autoridad_id)
    return render_template("autoridades/detail.jinja2", autoridad=autoridad)


@autoridades.route("/autoridades/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nueva Autoridad"""
    form = AutoridadForm()
    if form.validate_on_submit():
        # Validar que la clave no se repita
        clave = safe_clave(form.clave.data)
        if Autoridad.query.filter_by(clave=clave).first():
            flash("La clave ya está en uso. Debe de ser única.", "warning")
            return render_template("autoridades/new.jinja2", form=form)
        # Guardar
        autoridad = Autoridad(
            clave=clave,
            distrito_id=form.distrito.data,
            descripcion=safe_string(form.descripcion.data, save_enie=True),
            descripcion_corta=safe_string(form.descripcion_corta.data, save_enie=True),
            es_activo=form.es_activo.data,
        )
        autoridad.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nueva autoridad {autoridad.clave}"),
            url=url_for("autoridades.detail", autoridad_id=autoridad.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    # Consultar el distrito NO DEFINIDO
    distrito_no_definido = Distrito.query.filter_by(clave="ND").first()
    if distrito_no_definido:
        form.distrito.data = str(distrito_no_definido.id)  # Es un SelectField
    return render_template("autoridades/new.jinja2", form=form)


@autoridades.route("/autoridades/edicion/<autoridad_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(autoridad_id):
    """Editar Autoridad"""

    autoridad = Autoridad.query.get_or_404(autoridad_id)
    form = AutoridadForm()
    if form.validate_on_submit():
        es_valido = True
        # Si cambia la clave verificar que no este en uso
        clave = safe_clave(form.clave.data)
        if autoridad.clave != clave:
            autoridad_existente = Autoridad.query.filter_by(clave=clave).first()
            if autoridad_existente and autoridad_existente.id != autoridad_id:
                es_valido = False
                flash("La clave ya está en uso. Debe de ser única.", "warning")
        # Si es valido actualizar
        if es_valido:
            autoridad.clave = clave
            autoridad.distrito_id = form.distrito.data
            autoridad.descripcion = safe_string(form.descripcion.data, save_enie=True)
            autoridad.descripcion_corta = safe_string(form.descripcion_corta.data, save_enie=True)
            autoridad.es_activo = form.es_activo.data
            autoridad.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editada autoridad {autoridad.clave}"),
                url=url_for("autoridades.detail", autoridad_id=autoridad.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    form.clave.data = autoridad.clave
    form.distrito.data = str(autoridad.distrito_id)  # Es un SelectField
    form.descripcion.data = autoridad.descripcion
    form.descripcion_corta.data = autoridad.descripcion_corta
    form.es_activo.data = autoridad.es_activo
    return render_template("autoridades/edit.jinja2", form=form, autoridad=autoridad)


@autoridades.route("/autoridades/eliminar/<autoridad_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(autoridad_id):
    """Eliminar Autoridad"""

    autoridad = Autoridad.query.get_or_404(autoridad_id)
    if autoridad.estatus == "A":
        autoridad.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado autoridad {autoridad.clave}"),
            url=url_for("autoridades.detail", autoridad_id=autoridad.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("autoridades.detail", autoridad_id=autoridad.id))


@autoridades.route("/autoridades/recuperar/<autoridad_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(autoridad_id):
    """Recuperar Autoridad"""

    autoridad = Autoridad.query.get_or_404(autoridad_id)
    if autoridad.estatus == "B":
        autoridad.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado autoridad {autoridad.clave}"),
            url=url_for("autoridades.detail", autoridad_id=autoridad.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("autoridades.detail", autoridad_id=autoridad.id))


@autoridades.route("/autoridades/distrito_select_json/<distrito_id>", methods=["GET", "POST"])
def distrito_select_json(distrito_id):
    """Proporcionar el JSON de autoridades de un distrito para elegir con un select"""

    consulta = Autoridad.query.filter_by(estatus="A").filter_by(distrito_id=distrito_id).order_by(Autoridad.descripcion_corta)
    data = []
    for resultado in consulta.all():
        data.append({"id": str(resultado.id), "texto": f"{resultado.clave}: {resultado.descripcion_corta}"})
    return json.dumps(data)


@autoridades.route("/autoridades/select2_json", methods=["GET", "POST"])
def select2_json():
    """Proporcionar el JSON de usuarios para elegir con un Select2, puede recibir parte de la clave a buscar"""
    consulta = Autoridad.query.filter(Autoridad.estatus == "A")
    if "searchString" in request.form:
        clave = safe_clave(request.form["searchString"])
        if clave != "":
            consulta = consulta.filter(Autoridad.clave.contains(clave))
    resultados = []
    for autoridad in consulta.order_by(Autoridad.clave).limit(10).all():
        resultados.append({"id": autoridad.id, "text": f"{autoridad.clave}: {autoridad.descripcion_corta}"})
    return {"results": resultados, "pagination": {"more": False}}


@autoridades.route("/autoridades/toggle_es_activo_json/<autoridad_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.ADMINISTRAR)
def toggle_es_activo_json(autoridad_id):
    """Cambiar es_activo a su opuesto al dar clic a su boton en datatable"""

    # Consultar

    autoridad = Autoridad.query.get_or_404(autoridad_id)
    if autoridad is None:
        return {"success": False, "message": "No encontrado"}

    # Cambiar es_activo a su opuesto y guardar
    autoridad.es_activo = not autoridad.es_activo
    autoridad.save()

    # Entregar JSON
    return {
        "success": True,
        "message": "Activo" if autoridad.es_activo == "A" else "Inactivo",
        "es_activo": autoridad.es_activo,
        "id": autoridad.id,
    }
