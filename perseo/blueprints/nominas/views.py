"""
Nominas, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message, safe_quincena, safe_rfc, safe_string
from perseo.blueprints.bitacoras.models import Bitacora
from perseo.blueprints.centros_trabajos.models import CentroTrabajo
from perseo.blueprints.modulos.models import Modulo
from perseo.blueprints.nominas.forms import NominaEditForm, NominaExtraordinarioNewForm
from perseo.blueprints.nominas.models import Nomina
from perseo.blueprints.permisos.models import Permiso
from perseo.blueprints.personas.models import Persona
from perseo.blueprints.plazas.models import Plaza
from perseo.blueprints.quincenas.models import Quincena
from perseo.blueprints.usuarios.decorators import permission_required

MODULO = "NOMINAS"

nominas = Blueprint("nominas", __name__, template_folder="templates")


@nominas.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@nominas.route("/nominas/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de nominas"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Nomina.query.join(Quincena)  # Para ordenar por Quincena.clave.desc()
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(Nomina.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(Nomina.estatus == "A")
    if "centro_trabajo_id" in request.form:
        consulta = consulta.filter(Nomina.centro_trabajo_id == request.form["centro_trabajo_id"])
    if "persona_id" in request.form:
        consulta = consulta.filter(Nomina.persona_id == request.form["persona_id"])
    if "plaza_id" in request.form:
        consulta = consulta.filter(Nomina.plaza_id == request.form["plaza_id"])
    if "quincena_id" in request.form:
        consulta = consulta.filter(Nomina.quincena_id == request.form["quincena_id"])
    if "tipo" in request.form and request.form["tipo"] != "":
        consulta = consulta.filter(Nomina.tipo == request.form["tipo"])
    if "tfd" in request.form and request.form["tfd"] == "1":
        consulta = consulta.filter(Nomina.timbrado_id != None)
    if "tfd" in request.form and request.form["tfd"] == "-1":
        consulta = consulta.filter(Nomina.timbrado_id == None)
    # Luego filtrar por columnas de otras tablas
    if "quincena_clave" in request.form:
        try:
            quincena_clave = safe_quincena(request.form["quincena_clave"])
            consulta = consulta.filter(Quincena.clave == quincena_clave)
        except ValueError:
            pass
    if (
        "persona_rfc" in request.form
        or "persona_nombres" in request.form
        or "persona_apellido_primero" in request.form
        or "persona_apellido_segundo" in request.form
    ):
        consulta = consulta.join(Persona)
    if "persona_rfc" in request.form:
        consulta = consulta.filter(Persona.rfc.contains(safe_rfc(request.form["persona_rfc"], search_fragment=True)))
    if "persona_nombres" in request.form:
        consulta = consulta.filter(Persona.nombres.contains(safe_string(request.form["persona_nombres"], save_enie=True)))
    if "persona_apellido_primero" in request.form:
        consulta = consulta.filter(
            Persona.apellido_primero.contains(safe_string(request.form["persona_apellido_primero"], save_enie=True))
        )
    if "persona_apellido_segundo" in request.form:
        consulta = consulta.filter(
            Persona.apellido_segundo.contains(safe_string(request.form["persona_apellido_segundo"], save_enie=True))
        )
    # Ordenar y paginar
    registros = consulta.order_by(Quincena.clave.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("nominas.detail", nomina_id=resultado.id),
                },
                "quincena_clave": resultado.quincena.clave,
                "persona_rfc": resultado.persona.rfc,
                "persona_nombre_completo": resultado.persona.nombre_completo,
                "centro_trabajo_clave": resultado.centro_trabajo.clave,
                "plaza_clave": resultado.plaza.clave,
                "tipo": resultado.tipo,
                "desde_clave": resultado.desde_clave,
                "hasta_clave": resultado.hasta_clave,
                "percepcion": resultado.percepcion,
                "deduccion": resultado.deduccion,
                "importe": resultado.importe,
                "num_cheque": resultado.num_cheque,
                "fecha_pago": resultado.fecha_pago.strftime("%Y-%m-%d"),
                "timbrado": {
                    "id": resultado.timbrado_id if resultado.timbrado_id else 0,
                    "url": url_for("timbrados.detail", timbrado_id=resultado.timbrado_id) if resultado.timbrado_id else "",
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@nominas.route("/nominas")
def list_active():
    """Listado de Nóminas activas"""
    return render_template(
        "nominas/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Nóminas",
        estatus="A",
    )


@nominas.route("/nominas/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Nóminas inactivas"""
    return render_template(
        "nominas/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Nóminas inactivas",
        estatus="B",
    )


@nominas.route("/nominas/<int:nomina_id>")
def detail(nomina_id):
    """Detalle de un Nomina"""
    nomina = Nomina.query.get_or_404(nomina_id)
    return render_template("nominas/detail.jinja2", nomina=nomina)


