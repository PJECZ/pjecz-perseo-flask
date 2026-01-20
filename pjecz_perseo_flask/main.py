"""
PJECZ Perseo Flask
"""

from flask import Flask
from redis import Redis
from rq import Queue
from werkzeug.wrappers import Response

from .blueprints.autoridades.views import autoridades
from .blueprints.bancos.views import bancos
from .blueprints.beneficiarios.views import beneficiarios
from .blueprints.beneficiarios_cuentas.views import beneficiarios_cuentas
from .blueprints.beneficiarios_quincenas.views import beneficiarios_quincenas
from .blueprints.bitacoras.views import bitacoras
from .blueprints.centros_trabajos.views import centros_trabajos
from .blueprints.conceptos.views import conceptos
from .blueprints.conceptos_productos.views import conceptos_productos
from .blueprints.cuentas.views import cuentas
from .blueprints.distritos.views import distritos
from .blueprints.entradas_salidas.views import entradas_salidas
from .blueprints.modulos.views import modulos
from .blueprints.nominas.views import nominas
from .blueprints.percepciones_deducciones.views import percepciones_deducciones
from .blueprints.permisos.views import permisos
from .blueprints.personas.views import personas
from .blueprints.plazas.views import plazas
from .blueprints.productos.views import productos
from .blueprints.puestos.views import puestos
from .blueprints.quincenas.views import quincenas
from .blueprints.quincenas_productos.views import quincenas_productos
from .blueprints.roles.views import roles
from .blueprints.sistemas.views import sistemas
from .blueprints.tabuladores.views import tabuladores
from .blueprints.tareas.views import tareas
from .blueprints.timbrados.views import timbrados
from .blueprints.usuarios.models import Usuario
from .blueprints.usuarios.views import usuarios
from .blueprints.usuarios_roles.views import usuarios_roles
from .config.extensions import authentication, csrf, database, login_manager, moment
from .config.settings import Settings


# Clase para interceptar las peticiones para que en producción se inyecte el prefijo PREFIX
class PrefixMiddleware:
    def __init__(self, app, prefix=""):
        self.app = app
        self.prefix = prefix

    def __call__(self, environ, start_response):
        if environ["PATH_INFO"].startswith(self.prefix):
            environ["PATH_INFO"] = environ["PATH_INFO"][len(self.prefix) :]
            environ["SCRIPT_NAME"] = self.prefix
            return self.app(environ, start_response)
        else:
            res = Response("Not Found", status=404)
            return res(environ, start_response)


# Crear la aplicación
app = Flask(__name__, instance_relative_config=True)
app.add_url_rule("/favicon.ico", endpoint="sistemas.favicon")
app.config.from_object(Settings())

# Inicializar conexión a Redis
app.redis = Redis(host=app.config["REDIS_HOST"], port=app.config["REDIS_PORT"])
app.task_queue = Queue(name=app.config["TASK_QUEUE_NAME"], connection=app.redis)

# Registrar blueprints
app.register_blueprint(autoridades)
app.register_blueprint(bancos)
app.register_blueprint(beneficiarios)
app.register_blueprint(beneficiarios_cuentas)
app.register_blueprint(beneficiarios_quincenas)
app.register_blueprint(centros_trabajos)
app.register_blueprint(conceptos)
app.register_blueprint(conceptos_productos)
app.register_blueprint(cuentas)
app.register_blueprint(bitacoras)
app.register_blueprint(distritos)
app.register_blueprint(entradas_salidas)
app.register_blueprint(permisos)
app.register_blueprint(modulos)
app.register_blueprint(nominas)
app.register_blueprint(percepciones_deducciones)
app.register_blueprint(personas)
app.register_blueprint(plazas)
app.register_blueprint(productos)
app.register_blueprint(puestos)
app.register_blueprint(quincenas)
app.register_blueprint(quincenas_productos)
app.register_blueprint(roles)
app.register_blueprint(sistemas)
app.register_blueprint(tabuladores)
app.register_blueprint(timbrados)
app.register_blueprint(tareas)
app.register_blueprint(usuarios)
app.register_blueprint(usuarios_roles)

# Inicializar extensiones
csrf.init_app(app)
database.init_app(app)
moment.init_app(app)
login_manager.init_app(app)

# Cargar el modelo de usuario para la autenticación
authentication(Usuario)
