"""
Personas, vistas
"""
import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_curp, safe_message, safe_rfc, safe_string
from perseo.blueprints.bitacoras.models import Bitacora
from perseo.blueprints.modulos.models import Modulo
from perseo.blueprints.permisos.models import Permiso
from perseo.blueprints.personas.forms import PersonaForm
from perseo.blueprints.personas.models import Persona
from perseo.blueprints.usuarios.decorators import permission_required

MODULO = "PERSONAS"

personas = Blueprint("personas", __name__, template_folder="templates")


@personas.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@personas.route("/personas/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Personas"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Persona.query
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "rfc" in request.form:
        try:
            consulta = consulta.filter(Persona.rfc.contains(safe_rfc(request.form["rfc"], search_fragment=True)))
        except ValueError:
            pass
    if "nombres" in request.form:
        consulta = consulta.filter(Persona.nombres.contains(safe_string(request.form["nombres"])))
    if "apellido_primero" in request.form:
        consulta = consulta.filter(Persona.apellido_primero.contains(safe_string(request.form["apellido_primero"])))
    if "apellido_segundo" in request.form:
        consulta = consulta.filter(Persona.apellido_segundo.contains(safe_string(request.form["apellido_segundo"])))
    registros = consulta.order_by(Persona.rfc).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "rfc": resultado.rfc,
                    "url": url_for("personas.detail", persona_id=resultado.id),
                },
                "nombres": resultado.nombres,
                "apellido_primero": resultado.apellido_primero,
                "apellido_segundo": resultado.apellido_segundo,
                "curp": resultado.curp,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@personas.route("/personas")
def list_active():
    """Listado de Personas activas"""
    return render_template(
        "personas/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Personas",
        estatus="A",
    )


@personas.route("/personas/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Personas inactivas"""
    return render_template(
        "personas/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Personas inactivas",
        estatus="B",
    )


@personas.route("/personas/<int:persona_id>")
def detail(persona_id):
    """Detalle de una Persona"""
    persona = Persona.query.get_or_404(persona_id)
    return render_template("personas/detail.jinja2", persona=persona)


@personas.route("/personas/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo Persona"""
    form = PersonaForm()
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
        if Persona.query.filter_by(rfc=rfc).first():
            es_valido = False
            flash(safe_message("El RFC ya está en uso. Debe de ser único."), "warning")
        # Validar que el CURP no se repita
        if curp != "" and Persona.query.filter_by(curp=curp).first():
            es_valido = False
            flash(safe_message("El CURP ya está en uso. Debe de ser único."), "warning")
        # Si es válido, guardar
        if es_valido:
            persona = Persona(
                rfc=rfc,
                nombres=safe_string(form.nombres.data),
                apellido_primero=safe_string(form.apellido_primero.data),
                apellido_segundo=safe_string(form.apellido_segundo.data),
                curp=safe_string(form.curp.data),
            )
            persona.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nuevo Persona {persona.rfc}"),
                url=url_for("personas.detail", persona_id=persona.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    return render_template("personas/new.jinja2", form=form)


@personas.route("/personas/edicion/<int:persona_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(persona_id):
    """Editar Persona"""
    persona = Persona.query.get_or_404(persona_id)
    form = PersonaForm()
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
        if persona.rfc != rfc:
            persona_existente = Persona.query.filter_by(rfc=rfc).first()
            if persona_existente and persona_existente.id != persona.id:
                es_valido = False
                flash("El RFC ya está en uso. Debe de ser único.", "warning")
        # Si cambia el CURP verificar que no este en uso
        if persona.curp != curp and curp != "":
            persona_existente = Persona.query.filter_by(curp=curp).first()
            if persona_existente and persona_existente.id != persona.id:
                es_valido = False
                flash("El CURP ya está en uso. Debe de ser único.", "warning")
        # Si es válido, guardar
        if es_valido:
            persona.rfc = rfc
            persona.nombres = safe_string(form.nombres.data)
            persona.apellido_primero = safe_string(form.apellido_primero.data)
            persona.apellido_segundo = safe_string(form.apellido_segundo.data)
            persona.curp = curp
            persona.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado Persona {persona.rfc}"),
                url=url_for("personas.detail", persona_id=persona.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    form.rfc.data = persona.rfc
    form.nombres.data = persona.nombres
    form.apellido_primero.data = persona.apellido_primero
    form.apellido_segundo.data = persona.apellido_segundo
    form.curp.data = persona.curp
    return render_template("personas/edit.jinja2", form=form, persona=persona)


@personas.route("/personas/eliminar/<int:persona_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(persona_id):
    """Eliminar Persona"""
    persona = Persona.query.get_or_404(persona_id)
    if persona.estatus == "A":
        persona.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Persona {persona.rfc}"),
            url=url_for("personas.detail", persona_id=persona.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("personas.detail", persona_id=persona.id))


@personas.route("/personas/recuperar/<int:persona_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(persona_id):
    """Recuperar Persona"""
    persona = Persona.query.get_or_404(persona_id)
    if persona.estatus == "B":
        persona.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Persona {persona.rfc}"),
            url=url_for("personas.detail", persona_id=persona.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("personas.detail", persona_id=persona.id))
