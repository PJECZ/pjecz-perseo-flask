"""
Generadores de contraseñas
"""

import random
import re
import string

PASSWORD_REGEXP = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d]{8,24}$"


def generar_api_key(id: int, email: str, random_length: int = 24) -> str:
    """Generar API key a partir de un ID, un e-mail y una cadena aleatoria"""
    aleatorio = "".join(random.sample(string.ascii_letters + string.digits, k=random_length))
    hash_email = Hashids(salt=email, min_length=8).encode(1)
    hash_id = Hashids(salt=settings.SALT, min_length=8).encode(id)
    return f"{hash_id}.{hash_email}.{aleatorio}"


def generar_contrasena(largo=16):
    """Generar contraseña con minúsculas, mayúsculas, dígitos y signos"""
    minusculas = string.ascii_lowercase
    mayusculas = string.ascii_uppercase
    digitos = string.digits
    todos = minusculas + mayusculas + digitos
    contrasena = ""
    while re.match(PASSWORD_REGEXP, contrasena) is None:
        temp = random.sample(todos, largo)
        contrasena = "".join(temp)
    return contrasena
