"""
Centros de Trabajo, vistas
"""
import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_clave, safe_message, safe_string
from perseo.blueprints.bitacoras.models import Bitacora
from perseo.blueprints.centros_trabajos.forms import CentroTrabajoForm
from perseo.blueprints.centros_trabajos.models import CentroTrabajo
from perseo.blueprints.modulos.models import Modulo
from perseo.blueprints.permisos.models import Permiso
from perseo.blueprints.usuarios.decorators import permission_required

MODULO = "CENTROS TRABAJOS"

centros_trabajos = Blueprint("centros_trabajos", __name__, template_folder="templates")


@centros_trabajos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@centros_trabajos.route("/centros_trabajos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Centros de Trabajo"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = CentroTrabajo.query
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    registros = consulta.order_by(CentroTrabajo.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "clave": resultado.clave,
                    "url": url_for("centros_trabajos.detail", centro_trabajo_id=resultado.id),
                },
                "descripcion": resultado.descripcion,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@centros_trabajos.route("/centros_trabajos")
def list_active():
    """Listado de Centros de Trabajo activos"""
    return render_template(
        "centros_trabajos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Centros de Trabajo",
        estatus="A",
    )


@centros_trabajos.route("/centros_trabajos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Centros de Trabajo inactivos"""
    return render_template(
        "centros_trabajos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Centros de Trabajo inactivos",
        estatus="B",
    )


@centros_trabajos.route("/centros_trabajos/<int:centro_trabajo_id>")
def detail(centro_trabajo_id):
    """Detalle de un Centro de Trabajo"""
    centro_trabajo = CentroTrabajo.query.get_or_404(centro_trabajo_id)
    return render_template("centros_trabajos/detail.jinja2", centro_trabajo=centro_trabajo)


@centros_trabajos.route("/centros_trabajos/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo Centro de Trabajo"""
    form = CentroTrabajoForm()
    if form.validate_on_submit():
        # Validar que la clave no se repita
        clave = safe_clave(form.clave.data)
        if CentroTrabajo.query.filter_by(clave=clave).first():
            flash(safe_message(f"La clave {clave} ya está en uso. Debe de ser única."), "warning")
        else:
            centro_trabajo = CentroTrabajo(
                clave=clave,
                descripcion=safe_string(form.descripcion.data, save_enie=True),
            )
            centro_trabajo.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nuevo Centro de Trabajo {centro_trabajo.clave}"),
                url=url_for("centros_trabajos.detail", centro_trabajo_id=centro_trabajo.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    return render_template("centros_trabajos/new.jinja2", form=form)


@centros_trabajos.route("/centros_trabajos/edicion/<int:centro_trabajo_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(centro_trabajo_id):
    """Editar Centro de Trabajo"""
    centro_trabajo = CentroTrabajo.query.get_or_404(centro_trabajo_id)
    form = CentroTrabajoForm()
    if form.validate_on_submit():
        es_valido = True
        # Si cambia la clave verificar que no este en uso
        clave = safe_clave(form.clave.data)
        if centro_trabajo.clave != clave:
            centro_trabajo_existente = CentroTrabajo.query.filter_by(clave=clave).first()
            if centro_trabajo_existente and centro_trabajo_existente.id != centro_trabajo.id:
                es_valido = False
                flash("La clave ya está en uso. Debe de ser única.", "warning")
        # Si es valido actualizar
        if es_valido:
            centro_trabajo.clave = clave
            centro_trabajo.descripcion = safe_string(form.descripcion.data)
            centro_trabajo.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado Centro de Trabajo {centro_trabajo.descripcion}"),
                url=url_for("centros_trabajos.detail", centro_trabajo_id=centro_trabajo.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    form.clave.data = centro_trabajo.clave
    form.descripcion.data = centro_trabajo.descripcion
    return render_template("centros_trabajos/edit.jinja2", form=form, centro_trabajo=centro_trabajo)


@centros_trabajos.route("/centros_trabajos/eliminar/<int:centro_trabajo_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(centro_trabajo_id):
    """Eliminar Centro de Trabajo"""
    centro_trabajo = CentroTrabajo.query.get_or_404(centro_trabajo_id)
    if centro_trabajo.estatus == "A":
        centro_trabajo.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Centro de Trabajo {centro_trabajo.clave}"),
            url=url_for("centros_trabajos.detail", centro_trabajo_id=centro_trabajo.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("centros_trabajos.detail", centro_trabajo_id=centro_trabajo.id))


@centros_trabajos.route("/centros_trabajos/recuperar/<int:centro_trabajo_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(centro_trabajo_id):
    """Recuperar Centro de Trabajo"""
    centro_trabajo = CentroTrabajo.query.get_or_404(centro_trabajo_id)
    if centro_trabajo.estatus == "B":
        centro_trabajo.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Centro de Trabajo {centro_trabajo.clave}"),
            url=url_for("centros_trabajos.detail", centro_trabajo_id=centro_trabajo.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("centros_trabajos.detail", centro_trabajo_id=centro_trabajo.id))
