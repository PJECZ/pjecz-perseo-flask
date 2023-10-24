"""
Conceptos, vistas
"""
import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_clave, safe_message, safe_string
from perseo.blueprints.bitacoras.models import Bitacora
from perseo.blueprints.conceptos.forms import ConceptoForm
from perseo.blueprints.conceptos.models import Concepto
from perseo.blueprints.modulos.models import Modulo
from perseo.blueprints.permisos.models import Permiso
from perseo.blueprints.usuarios.decorators import permission_required

MODULO = "CONCEPTOS"

conceptos = Blueprint("conceptos", __name__, template_folder="templates")


@conceptos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@conceptos.route("/conceptos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Conceptos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Concepto.query
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    registros = consulta.order_by(Concepto.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "clave": resultado.clave,
                    "url": url_for("conceptos.detail", concepto_id=resultado.id),
                },
                "descripcion": resultado.descripcion,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@conceptos.route("/conceptos")
def list_active():
    """Listado de Conceptos activos"""
    return render_template(
        "conceptos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Conceptos",
        estatus="A",
    )


@conceptos.route("/conceptos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Conceptos inactivos"""
    return render_template(
        "conceptos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Conceptos inactivos",
        estatus="B",
    )


@conceptos.route("/conceptos/<int:concepto_id>")
def detail(concepto_id):
    """Detalle de un Concepto"""
    concepto = Concepto.query.get_or_404(concepto_id)
    return render_template("conceptos/detail.jinja2", concepto=concepto)


@conceptos.route("/conceptos/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo Concepto"""
    form = ConceptoForm()
    if form.validate_on_submit():
        # Validar que la clave no se repita
        clave = safe_clave(form.clave.data)
        if Concepto.query.filter_by(clave=clave).first():
            flash(safe_message(f"La clave {clave} ya está en uso. Debe de ser única."), "warning")
        else:
            concepto = Concepto(
                clave=clave,
                descripcion=safe_string(form.descripcion.data, save_enie=True),
            )
            concepto.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nuevo Concepto {concepto.clave}"),
                url=url_for("conceptos.detail", concepto_id=concepto.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    return render_template("conceptos/new.jinja2", form=form)


@conceptos.route("/conceptos/edicion/<int:concepto_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(concepto_id):
    """Editar Concepto"""
    concepto = Concepto.query.get_or_404(concepto_id)
    form = ConceptoForm()
    if form.validate_on_submit():
        es_valido = True
        # Si cambia la clave verificar que no este en uso
        clave = safe_clave(form.clave.data)
        if concepto.clave != clave:
            concepto_existente = Concepto.query.filter_by(clave=clave).first()
            if concepto_existente and concepto_existente.id != concepto.id:
                es_valido = False
                flash("La clave ya está en uso. Debe de ser única.", "warning")
        # Si es valido actualizar
        if es_valido:
            concepto.clave = clave
            concepto.descripcion = safe_string(form.descripcion.data)
            concepto.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado Concepto {concepto.descripcion}"),
                url=url_for("conceptos.detail", concepto_id=concepto.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    form.clave.data = concepto.clave
    form.descripcion.data = concepto.descripcion
    return render_template("conceptos/edit.jinja2", form=form, concepto=concepto)


@conceptos.route("/conceptos/eliminar/<int:concepto_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(concepto_id):
    """Eliminar Concepto"""
    concepto = Concepto.query.get_or_404(concepto_id)
    if concepto.estatus == "A":
        concepto.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Concepto {concepto.clave}"),
            url=url_for("conceptos.detail", concepto_id=concepto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("conceptos.detail", concepto_id=concepto.id))


@conceptos.route("/conceptos/recuperar/<int:concepto_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(concepto_id):
    """Recuperar Concepto"""
    concepto = Concepto.query.get_or_404(concepto_id)
    if concepto.estatus == "B":
        concepto.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Concepto {concepto.clave}"),
            url=url_for("conceptos.detail", concepto_id=concepto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("conceptos.detail", concepto_id=concepto.id))