@nominas.route("/nominas/edicion/<int:nomina_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(nomina_id):
    """Editar Nomina"""
    nomina = Nomina.query.get_or_404(nomina_id)
    form = NominaEditForm()
    if form.validate_on_submit():
        nomina.percepcion = form.percepcion.data
        nomina.deduccion = form.deduccion.data
        nomina.importe = form.importe.data
        nomina.tipo = safe_string(form.tipo.data)
        nomina.num_cheque = safe_string(form.num_cheque.data)
        nomina.fecha_pago = form.fecha_pago.data
        nomina.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Editado Nomina {nomina.id}"),
            url=url_for("nominas.detail", nomina_id=nomina.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    form.quincena_clave.data = nomina.quincena.clave  # Solo lectura
    form.persona_rfc.data = nomina.persona.rfc  # Solo lectura
    form.persona_nombre_completo.data = nomina.persona.nombre_completo  # Solo lectura
    form.centro_trabajo_clave.data = nomina.centro_trabajo.clave  # Solo lectura
    form.plaza_clave.data = nomina.plaza.clave  # Solo lectura
    form.tipo.data = nomina.tipo
    form.percepcion.data = nomina.percepcion
    form.deduccion.data = nomina.deduccion
    form.importe.data = nomina.importe
    form.num_cheque.data = nomina.num_cheque
    form.fecha_pago.data = nomina.fecha_pago
    return render_template("nominas/edit.jinja2", form=form, nomina=nomina)


@nominas.route("/nominas/eliminar/<int:nomina_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(nomina_id):
    """Eliminar Nomina"""
    nomina = Nomina.query.get_or_404(nomina_id)
    if nomina.estatus == "A":
        nomina.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Nomina ID {nomina.id}"),
            url=url_for("nominas.detail", nomina_id=nomina.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("nominas.detail", nomina_id=nomina.id))


@nominas.route("/nominas/recuperar/<int:nomina_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(nomina_id):
    """Recuperar Nomina"""
    nomina = Nomina.query.get_or_404(nomina_id)
    if nomina.estatus == "B":
        nomina.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Nomina ID {nomina.id}"),
            url=url_for("nominas.detail", nomina_id=nomina.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("nominas.detail", nomina_id=nomina.id))


@nominas.route("/nominas/nuevo_extraordinario/<int:persona_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def new_extraordinario(persona_id):
    """Nueva Nomina Extraordinaria"""
    persona = Persona.query.get_or_404(persona_id)
    form = NominaExtraordinarioNewForm()
    if form.validate_on_submit():
        nomina = Nomina(
            persona=persona,
            centro_trabajo=persona.centro_trabajo,
            plaza=persona.plaza,
            quincena=Quincena.query.filter_by(clave=form.quincena.data).first(),
            desde_clave=form.desde_clave.data,
            hasta_clave=form.hasta_clave.data,
            tipo="EXTRAORDINARIO",
            percepcion=0,
            deduccion=0,
            importe=0,
            num_cheque=safe_string(form.num_cheque.data),
            fecha_pago=form.fecha_pago.data,
            p30=form.p30.data,
            pgn=form.pgn.data,
            pga=form.pga.data,
            p22=form.p22.data,
            pvd=form.pvd.data,
            pgp=form.pgp.data,
            p20=form.p20.data,
            pam=form.pam.data,
            ps3=form.ps3.data,
            p07=form.p07.data,
            p7g=form.p7g.data,
            phr=form.phr.data,
        )
        nomina.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nueva Nomina Extraordinaria {nomina.id}"),
            url=url_for("nominas.detail", nomina_id=nomina.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    # Definir el contenido del campo de la persona
    form.persona_texto.data = f"{persona.rfc} - {persona.nombre_completo}"
    # Definir el contenido del campo del centro de trabajo
    if persona.ultimo_centro_trabajo_id:
        centro_trabajo = CentroTrabajo.query.get(persona.ultimo_centro_trabajo_id)
    else:
        centro_trabajo = CentroTrabajo.query.filter_by(clave="ND").first()
    form.centro_trabajo_texto.data = f"{centro_trabajo.clave} - {centro_trabajo.descripcion}"
    # Definir el contenido del campo de la plaza
    if persona.ultimo_plaza_id:
        plaza = Plaza.query.get(persona.ultimo_plaza_id)
    else:
        plaza = Plaza.query.filter_by(clave="ND").first()
    form.plaza_texto.data = f"{plaza.clave} - {plaza.descripcion}"
    # Definir el contenido del campo tipo
    form.tipo.data = "EXTRAORDINARIO"
    # Entregar el formulario
    return render_template("nominas/new_extraordinario.jinja2", form=form, persona=persona)
