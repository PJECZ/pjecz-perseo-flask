"""
Fechas
"""
import re
import math
from datetime import date, timedelta

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

    fecha_actual = date.today()

    # Validar año de la quincena
    anio = int(quincena[:-2])
    if anio <= 1950 or anio >= fecha_actual.year + 2:
        raise ValueError("Quincena (año) fuera de rango")

    # Validar número de quincena
    num_quincena = int(quincena[4:])
    if 0 <= num_quincena >= 25:
        raise ValueError("Quincena (número de quincena) fuera de rango")

    # Calcular mes:
    mes = math.ceil(num_quincena / 2)

    # Calcular día: Si es par el día es 16 sino es día primero
    dia = 0
    if dame_ultimo_dia:
        dia = 15
        if num_quincena % 2 == 0:
            # Calcular el último día del mes
            mes_siguiente = date(anio, mes, 28) + timedelta(days=4)
            fecha_ultimo_dia_mes = mes_siguiente - timedelta(days=mes_siguiente.day)
            dia = fecha_ultimo_dia_mes.day
    else:
        dia = 1
        if num_quincena % 2 == 0:
            dia = 16

    return date(anio, mes, dia)
