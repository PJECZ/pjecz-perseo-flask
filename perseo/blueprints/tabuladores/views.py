"""
Tabuladores, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_clave, safe_message
from perseo.blueprints.bitacoras.models import Bitacora
from perseo.blueprints.modulos.models import Modulo
from perseo.blueprints.permisos.models import Permiso
from perseo.blueprints.puestos.models import Puesto
from perseo.blueprints.tabuladores.forms import TabuladorForm
from perseo.blueprints.tabuladores.models import Tabulador
from perseo.blueprints.usuarios.decorators import permission_required

MODULO = "TABULADORES"

tabuladores = Blueprint("tabuladores", __name__, template_folder="templates")


@tabuladores.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@tabuladores.route("/tabuladores/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Tabuladores"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Tabulador.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "puesto_id" in request.form:
        consulta = consulta.filter_by(puesto_id=request.form["puesto_id"])
    if "modelo" in request.form:
        consulta = consulta.filter_by(modelo=request.form["modelo"])
    if "nivel" in request.form:
        consulta = consulta.filter_by(nivel=request.form["nivel"])
    if "quinquenio" in request.form:
        consulta = consulta.filter_by(quinquenio=request.form["quinquenio"])
    # Luego filtrar por columnas de otras tablas
    if "puesto_clave" in request.form:
        try:
            puesto_clave = safe_clave(request.form["puesto_clave"], max_len=24)
            if puesto_clave != "":
                consulta = consulta.join(Puesto)
                consulta = consulta.filter(Puesto.clave.contains(puesto_clave))
        except ValueError:
            pass
    # Ordenar y paginar
    registros = consulta.order_by(Tabulador.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("tabuladores.detail", tabulador_id=resultado.id),
                },
                "puesto": {
                    "clave": resultado.puesto.clave,
                    "url": url_for("puestos.detail", puesto_id=resultado.puesto_id),
                },
                "modelo": resultado.modelo,
                "nivel": resultado.nivel,
                "quinquenio": resultado.quinquenio,
                "fecha": resultado.fecha.strftime("%Y-%m-%d"),
                "sueldo_base": resultado.sueldo_base,
                "monedero": resultado.monedero,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@tabuladores.route("/tabuladores")
def list_active():
    """Listado de Tabuladores activos"""
    return render_template(
        "tabuladores/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Tabuladores",
        estatus="A",
    )


@tabuladores.route("/tabuladores/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Tabuladores inactivos"""
    return render_template(
        "tabuladores/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Tabuladores inactivos",
        estatus="B",
    )


@tabuladores.route("/tabuladores/<int:tabulador_id>")
def detail(tabulador_id):
    """Detalle de un Tabulador"""
    tabulador = Tabulador.query.get_or_404(tabulador_id)
    return render_template("tabuladores/detail.jinja2", tabulador=tabulador)


@tabuladores.route("/tabuladores/exportar_xlsx")
def exportar_xlsx():
    """Lanzar tarea en el fondo para exportar los Tabuladores a un archivo XLSX"""
    tarea = current_user.launch_task(
        comando="tabuladores.tasks.lanzar_exportar_xlsx",
        mensaje="Exportando los Tabuladores a un archivo XLSX...",
    )
    flash("Se ha lanzado esta tarea en el fondo. Esta página se va a recargar en 10 segundos...", "info")
    return redirect(url_for("tareas.detail", tarea_id=tarea.id))


