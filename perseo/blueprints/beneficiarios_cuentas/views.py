"""
Beneficiarios Cuentas, vistas
"""
import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_clave, safe_message
from perseo.blueprints.bancos.models import Banco
from perseo.blueprints.beneficiarios.models import Beneficiario
from perseo.blueprints.beneficiarios_cuentas.forms import BeneficiarioCuentaEditForm, BeneficiarioCuentaNewWithBeneficiarioForm
from perseo.blueprints.beneficiarios_cuentas.models import BeneficiarioCuenta
from perseo.blueprints.bitacoras.models import Bitacora
from perseo.blueprints.modulos.models import Modulo
from perseo.blueprints.permisos.models import Permiso
from perseo.blueprints.usuarios.decorators import permission_required

MODULO = "BENEFICIARIOS CUENTAS"

beneficiarios_cuentas = Blueprint("beneficiarios_cuentas", __name__, template_folder="templates")


@beneficiarios_cuentas.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@beneficiarios_cuentas.route("/beneficiarios_cuentas/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de BeneficiariosCuentas"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = BeneficiarioCuenta.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "beneficiario_id" in request.form:
        consulta = consulta.filter_by(beneficiario_id=request.form["beneficiario_id"])
    # Ordenar y paginar
    registros = consulta.order_by(BeneficiarioCuenta.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("beneficiarios_cuentas.detail", beneficiario_cuenta_id=resultado.id),
                },
                "beneficiario_rfc": resultado.beneficiario.rfc,
                "beneficiario_nombre_completo": resultado.beneficiario.nombre_completo,
                "banco_nombre": resultado.banco.nombre,
                "num_cuenta": resultado.num_cuenta,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@beneficiarios_cuentas.route("/beneficiarios_cuentas")
def list_active():
    """Listado de Beneficiarios Cuentas activos"""
    return render_template(
        "beneficiarios_cuentas/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Beneficiarios Cuentas",
        estatus="A",
    )


@beneficiarios_cuentas.route("/beneficiarios_cuentas/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Beneficiarios Cuentas inactivos"""
    return render_template(
        "beneficiarios_cuentas/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Beneficiarios Cuentas inactivos",
        estatus="B",
    )


@beneficiarios_cuentas.route("/beneficiarios_cuentas/<int:beneficiario_cuenta_id>")
def detail(beneficiario_cuenta_id):
    """Detalle de un Beneficiario Cuenta"""
    beneficiario_cuenta = BeneficiarioCuenta.query.get_or_404(beneficiario_cuenta_id)
    return render_template("beneficiarios_cuentas/detail.jinja2", beneficiario_cuenta=beneficiario_cuenta)


@beneficiarios_cuentas.route("/beneficiarios_cuentas/nuevo_con_beneficiario/<int:beneficiario_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new_with_beneficiario(beneficiario_id):
    """Nuevo Beneficiario Cuenta"""
    beneficiario = Beneficiario.query.get_or_404(beneficiario_id)
    form = BeneficiarioCuentaNewWithBeneficiarioForm()
    if form.validate_on_submit():
        banco = Banco.query.get_or_404(form.banco.data)
        beneficiario_cuenta = BeneficiarioCuenta(
            banco=banco,
            beneficiario=beneficiario,
            num_cuenta=safe_clave(form.num_cuenta.data, max_len=24, only_digits=True, separator=""),
        )
        beneficiario_cuenta.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo Beneficiario Cuenta {beneficiario_cuenta.num_cuenta}"),
            url=url_for("beneficiarios_cuentas.detail", beneficiario_cuenta_id=beneficiario_cuenta.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    form.beneficiario_rfc.data = beneficiario.rfc  # Solo lectura
    form.beneficiario_nombre.data = beneficiario.nombre_completo  # Solo lectura
    return render_template(
        "beneficiarios_cuentas/new_with_beneficiario.jinja2",
        form=form,
        beneficiario=beneficiario,
        titulo=f"Nueva Cuenta para Beneficiario {beneficiario.rfc}",
    )


@beneficiarios_cuentas.route("/beneficiarios_cuentas/edicion/<int:beneficiario_cuenta_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(beneficiario_cuenta_id):
    """Editar Beneficiario Cuenta"""
    beneficiario_cuenta = BeneficiarioCuenta.query.get_or_404(beneficiario_cuenta_id)
    form = BeneficiarioCuentaEditForm()
    if form.validate_on_submit():
        beneficiario_cuenta.num_cuenta = safe_clave(form.num_cuenta.data, max_len=24, only_digits=True, separator="")
        beneficiario_cuenta.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Editado Beneficiario Cuenta {beneficiario_cuenta.num_cuenta}"),
            url=url_for("beneficiarios_cuentas.detail", beneficiario_cuenta_id=beneficiario_cuenta.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    form.banco_nombre.data = beneficiario_cuenta.banco.nombre
    form.beneficiario_rfc.data = beneficiario_cuenta.beneficiario.rfc
    form.beneficiario_nombre.data = beneficiario_cuenta.beneficiario.nombre_completo
    form.num_cuenta.data = beneficiario_cuenta.num_cuenta
    return render_template("beneficiarios_cuentas/edit.jinja2", form=form, beneficiario_cuenta=beneficiario_cuenta)


@beneficiarios_cuentas.route("/beneficiarios_cuentas/eliminar/<int:beneficiario_cuenta_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(beneficiario_cuenta_id):
    """Eliminar Beneficiario Cuenta"""
    beneficiario_cuenta = BeneficiarioCuenta.query.get_or_404(beneficiario_cuenta_id)
    if beneficiario_cuenta.estatus == "A":
        beneficiario_cuenta.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Beneficiario Cuenta ID {beneficiario_cuenta.id}"),
            url=url_for("beneficiarios_cuentas.detail", beneficiario_cuenta_id=beneficiario_cuenta.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("beneficiarios_cuentas.detail", beneficiario_cuenta_id=beneficiario_cuenta.id))


@beneficiarios_cuentas.route("/beneficiarios_cuentas/recuperar/<int:beneficiario_cuenta_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(beneficiario_cuenta_id):
    """Recuperar Beneficiario Cuenta"""
    beneficiario_cuenta = BeneficiarioCuenta.query.get_or_404(beneficiario_cuenta_id)
    if beneficiario_cuenta.estatus == "B":
        beneficiario_cuenta.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Beneficiario Cuenta ID {beneficiario_cuenta.id}"),
            url=url_for("beneficiarios_cuentas.detail", beneficiario_cuenta_id=beneficiario_cuenta.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("beneficiarios_cuentas.detail", beneficiario_cuenta_id=beneficiario_cuenta.id))
