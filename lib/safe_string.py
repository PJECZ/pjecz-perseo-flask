"""
Safe String
"""
import re

from unidecode import unidecode

CONTRASENA_REGEXP = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d]{8,48}$"
CURP_REGEXP = r"^[a-zA-Z]{4}\d{6}[a-zA-Z]{6}\d{2}$"
EMAIL_REGEXP = r"^[\w.-]+@[\w.-]+\.\w+$"
QUINCENA_REGEXP = r"^\d{6}$"
RFC_REGEXP = r"^[a-zA-Z]{3,4}\d{6}[a-zA-Z0-9]{3}$"
TOKEN_REGEXP = r"^[a-zA-Z0-9_.=+-]+$"


def safe_clave(input_str, max_len=16):
    """Safe clave"""
    if not isinstance(input_str, str):
        return ""
    new_string = re.sub(r"[^a-zA-Z0-9()-]+", " ", unidecode(input_str))
    removed_multiple_spaces = re.sub(r"\s+", " ", new_string)
    spaces_to_dashes = re.sub(r"\s+", "-", removed_multiple_spaces)
    final = spaces_to_dashes.strip().upper()
    if len(final) > max_len:
        return final[:max_len]
    return final


def safe_curp(input_str):
    """Safe CURP"""
    if not isinstance(input_str, str):
        return ""
    # Quitar espacios y solo mayusculas
    curp = unidecode(re.sub(r"\s+", "", input_str).upper())
    # Validar por expresion regular
    if re.match(CURP_REGEXP, curp) is None:
        raise ValueError("CURP inválida")
    # Entregar
    return curp


def safe_email(input_str, search_fragment=False):
    """Safe string"""
    if not isinstance(input_str, str):
        return ""
    final = input_str.strip().lower()
    if search_fragment:
        if re.match(r"^[\w.-]*@*[\w.-]*\.*\w*$", final) is None:
            return ""
        return final
    if re.match(EMAIL_REGEXP, final) is None:
        return ""
    return final


def safe_message(input_str, max_len=250, default_output_str="Sin descripción"):
    """Safe message"""
    message = str(input_str)
    if message == "":
        return default_output_str
    return (message[:max_len] + "...") if len(message) > max_len else message


def safe_rfc(input_str):
    """Safe RFC"""
    if not isinstance(input_str, str):
        return ""
    # Quitar espacios y solo mayusculas
    rfc = unidecode(re.sub(r"\s+", "", input_str).upper())
    # Validar por expresion regular
    if re.match(RFC_REGEXP, rfc) is None:
        raise ValueError("RFC inválido")
    # Entregar
    return rfc


def safe_string(input_str, max_len=250, do_unidecode=True, save_enie=False, to_uppercase=True):
    """Safe string"""
    if not isinstance(input_str, str):
        return ""
    if do_unidecode:
        new_string = re.sub(r"[^a-zA-Z0-9.()/-]+", " ", input_str)
        if save_enie:
            new_string = ""
            for char in input_str:
                if char == "ñ":
                    new_string += "ñ"
                elif char == "Ñ":
                    new_string += "Ñ"
                else:
                    new_string += unidecode(char)
        else:
            new_string = re.sub(r"[^a-zA-Z0-9.()/-]+", " ", unidecode(input_str))
    else:
        if save_enie is False:
            new_string = re.sub(r"[^a-záéíóúüA-ZÁÉÍÓÚÜ0-9.()/-]+", " ", input_str)
        else:
            new_string = re.sub(r"[^a-záéíóúüñA-ZÁÉÍÓÚÜÑ0-9.()/-]+", " ", input_str)
    removed_multiple_spaces = re.sub(r"\s+", " ", new_string)
    final = removed_multiple_spaces.strip()
    if to_uppercase:
        final = final.upper()
    if max_len == 0:
        return final
    return (final[:max_len] + "...") if len(final) > max_len else final
