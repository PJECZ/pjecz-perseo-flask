"""
Beneficiarios Quincenas, vistas
"""
import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message, safe_string
from perseo.blueprints.beneficiarios.models import Beneficiario
from perseo.blueprints.beneficiarios_cuentas.forms import BeneficiarioCuentaNewWithBeneficiarioForm
from perseo.blueprints.beneficiarios_quincenas.forms import BeneficiarioQuincenaEditForm
from perseo.blueprints.beneficiarios_quincenas.models import BeneficiarioQuincena
from perseo.blueprints.bitacoras.models import Bitacora
from perseo.blueprints.modulos.models import Modulo
from perseo.blueprints.permisos.models import Permiso
from perseo.blueprints.usuarios.decorators import permission_required

MODULO = "BENEFICIARIOS QUINCENAS"

beneficiarios_quincenas = Blueprint("beneficiarios_quincenas", __name__, template_folder="templates")


@beneficiarios_quincenas.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@beneficiarios_quincenas.route("/beneficiarios_quincenas/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Beneficiarios Quincenas"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = BeneficiarioQuincena.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "beneficiario_id" in request.form:
        consulta = consulta.filter_by(beneficiario_id=request.form["beneficiario_id"])
    # Ordenar y paginar
    registros = consulta.order_by(BeneficiarioQuincena.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("beneficiarios_quincenas.detail", beneficiario_quincena_id=resultado.id),
                },
                "quincena": resultado.quincena,
                "beneficiario_rfc": resultado.beneficiario.rfc,
                "beneficiario_nombre_completo": resultado.beneficiario.nombre_completo,
                "importe": resultado.importe,
                "num_cheque": resultado.num_cheque,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@beneficiarios_quincenas.route("/beneficiarios_quincenas")
def list_active():
    """Listado de Beneficiarios Quincenas activos"""
    return render_template(
        "beneficiarios_quincenas/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Beneficiarios Quincenas",
        estatus="A",
    )


@beneficiarios_quincenas.route("/beneficiarios_quincenas/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Beneficiarios Quincenas inactivos"""
    return render_template(
        "beneficiarios_quincenas/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Beneficiarios Quincenas inactivos",
        estatus="B",
    )


@beneficiarios_quincenas.route("/beneficiarios_quincenas/<int:beneficiario_quincena_id>")
def detail(beneficiario_quincena_id):
    """Detalle de un Beneficiario Quincena"""
    beneficiario_quincena = BeneficiarioQuincena.query.get_or_404(beneficiario_quincena_id)
    return render_template("beneficiarios_quincenas/detail.jinja2", beneficiario_quincena=beneficiario_quincena)


@beneficiarios_quincenas.route("/beneficiarios_quincenas/nuevo_con_beneficiario/<int:beneficiario_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new_with_beneficiario(beneficiario_id):
    """Nuevo Beneficiario Quincena"""
    beneficiario = Beneficiario.query.get_or_404(beneficiario_id)
    form = BeneficiarioCuentaNewWithBeneficiarioForm()
    if form.validate_on_submit():
        beneficiario_quincena = BeneficiarioQuincena(
            beneficiario=beneficiario,
            quincena=form.quincena.data,
            importe=form.importe.data,
            num_cheque=form.num_cheque.data,
        )
        beneficiario_quincena.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo Beneficiario Quincena {beneficiario_quincena.num_cheque}"),
            url=url_for("beneficiarios_quincenas.detail", beneficiario_quincena_id=beneficiario_quincena.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    form.beneficiario_rfc.data = beneficiario.rfc  # Solo lectura
    form.beneficiario_nombre.data = beneficiario.nombre_completo  # Solo lectura
    return render_template(
        "beneficiarios_quincenas/new_with_beneficiario.jinja2",
        form=form,
        beneficiario=beneficiario,
        titulo=f"Nueva Quincena para Beneficiario {beneficiario.rfc}",
    )


@beneficiarios_quincenas.route("/beneficiarios_quincenas/edicion/<int:beneficiario_quincena_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(beneficiario_quincena_id):
    """Editar Beneficiario Quincena"""
    beneficiario_quincena = BeneficiarioQuincena.query.get_or_404(beneficiario_quincena_id)
    form = BeneficiarioQuincenaEditForm()
    if form.validate_on_submit():
        beneficiario_quincena.quincena = safe_string(form.quincena.data)
        beneficiario_quincena.importe = safe_string(form.importe.data)
        beneficiario_quincena.num_cheque = safe_string(form.num_cheque.data)
        beneficiario_quincena.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Editado Beneficiario Quincena {beneficiario_quincena.importe}"),
            url=url_for("beneficiarios_quincenas.detail", beneficiario_quincena_id=beneficiario_quincena.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    form.quincena.data = beneficiario_quincena.quincena
    form.beneficiario_nombre.data = beneficiario_quincena.beneficiario.nombre_completo  # Solo lectura
    form.beneficiario_rfc.data = beneficiario_quincena.beneficiario.rfc
    form.importe.data = beneficiario_quincena.importe
    form.num_cheque.data = beneficiario_quincena.num_cheque
    return render_template("beneficiarios_quincenas/edit.jinja2", form=form, beneficiario_quincena=beneficiario_quincena)


@beneficiarios_quincenas.route("/beneficiarios_quincenas/eliminar/<int:beneficiario_quincena_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(beneficiario_quincena_id):
    """Eliminar Beneficiario Quincena"""
    beneficiario_quincena = BeneficiarioQuincena.query.get_or_404(beneficiario_quincena_id)
    if beneficiario_quincena.estatus == "A":
        beneficiario_quincena.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Beneficiario Quincena ID {beneficiario_quincena.id}"),
            url=url_for("beneficiarios_quincenas.detail", beneficiario_quincena_id=beneficiario_quincena.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("beneficiarios_quincenas.detail", beneficiario_quincena_id=beneficiario_quincena.id))


@beneficiarios_quincenas.route("/beneficiarios_quincenas/recuperar/<int:beneficiario_quincena_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(beneficiario_quincena_id):
    """Recuperar Beneficiario Quincena"""
    beneficiario_quincena = BeneficiarioQuincena.query.get_or_404(beneficiario_quincena_id)
    if beneficiario_quincena.estatus == "B":
        beneficiario_quincena.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Beneficiario Quincena {beneficiario_quincena.id}"),
            url=url_for("beneficiarios_quincenas.detail", beneficiario_quincena_id=beneficiario_quincena.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("beneficiarios_quincenas.detail", beneficiario_quincena_id=beneficiario_quincena.id))
