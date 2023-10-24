"""
Productos, vistas
"""
import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_clave, safe_message, safe_string
from perseo.blueprints.bitacoras.models import Bitacora
from perseo.blueprints.modulos.models import Modulo
from perseo.blueprints.permisos.models import Permiso
from perseo.blueprints.productos.forms import ProductoForm
from perseo.blueprints.productos.models import Producto
from perseo.blueprints.usuarios.decorators import permission_required

MODULO = "PRODUCTOS"

productos = Blueprint("productos", __name__, template_folder="templates")


@productos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@productos.route("/productos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Productos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Producto.query
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    registros = consulta.order_by(Producto.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "clave": resultado.clave,
                    "url": url_for("productos.detail", producto_id=resultado.id),
                },
                "descripcion": resultado.descripcion,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@productos.route("/productos")
def list_active():
    """Listado de Productos activos"""
    return render_template(
        "productos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Productos",
        estatus="A",
    )


@productos.route("/productos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Productos inactivos"""
    return render_template(
        "productos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Productos inactivos",
        estatus="B",
    )


@productos.route("/productos/<int:producto_id>")
def detail(producto_id):
    """Detalle de un Producto"""
    producto = Producto.query.get_or_404(producto_id)
    return render_template("productos/detail.jinja2", producto=producto)


@productos.route("/productos/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo Producto"""
    form = ProductoForm()
    if form.validate_on_submit():
        # Validar que la clave no se repita
        clave = safe_clave(form.clave.data)
        if Producto.query.filter_by(clave=clave).first():
            form.clave.errors.append("Clave repetida")
        else:
            producto = Producto(
                clave=clave,
                descripcion=safe_string(form.descripcion.data, save_enie=True),
            )
            producto.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nuevo Producto {producto.clave}"),
                url=url_for("productos.detail", producto_id=producto.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    return render_template("productos/new.jinja2", form=form)


@productos.route("/productos/edicion/<int:producto_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(producto_id):
    """Editar Producto"""
    producto = Producto.query.get_or_404(producto_id)
    form = ProductoForm()
    if form.validate_on_submit():
        es_valido = True
        # Si cambia la clave verificar que no este en uso
        clave = safe_clave(form.clave.data)
        if producto.clave != clave:
            producto_existente = Producto.query.filter_by(clave=clave).first()
            if producto_existente and producto_existente.id != producto.id:
                es_valido = False
                flash("La clave ya está en uso. Debe de ser única.", "warning")
        # Si es valido actualizar
        if es_valido:
            producto.clave = clave
            producto.descripcion = safe_string(form.descripcion.data)
            producto.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado Producto {producto.descripcion}"),
                url=url_for("productos.detail", producto_id=producto.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    form.clave.data = producto.clave
    form.descripcion.data = producto.descripcion
    return render_template("productos/edit.jinja2", form=form, producto=producto)


@productos.route("/productos/eliminar/<int:producto_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(producto_id):
    """Eliminar Producto"""
    producto = Producto.query.get_or_404(producto_id)
    if producto.estatus == "A":
        producto.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Producto {producto.clave}"),
            url=url_for("productos.detail", producto_id=producto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("productos.detail", producto_id=producto.id))


@productos.route("/productos/recuperar/<int:producto_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(producto_id):
    """Recuperar Producto"""
    producto = Producto.query.get_or_404(producto_id)
    if producto.estatus == "B":
        producto.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Producto {producto.clave}"),
            url=url_for("productos.detail", producto_id=producto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("productos.detail", producto_id=producto.id))
