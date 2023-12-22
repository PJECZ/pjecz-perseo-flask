"""
Nominas, comunes para los generadores
"""
import logging
import re

from lib.exceptions import MyNotExistsError, MyNotValidParamError
from lib.safe_string import QUINCENA_REGEXP
from perseo.app import create_app
from perseo.blueprints.quincenas.models import Quincena
from perseo.blueprints.quincenas_productos.models import QuincenaProducto
from perseo.extensions import database

GCS_BASE_DIRECTORY = "reports/nominas"
LOCAL_BASE_DIRECTORY = "reports/nominas"
TIMEZONE = "America/Mexico_City"

bitacora = logging.getLogger(__name__)
bitacora.setLevel(logging.INFO)
formato = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")
empunadura = logging.FileHandler("nominas.log")
empunadura.setFormatter(formato)
bitacora.addHandler(empunadura)

app = create_app()
app.app_context().push()
database.app = app


def consultar_validar_quincena(quincena_clave: str) -> Quincena:
    """Consultar y validar la quincena"""

    # Validar quincena_clave
    if re.match(QUINCENA_REGEXP, quincena_clave) is None:
        raise MyNotValidParamError("Clave de la quincena inválida.")

    # Consultar quincena
    quincena = Quincena.query.filter_by(clave=quincena_clave).first()

    # Si no existe la quincena, provocar error y terminar
    if quincena is None:
        return MyNotExistsError(f"No existe la quincena {quincena_clave}")

    # Si la quincena no esta ABIERTA, provocar error y terminar
    if quincena.estado != "ABIERTA":
        return MyNotValidParamError(f"La quincena {quincena_clave} no esta ABIERTA")

    # Si la quincena esta eliminada, provocar error y terminar
    if quincena.estatus != "A":
        return MyNotValidParamError(f"La quincena {quincena_clave} esta eliminada")

    # Entregar la quincena
    return quincena


def actualizar_quincena_producto(
    quincena_producto_id: int,
    quincena_id: int,
    fuente: str,
    mensajes: list,
    archivo: str = "",
    url: str = "",
    es_satisfactorio: bool = False,
) -> QuincenaProducto:
    """Actualizar la quincena_producto"""

    # Validar fuente
    if fuente not in QuincenaProducto.FUENTES:
        raise MyNotValidParamError("Fuente inválida.")

    # Si quincena_producto_id es cero
    if quincena_producto_id == 0:
        # Agregar un registro para conservar las rutas y mensajes
        quincena_producto = QuincenaProducto(
            quincena_id=quincena_id,
            archivo=archivo,
            es_satisfactorio=es_satisfactorio,
            fuente=fuente,
            mensajes="\n".join(mensajes),
            url=url,
        )
    else:
        # Si quincena_producto_id es diferente de cero, actualizar el registro
        quincena_producto = QuincenaProducto.query.get(quincena_producto_id)
        quincena_producto.archivo = archivo
        quincena_producto.es_satisfactorio = es_satisfactorio
        quincena_producto.fuente = fuente
        quincena_producto.mensajes = "\n".join(mensajes)
        quincena_producto.url = url
    quincena_producto.save()

    # Entregar la quincena_producto
    return quincena_producto
