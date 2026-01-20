"""
Conceptos-Productos, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ...lib.datatables import get_datatable_parameters, output_datatable_json
from ...lib.safe_string import safe_message
from ..bitacoras.models import Bitacora
from ..conceptos.models import Concepto
from ..modulos.models import Modulo
from ..permisos.models import Permiso
from ..productos.models import Producto
from ..usuarios.decorators import permission_required
from .forms import ConceptoProductoNewWithConceptoForm, ConceptoProductoNewWithProductoForm
from .models import ConceptoProducto

MODULO = "CONCEPTOS PRODUCTOS"

conceptos_productos = Blueprint("conceptos_productos", __name__, template_folder="templates")


@conceptos_productos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@conceptos_productos.route("/conceptos_productos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Conceptos-Productos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = ConceptoProducto.query
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "concepto_id" in request.form:
        consulta = consulta.filter_by(concepto_id=request.form["concepto_id"])
    if "producto_id" in request.form:
        consulta = consulta.filter_by(producto_id=request.form["producto_id"])
    registros = consulta.order_by(ConceptoProducto.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("conceptos_productos.detail", concepto_producto_id=resultado.id),
                },
                "concepto": {
                    "clave": resultado.concepto.clave,
                    "url": (
                        url_for("conceptos.detail", concepto_id=resultado.concepto_id)
                        if current_user.can_view("CONCEPTOS")
                        else ""
                    ),
                },
                "concepto_descripcion": resultado.concepto.descripcion,
                "producto": {
                    "clave": resultado.producto.clave,
                    "url": (
                        url_for("productos.detail", producto_id=resultado.producto_id)
                        if current_user.can_view("PRODUCTOS")
                        else ""
                    ),
                },
                "producto_descripcion": resultado.producto.descripcion,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@conceptos_productos.route("/conceptos_productos")
def list_active():
    """Listado de Conceptos-Productos activos"""
    return render_template(
        "conceptos_productos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Conceptos-Productos",
        estatus="A",
    )


@conceptos_productos.route("/conceptos_productos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Conceptos-Productos inactivos"""
    return render_template(
        "conceptos_productos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Conceptos-Productos inactivos",
        estatus="B",
    )


@conceptos_productos.route("/conceptos_productos/<int:concepto_producto_id>")
def detail(concepto_producto_id):
    """Detalle de un Concepto-Producto"""
    concepto_producto = ConceptoProducto.query.get_or_404(concepto_producto_id)
    return render_template("conceptos_productos/detail.jinja2", concepto_producto=concepto_producto)


@conceptos_productos.route("/conceptos_productos/nuevo_con_concepto/<int:concepto_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new_with_concepto(concepto_id):
    """Nuevo Concepto-Producto con Concepto"""
    concepto = Concepto.query.get_or_404(concepto_id)
    form = ConceptoProductoNewWithConceptoForm()
    if form.validate_on_submit():
        producto = Producto.query.get_or_404(form.producto.data)
        descripcion = f"{concepto.descripcion} en {producto.descripcion}"
        concepto_producto_existente = ConceptoProducto.query.filter(
            ConceptoProducto.concepto == concepto, ConceptoProducto.producto == producto
        ).first()
        if concepto_producto_existente is not None:
            flash(safe_message(f"CONFLICTO: Ya existe {descripcion}."), "warning")
            return redirect(url_for("conceptos_productos.detail", concepto_producto_id=concepto_producto_existente.id))
        concepto_producto = ConceptoProducto(
            concepto=concepto,
            producto=producto,
            descripcion=descripcion,
        )
        concepto_producto.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo Concepto-Producto {descripcion}"),
            url=url_for("conceptos_productos.detail", concepto_producto_id=concepto_producto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(url_for("conceptos.detail", concepto_id=concepto.id))
    form.concepto_clave.data = concepto.clave  # Solo lectura
    form.concepto_descripcion.data = concepto.descripcion  # Solo lectura
    return render_template(
        "conceptos_productos/new_with_concepto.jinja2",
        titulo=f"Agregar concepto {concepto.clave} a un producto",
        form=form,
        concepto=concepto,
    )


@conceptos_productos.route("/conceptos_productos/nuevo_con_producto/<int:producto_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new_with_producto(producto_id):
    """Nuevo Concepto-Producto con Producto"""
    producto = Producto.query.get_or_404(producto_id)
    form = ConceptoProductoNewWithProductoForm()
    if form.validate_on_submit():
        concepto = Concepto.query.get_or_404(form.concepto.data)
        descripcion = f"{concepto.descripcion} en {producto.descripcion}"
        concepto_producto_existente = ConceptoProducto.query.filter(
            ConceptoProducto.concepto == concepto, ConceptoProducto.producto == producto
        ).first()
        if concepto_producto_existente is not None:
            flash(safe_message(f"CONFLICTO: Ya existe {descripcion}."), "warning")
            return redirect(url_for("conceptos_productos.detail", concepto_producto_id=concepto_producto_existente.id))
        concepto_producto = ConceptoProducto(
            concepto=concepto,
            producto=producto,
            descripcion=descripcion,
        )
        concepto_producto.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo Concepto-Producto {descripcion}"),
            url=url_for("conceptos_productos.detail", concepto_producto_id=concepto_producto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(url_for("productos.detail", producto_id=producto.id))
    form.producto_clave.data = producto.clave  # Solo lectura
    form.producto_descripcion.data = producto.descripcion  # Solo lectura
    return render_template(
        "conceptos_productos/new_with_producto.jinja2",
        titulo=f"Agregar producto {producto.clave} a un concepto",
        form=form,
        producto=producto,
    )


@conceptos_productos.route("/conceptos_productos/eliminar/<int:concepto_producto_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(concepto_producto_id):
    """Eliminar Concepto-Producto"""
    concepto_producto = ConceptoProducto.query.get_or_404(concepto_producto_id)
    if concepto_producto.estatus == "A":
        concepto_producto.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Concepto-Producto {concepto_producto.descripcion}"),
            url=url_for("conceptos_productos.detail", concepto_producto_id=concepto_producto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("conceptos_productos.detail", concepto_producto_id=concepto_producto.id))


@conceptos_productos.route("/conceptos_productos/recuperar/<int:concepto_producto_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(concepto_producto_id):
    """Recuperar Concepto-Producto"""
    concepto_producto = ConceptoProducto.query.get_or_404(concepto_producto_id)
    if concepto_producto.estatus == "B":
        concepto_producto.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Concepto-Producto {concepto_producto.descripcion}"),
            url=url_for("conceptos_productos.detail", concepto_producto_id=concepto_producto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("conceptos_productos.detail", concepto_producto_id=concepto_producto.id))
