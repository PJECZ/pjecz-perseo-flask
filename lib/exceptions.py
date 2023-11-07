"""
Exceptions
"""


class MyAnyError(Exception):
    """Base exception class"""


class MyAlreadyExistsError(MyAnyError):
    """Excepción porque ya existe"""


class MyAuthenticationError(MyAnyError):
    """Excepción porque fallo la autentificacion"""


class MyBucketNotFoundError(MyAnyError):
    """Excepción porque no se encontró el bucket"""


class MyConnectionError(MyAnyError):
    """Excepción porque no se pudo conectar"""


class MyEmptyError(MyAnyError):
    """Excepción porque no hay resultados"""


class MyFilenameError(MyAnyError):
    """Exception raised when the filename is None"""


class MyFileNotFoundError(MyAnyError):
    """Excepción porque no se encontró el archivo"""


class MyFileNotAllowedError(MyAnyError):
    """Excepción porque no se permite el tipo del archivo"""


class MyIsDeletedError(MyAnyError):
    """Excepción porque esta eliminado"""


class MyMissingConfigurationError(MyAnyError):
    """Exception raised when a environment variable is not configured"""


class MyNotAllowedExtensionError(MyAnyError):
    """Exception raised when the extension is not allowed"""


class MyNotExistsError(MyAnyError):
    """Excepción porque no existe"""


class MyNotValidAnswerError(MyAnyError):
    """Excepción porque la respuesta no es válida"""


class MyNotValidParamError(MyAnyError):
    """Excepción porque un parámetro es inválido"""


class MyOutOfRangeParamError(MyAnyError):
    """Excepción porque un parámetro esta fuera de rango"""


class MyRequestError(MyAnyError):
    """Excepción porque falló el request"""


class MyResponseError(MyAnyError):
    """Excepción porque falló la respuesta"""


class MyStatusCodeError(MyAnyError):
    """Excepción porque el status code no es 200"""


class MyTimeoutError(MyAnyError):
    """Excepción porque se agoto el tiempo de espera"""


class MyUnknownError(MyAnyError):
    """Excepción porque hubo un error desconocido"""


class MyUnknownExtensionError(MyAnyError):
    """Exception raised when the extension is unknown"""


class MyUploadError(MyAnyError):
    """Excepción porque falló la subida"""
