"""
Siguiente URL segura
"""

from urllib.parse import urljoin, urlparse

from flask import request, url_for


def safe_next_url(target: str) -> str:
    """Obtener una URL segura para redirigir después del login"""
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    if test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc:
        return target
    return url_for("sistemas.start")
