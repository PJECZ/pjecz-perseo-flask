"""
Percepciones Deducciones, vistas
"""
import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_clave, safe_message, safe_quincena, safe_rfc
from perseo.blueprints.bitacoras.models import Bitacora
from perseo.blueprints.conceptos.models import Concepto
from perseo.blueprints.modulos.models import Modulo
from perseo.blueprints.percepciones_deducciones.forms import PercepcionDeduccionNewWithPersonaForm
from perseo.blueprints.percepciones_deducciones.models import PercepcionDeduccion
from perseo.blueprints.permisos.models import Permiso
from perseo.blueprints.personas.models import Persona
from perseo.blueprints.usuarios.decorators import permission_required

MODULO = "PERCEPCIONES DEDUCCIONES"

percepciones_deducciones = Blueprint("percepciones_deducciones", __name__, template_folder="templates")


@percepciones_deducciones.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@percepciones_deducciones.route("/percepciones_deducciones/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Percepciones Deducciones"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = PercepcionDeduccion.query
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    # Primero filtrar por columnas propias de percepciones_deducciones
    if "quincena" in request.form:
        try:
            consulta = consulta.filter_by(quincena=safe_quincena(request.form["quincena"]))
        except ValueError:
            pass
    if "concepto_id" in request.form:
        consulta = consulta.filter_by(concepto_id=request.form["concepto_id"])
    if "persona_id" in request.form:
        consulta = consulta.filter_by(persona_id=request.form["persona_id"])
    # Luego filtrar por columnas de otras tablas
    if "concepto_clave" in request.form:
        consulta = consulta.join(Concepto)
        consulta = consulta.filter(Concepto.clave == safe_clave(request.form["concepto_clave"]))
    if "persona_rfc" in request.form:
        consulta = consulta.join(Persona)
        consulta = consulta.filter(Persona.rfc.contains(safe_rfc(request.form["persona_rfc"], search_fragment=True)))
    registros = consulta.order_by(PercepcionDeduccion.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("percepciones_deducciones.detail", percepcion_deduccion_id=resultado.id),
                },
                "persona_rfc": resultado.persona.rfc,
                "persona_nombre_completo": resultado.persona.nombre_completo,
                "centro_trabajo_clave": resultado.centro_trabajo.clave,
                "concepto_clave": resultado.concepto.clave,
                "plaza_clave": resultado.plaza.clave,
                "quincena": resultado.quincena,
                "importe": resultado.importe,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@percepciones_deducciones.route("/percepciones_deducciones")
def list_active():
    """Listado de Percepciones Deducciones activos"""
    return render_template(
        "percepciones_deducciones/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Percepciones Deducciones",
        estatus="A",
    )


@percepciones_deducciones.route("/percepciones_deducciones/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Percepciones Deducciones inactivos"""
    return render_template(
        "percepciones_deducciones/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Percepciones Deducciones inactivos",
        estatus="B",
    )


@percepciones_deducciones.route("/percepciones_deducciones/<int:percepcion_deduccion_id>")
def detail(percepcion_deduccion_id):
    """Detalle de una Percepcion Deduccion"""
    percepcion_deduccion = PercepcionDeduccion.query.get_or_404(percepcion_deduccion_id)
    return render_template("percepciones_deducciones/detail.jinja2", percepcion_deduccion=percepcion_deduccion)


@percepciones_deducciones.route("/percepciones_deducciones/nuevo_con_persona/<int:persona_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new_with_persona(persona_id):
    """Nueva Percepcion Deduccion"""
    persona = Persona.query.get_or_404(persona_id)
    form = PercepcionDeduccionNewWithPersonaForm()
    if form.validate_on_submit():
        percepcion_deduccion = PercepcionDeduccion(
            persona=persona,
            centro_trabajo_id=form.centro_trabajo.data,
            concepto_id=form.concepto.data,
            plaza_id=form.plaza.data,
            quincena=form.quincena.data,
            importe=form.importe.data,
        )
        percepcion_deduccion.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo Percepcion Deduccion {percepcion_deduccion.importe}"),
            url=url_for("percepciones_deducciones.detail", percepcion_deduccion_id=percepcion_deduccion.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    form.persona_rfc.data = persona.rfc  # Solo lectura
    form.persona_nombre_completo.data = persona.nombre_completo  # Solo lectura
    return render_template(
        "percepciones_deducciones/new_with_persona.jinja2",
        titulo=f"Agregar Percepción-Deducción a {persona.rfc}",
        form=form,
        persona=persona,
    )


@percepciones_deducciones.route("/percepciones_deducciones/edicion/<int:percepcion_deduccion_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(percepcion_deduccion_id):
    """Editar Percepcion Deduccion"""
    percepcion_deduccion = PercepcionDeduccion.query.get_or_404(percepcion_deduccion_id)
    form = PercepcionDeduccionNewWithPersonaForm()
    if form.validate_on_submit():
        percepcion_deduccion.centro_trabajo_id = form.centro_trabajo.data
        percepcion_deduccion.concepto_id = form.concepto.data
        percepcion_deduccion.plaza_id = form.plaza.data
        percepcion_deduccion.quincena = form.quincena.data
        percepcion_deduccion.importe = form.importe.data
        percepcion_deduccion.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Editado Percepcion Deduccion {percepcion_deduccion.importe}"),
            url=url_for("percepciones_deducciones.detail", percepcion_deduccion_id=percepcion_deduccion.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    form.persona_rfc.data = percepcion_deduccion.persona.rfc  # Solo lectura
    form.persona_nombre_completo.data = percepcion_deduccion.persona.nombre_completo  # Solo lectura
    form.centro_trabajo.data = percepcion_deduccion.centro_trabajo_id
    form.concepto.data = percepcion_deduccion.concepto_id
    form.plaza.data = percepcion_deduccion.plaza_id
    form.quincena.data = percepcion_deduccion.quincena
    form.importe.data = percepcion_deduccion.importe
    return render_template("percepciones_deducciones/edit.jinja2", form=form, percepcion_deduccion=percepcion_deduccion)


@percepciones_deducciones.route("/percepciones_deducciones/eliminar/<int:percepcion_deduccion_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(percepcion_deduccion_id):
    """Eliminar Percepcion Deduccion"""
    percepcion_deduccion = PercepcionDeduccion.query.get_or_404(percepcion_deduccion_id)
    if percepcion_deduccion.estatus == "A":
        percepcion_deduccion.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Percepcion Deduccion {percepcion_deduccion.id}"),
            url=url_for("percepciones_deducciones.detail", percepcion_deduccion_id=percepcion_deduccion.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("percepciones_deducciones.detail", percepcion_deduccion_id=percepcion_deduccion.id))


@percepciones_deducciones.route("/percepciones_deducciones/recuperar/<int:percepcion_deduccion_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(percepcion_deduccion_id):
    """Recuperar Percepcion Deduccion"""
    percepcion_deduccion = PercepcionDeduccion.query.get_or_404(percepcion_deduccion_id)
    if percepcion_deduccion.estatus == "B":
        percepcion_deduccion.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Percepcion Deduccion {percepcion_deduccion.id}"),
            url=url_for("percepciones_deducciones.detail", percepcion_deduccion_id=percepcion_deduccion.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("percepciones_deducciones.detail", percepcion_deduccion_id=percepcion_deduccion.id))
