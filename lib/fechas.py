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
