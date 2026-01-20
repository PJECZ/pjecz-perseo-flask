"""
Puestos, vistas
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
from .forms import PuestoForm
from .models import Puesto

MODULO = "PUESTOS"

puestos = Blueprint("puestos", __name__, template_folder="templates")


@puestos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@puestos.route("/puestos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Puestos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Puesto.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "clave" in request.form:
        try:
            clave = safe_clave(request.form["clave"], max_len=24)
            if clave != "":
                consulta = consulta.filter(Puesto.clave.contains(clave))
        except ValueError:
            pass
    if "descripcion" in request.form:
        consulta = consulta.filter(Puesto.descripcion.contains(safe_string(request.form["descripcion"])))
    # Ordenar y paginar
    registros = consulta.order_by(Puesto.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "clave": resultado.clave,
                    "url": url_for("puestos.detail", puesto_id=resultado.id),
                },
                "descripcion": resultado.descripcion,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@puestos.route("/puestos")
def list_active():
    """Listado de Puestos activos"""
    return render_template(
        "puestos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Puestos",
        estatus="A",
    )


@puestos.route("/puestos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Puestos inactivos"""
    return render_template(
        "puestos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Puestos inactivos",
        estatus="B",
    )


@puestos.route("/puestos/<int:puesto_id>")
def detail(puesto_id):
    """Detalle de un Puesto"""
    puesto = Puesto.query.get_or_404(puesto_id)
    return render_template("puestos/detail.jinja2", puesto=puesto)


@puestos.route("/puestos/exportar_xlsx")
def exportar_xlsx():
    """Lanzar tarea en el fondo para exportar los Puestos a un archivo XLSX"""
    tarea = current_user.launch_task(
        comando="puestos.tasks.lanzar_exportar_xlsx",
        mensaje="Exportando los Puestos a un archivo XLSX...",
    )
    flash("Se ha lanzado la tarea en el fondo. Esta página se va a recargar en 10 segundos...", "info")
    return redirect(url_for("tareas.detail", tarea_id=tarea.id))


@puestos.route("/puestos/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo Puesto"""
    form = PuestoForm()
    if form.validate_on_submit():
        # Validar que la clave no se repita
        clave = safe_clave(form.clave.data, max_len=16)
        if Puesto.query.filter_by(clave=clave).first():
            flash("La clave ya está en uso. Debe de ser única.", "warning")
            return render_template("puestos/new.jinja2", form=form)
        # Guardar
        puesto = Puesto(
            clave=clave,
            descripcion=safe_string(form.descripcion.data, save_enie=True),
        )
        puesto.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo Puesto {puesto.clave}"),
            url=url_for("puestos.detail", puesto_id=puesto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    return render_template("puestos/new.jinja2", form=form)


@puestos.route("/puestos/edicion/<int:puesto_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(puesto_id):
    """Editar Puesto"""
    puesto = Puesto.query.get_or_404(puesto_id)
    form = PuestoForm()
    if form.validate_on_submit():
        es_valido = True
        # Si cambia la clave verificar que no este en uso
        clave = safe_clave(form.clave.data, max_len=24)
        if puesto.clave != clave:
            puesto_existente = Puesto.query.filter_by(clave=clave).first()
            if puesto_existente and puesto_existente.id != puesto.id:
                es_valido = False
                flash("La clave ya está en uso. Debe de ser única.", "warning")
        # Si es valido actualizar
        if es_valido:
            puesto.clave = clave
            puesto.descripcion = safe_string(form.descripcion.data, save_enie=True)
            puesto.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado Puesto {puesto.clave}"),
                url=url_for("puestos.detail", puesto_id=puesto.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    form.clave.data = puesto.clave
    form.descripcion.data = puesto.descripcion
    return render_template("puestos/edit.jinja2", form=form, puesto=puesto)


@puestos.route("/puestos/eliminar/<int:puesto_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(puesto_id):
    """Eliminar Puesto"""
    puesto = Puesto.query.get_or_404(puesto_id)
    if puesto.estatus == "A":
        puesto.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Puesto {puesto.clave}"),
            url=url_for("puestos.detail", puesto_id=puesto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("puestos.detail", puesto_id=puesto.id))


@puestos.route("/puestos/recuperar/<int:puesto_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(puesto_id):
    """Recuperar Puesto"""
    puesto = Puesto.query.get_or_404(puesto_id)
    if puesto.estatus == "B":
        puesto.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Puesto {puesto.clave}"),
            url=url_for("puestos.detail", puesto_id=puesto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("puestos.detail", puesto_id=puesto.id))
