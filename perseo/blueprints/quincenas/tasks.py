"""
Quincenas, tareas en el fondo
"""
from lib.tasks import set_task_error, set_task_progress
from perseo.app import create_app
from perseo.blueprints.quincenas.models import Quincena
from perseo.extensions import database

app = create_app()
app.app_context().push()
database.app = app


def cerrar():
    """Cerrar las quincenas con estado ABIERTA, a exepcion de la ultima quincena"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, "Cerrando quincenas...")

    # Iniciar sesion con la base de datos para que la alimentacion sea rapida
    sesion = database.session

    # Consultar todas las quincenas con estatus "A"
    quincenas = sesion.query(Quincena).order_by(Quincena.quincena).filter_by(estatus="A").all()

    # Si no hay quincenas, mostrar mensaje de error y salir
    if len(quincenas) == 0:
        set_task_error("No hay quincenas activas.")
        return

    # Inicializar listados que se usan en el mensaje de termino
    quincenas_abiertas = []
    quincenas_cerradas = []

    # Separar la ultima quincena de las demas
    ultima_quincena = quincenas.pop()

    # Bucle por las quincenas
    for quincena_obj in quincenas:
        # Si la quincena esta abierta, cerrarla
        if quincena_obj.estado == "ABIERTA":
            quincena_obj.estado = "CERRADA"
            sesion.add(quincena_obj)
            quincenas_cerradas.append(quincena_obj)

    # Si la ultima quincena esta cerrada, abrirla
    if ultima_quincena.estado == "CERRADA":
        ultima_quincena.estado = "ABIERTA"
        sesion.add(ultima_quincena)
        quincenas_abiertas.append(ultima_quincena)

    # Hacer commit de los cambios en la base de datos
    sesion.commit()

    # Mensaje de termino
    if len(quincenas_abiertas) == 0 and len(quincenas_cerradas) == 0:
        set_task_progress(100, "No se hicieron cambios")
    else:
        cerradas_str = ", ".join([q.quincena for q in quincenas_cerradas])
        abiertas_str = ", ".join([q.quincena for q in quincenas_abiertas])
        set_task_progress(100, f"Cerradas: {cerradas_str} | Abiertas: {abiertas_str}")
