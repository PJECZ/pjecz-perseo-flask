"""
Nominas, vistas
"""
import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message, safe_quincena, safe_rfc, safe_string
from perseo.blueprints.bitacoras.models import Bitacora
from perseo.blueprints.modulos.models import Modulo
from perseo.blueprints.nominas.forms import NominaEditForm
from perseo.blueprints.nominas.models import Nomina
from perseo.blueprints.permisos.models import Permiso
from perseo.blueprints.personas.models import Persona
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
    consulta = Nomina.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "persona_id" in request.form:
        consulta = consulta.filter_by(persona_id=request.form["persona_id"])
    # Luego filtrar por columnas de otras tablas
    if "quincena_clave" in request.form:
        try:
            quincena_clave = safe_quincena(request.form["quincena_clave"])
            consulta = consulta.join(Quincena)
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
    registros = consulta.order_by(Nomina.id).offset(start).limit(rows_per_page).all()
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
                "percepcion": resultado.percepcion,
                "deduccion": resultado.deduccion,
                "importe": resultado.importe,
                "tipo": resultado.tipo,
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
        nomina.percepcion = safe_string(form.percepcion.data)
        nomina.deduccion = safe_string(form.deduccion.data)
        nomina.importe = safe_string(form.importe.data)
        nomina.tipo = safe_string(form.tipo.data)
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
    form.percepcion.data = nomina.percepcion
    form.deduccion.data = nomina.deduccion
    form.importe.data = nomina.importe
    form.tipo.data = nomina.tipo
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


@nominas.route("/nominas/generar_nominas/<quincena_clave>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def generate_nominas(quincena_clave):
    """Lanzar tarea en el fondo para generar archivo XLSX con las nominas de una quincena ABIERTA"""
    quincena = Quincena.query.filter_by(clave=quincena_clave).first_or_404()
    current_user.launch_task(
        comando="nominas.tasks.generar_nominas",
        mensaje="Lanzando generar nominas...",
        quincena_clave=quincena_clave,
    )
    flash("Se ha lanzado la tarea en el fondo. Esta página se va a recargar en 10 segundos...", "info")
    return redirect(url_for("quincenas.detail", quincena_id=quincena.id))


@nominas.route("/nominas/generar_monederos/<quincena_clave>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def generate_monederos(quincena_clave):
    """Lanzar tarea en el fondo para generar archivo XLSX con los monederos de una quincena ABIERTA"""
    quincena = Quincena.query.filter_by(clave=quincena_clave).first_or_404()
    current_user.launch_task(
        comando="nominas.tasks.generar_monederos",
        mensaje="Lanzando generar monederos...",
        quincena_clave=quincena_clave,
    )
    flash("Se ha lanzado la tarea en el fondo. Esta página se va a recargar en 10 segundos...", "info")
    return redirect(url_for("quincenas.detail", quincena_id=quincena.id))


@nominas.route("/nominas/generar_dispersiones_pensionados/<quincena_clave>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def generate_dispersiones_pensionados(quincena_clave):
    """Lanzar tarea en el fondo para Generar archivo XLSX con las dispersiones pensionados de una quincena CERRADA"""
    quincena = Quincena.query.filter_by(clave=quincena_clave).first_or_404()
    current_user.launch_task(
        comando="nominas.tasks.generar_dispersiones_pensionados",
        mensaje="Lanzando generar dispersiones pensionados...",
        quincena_clave=quincena_clave,
    )
    flash("Se ha lanzado la tarea en el fondo. Esta página se va a recargar en 10 segundos...", "info")
    return redirect(url_for("quincenas.detail", quincena_id=quincena.id))
