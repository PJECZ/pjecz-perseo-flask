"""
Fechas
"""

import calendar
import math
import re
from datetime import date

QUINCENA_REGEXP = r"^\d{6}$"


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


def quincena_to_fecha(quincena_clave: str, dame_ultimo_dia: bool = False) -> date:
    """Dando un quincena AAAANN donde NN es el número de quincena regresamos una fecha"""

    # Validar str de quincena
    quincena_clave = quincena_clave.strip()
    if re.match(QUINCENA_REGEXP, quincena_clave) is None:
        raise ValueError("Quincena invalida")

    # Validar año de la quincena
    anio = int(quincena_clave[:-2])
    if anio < 1950 or anio > date.today().year:
        raise ValueError("Quincena (año) fuera de rango")

    # Validar número de quincena
    num_quincena = int(quincena_clave[4:])
    if 0 <= num_quincena >= 25:
        raise ValueError("Quincena (número de quincena) fuera de rango")

    # Calcular el mes
    mes = math.ceil(num_quincena / 2)

    # Si se solicita el ultimo dia de la quincena
    if dame_ultimo_dia:
        # Si es quincena par
        if num_quincena % 2 == 0:
            _, dia = calendar.monthrange(anio, mes)  # Es 30 o 31 o el 28 o 29 de febrero
        else:
            dia = 15  # Siempre es 15
    else:
        # Si es quincena par
        if num_quincena % 2 == 0:
            dia = 16  # La quincena comienza el 16
        else:
            dia = 1  # La quincena comienza el 1

    # Entregar
    return date(anio, mes, dia)


def quinquenio_count(desde: date, hasta: date) -> int:
    """Cuenta la cantidad de quinquenios entre dos fechas dadas"""

    # Si la fecha 'desde' es mayor a la de 'hasta' intercambiar las fechas.
    if desde > hasta:
        desde, hasta = hasta, desde

    # Diferencia de años entre fechas
    diff_fechas = hasta - desde
    diff_years = diff_fechas.days / 365.25

    # Contamos cada quinquenio, grupos de 5 años
    count = math.floor(diff_years / 5)

    # Solo puede haber un máximo de 6 quinquenios
    count = min(count, 6)

    # Entregar el conteo de quinquenios
    return count
