"""
Fechas
"""
from datetime import date


def crear_clave_quincena(fecha: date = None) -> str:
    """Crear clave de quincena como AAAANN donde NN es el numero de quincena"""

    # Si no se proporciona la fecha, usar la fecha actual
    if fecha is None:
        fecha = date.today()

    # Obtener año
    anio_str = str(fecha.year)

    # Si el dia es entre 1 y 15, es la primer quincena
    if fecha.day <= 15:
        quincena_sumar = 0
    else:
        quincena_sumar = 1

    # Obtener quincena, multiplicando el numero del mes por dos y sumando quincena_sumar
    quincena = fecha.month * 2 + quincena_sumar - 1

    # Entregar la clave de quincena como AAAANN
    return anio_str + str(quincena).zfill(2)


def fecha_to_quincena(fecha: date) -> str:
    """Convierte una fecha en quincena"""

    quincena = fecha.month * 2

    if fecha.day < 16:
        quincena = quincena - 1

    return f"{fecha.year}{quincena:02d}"


def quincena_count(desde: date, hasta: date) -> int:
    """Cuenta el número de quincenas entre dos fechas dadas"""

    # Si la fecha desde es mayor a la fecha hasta, las intercambia
    if desde > hasta:
        desde, hasta = hasta, desde

    # Cuenta la diferencia de años
    count = (hasta.year - desde.year) * 24

    quincena_desde = int(fecha_to_quincena(desde)[4:6])
    quincena_hasta = int(fecha_to_quincena(hasta)[4:6])

    # Sumamos los años más las quincenas
    count = count + quincena_hasta - quincena_desde

    return count
