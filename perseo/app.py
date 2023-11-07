"""
Flask App
"""
import rq
from flask import Flask
from redis import Redis

from config.settings import Settings
from perseo.blueprints.autoridades.views import autoridades
from perseo.blueprints.bancos.views import bancos
from perseo.blueprints.bitacoras.views import bitacoras
from perseo.blueprints.centros_trabajos.views import centros_trabajos
from perseo.blueprints.conceptos.views import conceptos
from perseo.blueprints.conceptos_productos.views import conceptos_productos
from perseo.blueprints.cuentas.views import cuentas
from perseo.blueprints.distritos.views import distritos
from perseo.blueprints.entradas_salidas.views import entradas_salidas
from perseo.blueprints.modulos.views import modulos
from perseo.blueprints.nominas.views import nominas
from perseo.blueprints.nominas_reportes.views import nominas_reportes
from perseo.blueprints.percepciones_deducciones.views import percepciones_deducciones
from perseo.blueprints.permisos.views import permisos
from perseo.blueprints.personas.views import personas
from perseo.blueprints.plazas.views import plazas
from perseo.blueprints.productos.views import productos
from perseo.blueprints.quincenas.views import quincenas
from perseo.blueprints.quincenas_productos.views import quincenas_productos
from perseo.blueprints.roles.views import roles
from perseo.blueprints.sistemas.views import sistemas
from perseo.blueprints.tareas.views import tareas
from perseo.blueprints.usuarios.models import Usuario
from perseo.blueprints.usuarios.views import usuarios
from perseo.blueprints.usuarios_roles.views import usuarios_roles
from perseo.extensions import csrf, database, login_manager, moment


def create_app():
    """Crear app"""
    # Definir app
    app = Flask(__name__, instance_relative_config=True)

    # Cargar la configuración
    app.config.from_object(Settings())

    # Redis
    app.redis = Redis.from_url(app.config["REDIS_URL"])
    app.task_queue = rq.Queue(app.config["TASK_QUEUE"], connection=app.redis, default_timeout=1920)

    # Registrar blueprints
    app.register_blueprint(autoridades)
    app.register_blueprint(bancos)
    app.register_blueprint(distritos)
    app.register_blueprint(bitacoras)
    app.register_blueprint(centros_trabajos)
    app.register_blueprint(conceptos)
    app.register_blueprint(conceptos_productos)
    app.register_blueprint(cuentas)
    app.register_blueprint(entradas_salidas)
    app.register_blueprint(modulos)
    app.register_blueprint(nominas)
    app.register_blueprint(nominas_reportes)
    app.register_blueprint(percepciones_deducciones)
    app.register_blueprint(permisos)
    app.register_blueprint(personas)
    app.register_blueprint(plazas)
    app.register_blueprint(productos)
    app.register_blueprint(quincenas)
    app.register_blueprint(quincenas_productos)
    app.register_blueprint(roles)
    app.register_blueprint(sistemas)
    app.register_blueprint(tareas)
    app.register_blueprint(usuarios)
    app.register_blueprint(usuarios_roles)

    # Inicializar extensiones
    extensions(app)

    # Inicializar autenticación
    authentication(Usuario)

    # Entregar app
    return app


def extensions(app):
    """Inicializar extensiones"""
    csrf.init_app(app)
    database.init_app(app)
    login_manager.init_app(app)
    moment.init_app(app)


def authentication(user_model):
    """Inicializar Flask-Login"""
    login_manager.login_view = "usuarios.login"

    @login_manager.user_loader
    def load_user(uid):
        return user_model.query.get(uid)