@tabuladores.route("/tabuladores/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo Tabulador"""
    form = TabuladorForm()
    if form.validate_on_submit():
        # Inicializar es_valido
        es_valido = True
        # Validar que solo modelo 2 tenga quinquenio mayor a cero
        if form.modelo.data != 2 and form.quinquenio.data > 0:
            flash("Solo el modelo 2) SINDICALIZADO puede tener quinquenio mayor a cero.", "warning")
            es_valido = False
        # Validar que puesto_id, modelo, nivel y quinquenio no se repitan
        tabulador_existente = Tabulador.query.filter_by(
            puesto=form.puesto.data,
            modelo=form.modelo.data,
            nivel=form.nivel.data,
            quinquenio=form.quinquenio.data,
        ).first()
        if tabulador_existente:
            flash("El Tabulador ya existe.", "warning")
            es_valido = False
        # Si es valido, guardar
        if es_valido:
            tabulador = Tabulador(
                puesto=form.puesto.data,
                modelo=form.modelo.data,
                nivel=form.nivel.data,
                quinquenio=form.quinquenio.data,
                fecha=form.fecha.data,
                sueldo_base=form.sueldo_base.data,
                incentivo=form.incentivo.data,
                monedero=form.monedero.data,
                rec_cul_dep=form.rec_cul_dep.data,
                sobresueldo=form.sobresueldo.data,
                rec_dep_cul_gravado=form.rec_dep_cul_gravado.data,
                rec_dep_cul_excento=form.rec_dep_cul_excento.data,
                ayuda_transp=form.ayuda_transp.data,
                monto_quinquenio=form.monto_quinquenio.data,
                total_percepciones=form.total_percepciones.data,
                salario_diario=form.salario_diario.data,
                prima_vacacional_mensual=form.prima_vacacional_mensual.data,
                aguinaldo_mensual=form.aguinaldo_mensual.data,
                prima_vacacional_mensual_adicional=form.prima_vacacional_mensual_adicional.data,
                total_percepciones_integrado=form.total_percepciones_integrado.data,
                salario_diario_integrado=form.salario_diario_integrado.data,
                pension_vitalicia_excento=form.pension_vitalicia_excento.data,
                pension_vitalicia_gravable=form.pension_vitalicia_gravable.data,
                pension_bonificacion=form.pension_bonificacion.data,
            )
            tabulador.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nuevo Tabulador {tabulador.puesto_id}"),
                url=url_for("tabuladores.detail", tabulador_id=tabulador.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    return render_template("tabuladores/new.jinja2", form=form)


@tabuladores.route("/tabuladores/edicion/<int:tabulador_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(tabulador_id):
    """Editar Tabulador"""
    tabulador = Tabulador.query.get_or_404(tabulador_id)
    form = TabuladorForm()
    if form.validate_on_submit():
        # Inicializar es_valido
        es_valido = True
        # Validar que solo el modelo 2 tenga quinquenio mayor a cero
        if form.modelo.data != 2 and form.quinquenio.data > 0:
            flash("Solo el modelo 2) SINDICALIZADO puede tener quinquenio mayor a cero.", "warning")
            es_valido = False
        # Validar que puesto_id, modelo, nivel y quinquenio no se repitan
        tabulador_existente = Tabulador.query.filter_by(
            puesto=form.puesto.data,
            modelo=form.modelo.data,
            nivel=form.nivel.data,
            quinquenio=form.quinquenio.data,
        ).first()
        if tabulador_existente and tabulador_existente.id != tabulador.id:
            flash("El Tabulador ya existe.", "warning")
            es_valido = False
        # Si es valido, guardar
        if es_valido:
            tabulador.puesto = form.puesto.data
            tabulador.modelo = form.modelo.data
            tabulador.nivel = form.nivel.data
            tabulador.quinquenio = form.quinquenio.data
            tabulador.fecha = form.fecha.data
            tabulador.sueldo_base = form.sueldo_base.data
            tabulador.incentivo = form.incentivo.data
            tabulador.monedero = form.monedero.data
            tabulador.rec_cul_dep = form.rec_cul_dep.data
            tabulador.sobresueldo = form.sobresueldo.data
            tabulador.rec_dep_cul_gravado = form.rec_dep_cul_gravado.data
            tabulador.rec_dep_cul_excento = form.rec_dep_cul_excento.data
            tabulador.ayuda_transp = form.ayuda_transp.data
            tabulador.monto_quinquenio = form.monto_quinquenio.data
            tabulador.total_percepciones = form.total_percepciones.data
            tabulador.salario_diario = form.salario_diario.data
            tabulador.prima_vacacional_mensual = form.prima_vacacional_mensual.data
            tabulador.aguinaldo_mensual = form.aguinaldo_mensual.data
            tabulador.prima_vacacional_mensual_adicional = form.prima_vacacional_mensual_adicional.data
            tabulador.total_percepciones_integrado = form.total_percepciones_integrado.data
            tabulador.salario_diario_integrado = form.salario_diario_integrado.data
            tabulador.pension_vitalicia_excento = form.pension_vitalicia_excento.data
            tabulador.pension_vitalicia_gravable = form.pension_vitalicia_gravable.data
            tabulador.pension_bonificacion = form.pension_bonificacion.data
            tabulador.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado Tabulador {tabulador.puesto}"),
                url=url_for("tabuladores.detail", tabulador_id=tabulador.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    form.puesto.data = tabulador.puesto
    form.modelo.data = tabulador.modelo
    form.nivel.data = tabulador.nivel
    form.quinquenio.data = tabulador.quinquenio
    form.fecha.data = tabulador.fecha
    form.sueldo_base.data = tabulador.sueldo_base
    form.incentivo.data = tabulador.incentivo
    form.monedero.data = tabulador.monedero
    form.rec_cul_dep.data = tabulador.rec_cul_dep
    form.sobresueldo.data = tabulador.sobresueldo
    form.rec_dep_cul_gravado.data = tabulador.rec_dep_cul_gravado
    form.rec_dep_cul_excento.data = tabulador.rec_dep_cul_excento
    form.ayuda_transp.data = tabulador.ayuda_transp
    form.monto_quinquenio.data = tabulador.monto_quinquenio
    form.total_percepciones.data = tabulador.total_percepciones
    form.salario_diario.data = tabulador.salario_diario
    form.prima_vacacional_mensual.data = tabulador.prima_vacacional_mensual
    form.aguinaldo_mensual.data = tabulador.aguinaldo_mensual
    form.prima_vacacional_mensual_adicional.data = tabulador.prima_vacacional_mensual_adicional
    form.total_percepciones_integrado.data = tabulador.total_percepciones_integrado
    form.salario_diario_integrado.data = tabulador.salario_diario_integrado
    form.pension_vitalicia_excento.data = tabulador.pension_vitalicia_excento
    form.pension_vitalicia_gravable.data = tabulador.pension_vitalicia_gravable
    form.pension_bonificacion.data = tabulador.pension_bonificacion
    return render_template("tabuladores/edit.jinja2", form=form, tabulador=tabulador)


@tabuladores.route("/tabuladores/eliminar/<int:tabulador_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(tabulador_id):
    """Eliminar Tabulador"""
    tabulador = Tabulador.query.get_or_404(tabulador_id)
    if tabulador.estatus == "A":
        tabulador.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Tabulador {tabulador.id}"),
            url=url_for("tabuladores.detail", tabulador_id=tabulador.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("tabuladores.detail", tabulador_id=tabulador.id))


@tabuladores.route("/tabuladores/recuperar/<int:tabulador_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(tabulador_id):
    """Recuperar Tabulador"""
    tabulador = Tabulador.query.get_or_404(tabulador_id)
    if tabulador.estatus == "B":
        tabulador.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Tabulador {tabulador.id}"),
            url=url_for("tabuladores.detail", tabulador_id=tabulador.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("tabuladores.detail", tabulador_id=tabulador.id))
