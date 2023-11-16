"""
Quincenas, vistas
"""
import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message, safe_quincena
from perseo.blueprints.bitacoras.models import Bitacora
from perseo.blueprints.modulos.models import Modulo
from perseo.blueprints.permisos.models import Permiso
from perseo.blueprints.quincenas.forms import QuincenaForm
from perseo.blueprints.quincenas.models import Quincena
from perseo.blueprints.quincenas_productos.models import QuincenaProducto
from perseo.blueprints.usuarios.decorators import permission_required

MODULO = "QUINCENAS"

quincenas = Blueprint("quincenas", __name__, template_folder="templates")


@quincenas.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@quincenas.route("/quincenas/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Quincenas"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Quincena.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "quincena_clave" in request.form:
        try:
            consulta = consulta.filter_by(quincena=safe_quincena(request.form["quincena_clave"]))
        except ValueError:
            pass
    # Ordenar y paginar
    registros = consulta.order_by(Quincena.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "clave": resultado.clave,
                    "url": url_for("quincenas.detail", quincena_id=resultado.id),
                },
                "estado": resultado.estado,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@quincenas.route("/quincenas")
def list_active():
    """Listado de Quincenas activas"""
    return render_template(
        "quincenas/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Quincenas",
        estatus="A",
    )


@quincenas.route("/quincenas/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Quincenas inactivas"""
    return render_template(
        "quincenas/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Quincenas inactivas",
        estatus="B",
    )


@quincenas.route("/quincenas/<int:quincena_id>")
def detail(quincena_id):
    """Detalle de una Quincena"""
    quincena = Quincena.query.get_or_404(quincena_id)
    return render_template("quincenas/detail.jinja2", quincena=quincena)


@quincenas.route("/quincenas/edicion/<int:quincena_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(quincena_id):
    """Editar Quincena"""
    quincena = Quincena.query.get_or_404(quincena_id)
    form = QuincenaForm()
    if form.validate_on_submit():
        es_valido = True
        # Validar la clave de la quincena
        try:
            clave = safe_quincena(form.clave.data)
        except ValueError:
            flash("Quincena inválida", "warning")
            es_valido = False
        # Si cambia la clave, verificar que no este en uso
        if es_valido and clave != quincena.clave:
            quincena_existente = Quincena.query.filter_by(clave=clave).first()
            if quincena_existente and quincena_existente.id != quincena.id:
                flash("La quincena ya está en uso. Debe de ser única.", "warning")
                es_valido = False
        # Si es valido actualizar
        if es_valido:
            quincena.clave = clave
            quincena.estado = form.estado.data
            quincena.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editada Quincena {quincena.clave} con estado {quincena.estado}"),
                url=url_for("quincenas.detail", quincena_id=quincena.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    form.clave.data = quincena.clave
    form.estado.data = quincena.estado
    return render_template("quincenas/edit.jinja2", form=form, quincena=quincena)


@quincenas.route("/quincenas/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo Quincena"""
    form = QuincenaForm()
    if form.validate_on_submit():
        es_valido = True
        # Validar la clave de la quincena
        try:
            clave = safe_quincena(form.clave.data)
        except ValueError:
            flash("Quincena inválida", "warning")
            es_valido = False
        # Validar que la clave no este en uso
        if es_valido and Quincena.query.filter_by(clave=clave).first():
            flash("La quincena ya está en uso. Debe de ser única.", "warning")
            es_valido = False
        # Si es valido, guardar
        if es_valido:
            quincena = Quincena(clave=clave, estado=form.estado.data)
            quincena.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nueva Quincena {quincena.clave} como {quincena.estado}"),
                url=url_for("quincenas.detail", quincena_id=quincena.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    return render_template("quincenas/new.jinja2", form=form)


@quincenas.route("/quincenas/eliminar/<int:quincena_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(quincena_id):
    """Eliminar Quincena"""
    quincena = Quincena.query.get_or_404(quincena_id)
    if quincena.estatus == "A":
        quincena.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminada Quincena {quincena.clave}"),
            url=url_for("quincenas.detail", quincena_id=quincena.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("quincenas.detail", quincena_id=quincena.id))


@quincenas.route("/quincenas/recuperar/<int:quincena_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(quincena_id):
    """Recuperar Quincena"""
    quincena = Quincena.query.get_or_404(quincena_id)
    if quincena.estatus == "B":
        quincena.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperada Quincena {quincena.clave}"),
            url=url_for("quincenas.detail", quincena_id=quincena.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("quincenas.detail", quincena_id=quincena.id))


@quincenas.route("/quincenas/cerrar")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def close():
    """Lanzar tarea en el fondo para cerrar las quincenas pasadas, menos la ultima"""
    current_user.launch_task(comando="quincenas.tasks.cerrar", mensaje="Lanzando cerrar quincenas...")
    flash("Se ha lanzado la tarea en el fondo. Esta página se va a recargar en 10 segundos...", "info")
    return redirect(url_for("quincenas.list_active"))


@quincenas.route("/quincenas/generar_nominas/<int:quincena_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def generate_nominas(quincena_id):
    """Lanzar tarea en el fondo para crear un archivo XLSX con las nominas de una quincena"""
    # Consultar y validar la quincena
    quincena = Quincena.query.get_or_404(quincena_id)
    if quincena.estatus != "A":
        flash("Quincena no activa", "warning")
        return redirect(url_for("quincenas.detail", quincena_id=quincena.id))
    if quincena.estado != "ABIERTA":
        flash("Quincena no abierta", "warning")
        return redirect(url_for("quincenas.detail", quincena_id=quincena.id))
    # Agregar producto
    quincena_producto = QuincenaProducto(
        quincena=quincena,
        archivo="",
        es_satisfactorio=False,
        fuente="NOMINAS",
        mensajes="Lanzando nominas.tasks.generar_nominas...",
        url="",
    )
    quincena_producto.save()
    # Lanzar la tarea en el fondo
    current_user.launch_task(
        comando="nominas.tasks.generar_nominas",
        mensaje="Lanzando nominas.tasks.generar_nominas...",
        quincena_clave=quincena.clave,
        quincena_producto_id=quincena_producto.id,
    )
    flash("Se ha lanzado la tarea en el fondo. Esta página se va a recargar en 10 segundos...", "info")
    # Redireccionar al detalle del producto
    return redirect(url_for("quincenas_productos.detail", quincena_producto_id=quincena_producto.id))


@quincenas.route("/quincenas/generar_monederos/<int:quincena_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def generate_monederos(quincena_id):
    """Lanzar tarea en el fondo para crear un archivo XLSX con los monederos de una quincena"""
    # Consultar y validar la quincena
    quincena = Quincena.query.get_or_404(quincena_id)
    if quincena.estatus != "A":
        flash("Quincena no activa", "warning")
        return redirect(url_for("quincenas.detail", quincena_id=quincena.id))
    if quincena.estado != "ABIERTA":
        flash("Quincena no abierta", "warning")
        return redirect(url_for("quincenas.detail", quincena_id=quincena.id))
    # Agregar producto
    quincena_producto = QuincenaProducto(
        quincena=quincena,
        archivo="",
        es_satisfactorio=False,
        fuente="MONEDEROS",
        mensajes="Lanzando nominas.tasks.generar_monederos...",
        url="",
    )
    quincena_producto.save()
    # Lanzar la tarea en el fondo
    current_user.launch_task(
        comando="nominas.tasks.generar_monederos",
        mensaje="Lanzando nominas.tasks.generar_monederos...",
        quincena_clave=quincena.clave,
        quincena_producto_id=quincena_producto.id,
    )
    flash("Se ha lanzado la tarea en el fondo. Esta página se va a recargar en 10 segundos...", "info")
    # Redireccionar al detalle del producto
    return redirect(url_for("quincenas_productos.detail", quincena_producto_id=quincena_producto.id))


@quincenas.route("/quincenas/generar_pensionados/<int:quincena_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def generate_pensionados(quincena_id):
    """Lanzar tarea en el fondo para crear un archivo XLSX con los pensionados de una quincena"""
    # Consultar y validar la quincena
    quincena = Quincena.query.get_or_404(quincena_id)
    if quincena.estatus != "A":
        flash("Quincena no activa", "warning")
        return redirect(url_for("quincenas.detail", quincena_id=quincena.id))
    if quincena.estado != "ABIERTA":
        flash("Quincena no abierta", "warning")
        return redirect(url_for("quincenas.detail", quincena_id=quincena.id))
    # Agregar producto
    quincena_producto = QuincenaProducto(
        quincena=quincena,
        archivo="",
        es_satisfactorio=False,
        fuente="PENSIONADOS",
        mensajes="Lanzando nominas.tasks.generar_pensionados...",
        url="",
    )
    quincena_producto.save()
    # Lanzar la tarea en el fondo
    current_user.launch_task(
        comando="nominas.tasks.generar_pensionados",
        mensaje="Lanzando nominas.tasks.generar_pensionados...",
        quincena_clave=quincena.clave,
        quincena_producto_id=quincena_producto.id,
    )
    flash("Se ha lanzado la tarea en el fondo. Esta página se va a recargar en 10 segundos...", "info")
    # Redireccionar al detalle del producto
    return redirect(url_for("quincenas_productos.detail", quincena_producto_id=quincena_producto.id))


@quincenas.route("/quincenas/generar_dispersiones_pensionados/<int:quincena_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def generar_dispersiones_pensionados(quincena_id):
    """Lanzar tarea en el fondo para crear un archivo XLSX con las dispersiones pensionados de una quincena"""
    # Consultar y validar la quincena
    quincena = Quincena.query.get_or_404(quincena_id)
    if quincena.estatus != "A":
        flash("Quincena no activa", "warning")
        return redirect(url_for("quincenas.detail", quincena_id=quincena.id))
    if quincena.estado != "ABIERTA":
        flash("Quincena no abierta", "warning")
        return redirect(url_for("quincenas.detail", quincena_id=quincena.id))
    # Agregar producto
    quincena_producto = QuincenaProducto(
        quincena=quincena,
        archivo="",
        es_satisfactorio=False,
        fuente="DISPERSIONES PENSIONADOS",
        mensajes="Lanzando nominas.tasks.generar_dispersiones_pensionados...",
        url="",
    )
    quincena_producto.save()
    # Lanzar la tarea en el fondo
    current_user.launch_task(
        comando="nominas.tasks.generar_dispersiones_pensionados",
        mensaje="Lanzando nominas.tasks.generar_dispersiones_pensionados...",
        quincena_clave=quincena.clave,
        quincena_producto_id=quincena_producto.id,
    )
    flash("Se ha lanzado la tarea en el fondo. Esta página se va a recargar en 10 segundos...", "info")
    # Redireccionar al detalle del producto
    return redirect(url_for("quincenas_productos.detail", quincena_producto_id=quincena_producto.id))


@quincenas.route("/quincenas/generar_todos/<int:quincena_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def generar_todos(quincena_id):
    """Lanzar tarea en el fondo para crear todos los archivo XLSX de una quincena"""
    # Consultar y validar la quincena
    quincena = Quincena.query.get_or_404(quincena_id)
    if quincena.estatus != "A":
        flash("Quincena no activa", "warning")
        return redirect(url_for("quincenas.detail", quincena_id=quincena.id))
    if quincena.estado != "ABIERTA":
        flash("Quincena no abierta", "warning")
        return redirect(url_for("quincenas.detail", quincena_id=quincena.id))
    # Lanzar la tarea en el fondo
    current_user.launch_task(
        comando="nominas.tasks.generar_todos",
        mensaje="Lanzando nominas.tasks.generar_todos...",
        quincena_clave=quincena.clave,
    )
    flash("Se ha lanzado la tarea en el fondo. Esta página se va a recargar en 30 segundos...", "info")
    # Redireccionar al listado de productos activos
    return redirect(url_for("quincenas.list_active"))
