"""
Sistemas
"""
from flask import Blueprint, send_from_directory

sistemas = Blueprint("sistemas", __name__, template_folder="templates")


@sistemas.route("/")
def start():
    """Pagina Inicial"""
    return """
    <html>
    <head>
        <title>Perseo</title>
    </head>
    <body>
        <h1>Sistemas</h1>
        <p>Esta es la pagina de sistemas</p>
    </body>"""


@sistemas.route("/favicon.ico")
def favicon():
    """Favicon"""
    return send_from_directory("static/img", "favicon.ico", mimetype="image/vnd.microsoft.icon")
