"""
Quincenas Productos, vistas
"""
import json

from flask import Blueprint, current_app, flash, make_response, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.exceptions import MyAnyError
from lib.google_cloud_storage import get_blob_name_from_url, get_file_from_gcs
from lib.safe_string import safe_message, safe_quincena
from perseo.blueprints.bitacoras.models import Bitacora
from perseo.blueprints.modulos.models import Modulo
from perseo.blueprints.permisos.models import Permiso
from perseo.blueprints.quincenas.models import Quincena
from perseo.blueprints.quincenas_productos.models import QuincenaProducto
from perseo.blueprints.usuarios.decorators import permission_required

MODULO = "QUINCENAS PRODUCTOS"

quincenas_productos = Blueprint("quincenas_productos", __name__, template_folder="templates")


@quincenas_productos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@quincenas_productos.route("/quincenas_productos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Quincenas Productos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = QuincenaProducto.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "fuente" in request.form:
        consulta = consulta.filter_by(fuente=request.form["fuente"])
    if "quincena_id" in request.form:
        consulta = consulta.filter_by(quincena_id=request.form["quincena_id"])
    # Luego filtrar por columnas de otras tablas
    if "quincena_clave" in request.form:
        try:
            quincena_clave = safe_quincena(request.form["quincena_clave"])
            consulta = consulta.join(Quincena)
            consulta = consulta.filter(Quincena.clave == quincena_clave)
        except ValueError:
            pass
    # Ordenar y paginar
    registros = consulta.order_by(QuincenaProducto.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("quincenas_productos.detail", quincena_producto_id=resultado.id),
                },
                "quincena_clave": resultado.quincena.clave,
                "fuente": resultado.fuente,
                "mensajes": resultado.mensajes,
                "archivo": {
                    "nombre_archivo": resultado.archivo,
                    "url": resultado.url,
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@quincenas_productos.route("/quincenas_productos")
def list_active():
    """Listado de Quincenas Productos activos"""
    return render_template(
        "quincenas_productos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Productos",
        estatus="A",
    )


@quincenas_productos.route("/quincenas_productos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Quincenas Productos inactivos"""
    return render_template(
        "quincenas_productos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Productos inactivos",
        estatus="B",
    )


@quincenas_productos.route("/quincenas_productos/<int:quincena_producto_id>")
def detail(quincena_producto_id):
    """Detalle de un Quincena Producto"""
    quincena_producto = QuincenaProducto.query.get_or_404(quincena_producto_id)
    return render_template("quincenas_productos/detail.jinja2", quincena_producto=quincena_producto)


@quincenas_productos.route("/quincenas_productos/<int:quincena_producto_id>/xlsx")
def download_xlsx(quincena_producto_id):
    """Descargar archivo XLSX de una Quincena Producto"""

    # Consultar la Quincena Producto
    quincena_producto = QuincenaProducto.query.get_or_404(quincena_producto_id)

    # Si no tiene URL, regidir a la página de detalle
    if quincena_producto.url == "":
        flash("La Quincena Producto no tiene un archivo XLSX", "warning")
        return redirect(url_for("quincenas_productos.detail", quincena_producto_id=quincena_producto.id))

    # Si no tiene nombre para el archivo, elaborar uno con la clave de la quincena y la fuente
    descarga_nombre = quincena_producto.archivo
    if descarga_nombre == "":
        fuente_str = quincena_producto.fuente.replace(" ", "_").lower()
        descarga_nombre = f"{quincena_producto.quincena.clave}-{fuente_str}.xlsx"

    # Obtener el contenido del archivo desde Google Storage
    try:
        descarga_contenido = get_file_from_gcs(
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO"],
            blob_name=get_blob_name_from_url(quincena_producto.url),
        )
    except MyAnyError as error:
        flash(str(error), "danger")
        return redirect(url_for("quincenas_productos.detail", quincena_producto_id=quincena_producto.id))

    # Descargar un archivo XLSX
    response = make_response(descarga_contenido)
    response.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    response.headers["Content-Disposition"] = f"attachment; filename={descarga_nombre}"
    return response


@quincenas_productos.route("/quincenas_productos/eliminar/<int:quincena_producto_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(quincena_producto_id):
    """Eliminar Quincena Producto"""
    quincena_producto = QuincenaProducto.query.get_or_404(quincena_producto_id)
    if quincena_producto.estatus == "A":
        quincena_producto.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Quincena Producto {quincena_producto.archivo}"),
            url=url_for("quincenas_productos.detail", quincena_producto_id=quincena_producto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("quincenas.detail", quincena_id=quincena_producto.quincena_id))


@quincenas_productos.route("/quincenas_productos/recuperar/<int:quincena_producto_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(quincena_producto_id):
    """Recuperar Quincena Producto"""
    quincena_producto = QuincenaProducto.query.get_or_404(quincena_producto_id)
    if quincena_producto.estatus == "B":
        quincena_producto.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Quincena Producto {quincena_producto.archivo}"),
            url=url_for("quincenas_productos.detail", quincena_producto_id=quincena_producto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("quincenas.detail", quincena_id=quincena_producto.quincena_id))
