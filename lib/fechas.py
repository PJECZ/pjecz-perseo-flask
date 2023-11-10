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


def quincena_to_fecha(quincena: str, dame_ultimo_dia: bool = False) -> date:
    """Dando un quincena AAAANN donde NN es el número de quincena regresamos una fecha"""

    # Validar str de quincena
    quincena = quincena.strip()
    if re.match(QUINCENA_REGEXP, quincena) is None:
        raise ValueError("Quincena invalida")

    # Validar año de la quincena
    anio = int(quincena[:-2])
    if anio < 2000 or anio > date.today().year:
        raise ValueError("Quincena (año) fuera de rango")

    # Validar número de quincena
    num_quincena = int(quincena[4:])
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
