"""
Worker, para procesar tareas en segundo plano usando RQ y Redis

Ejecutar en la terminal y dejar corriendo:

    python3 worker.py

"""

from rq import worker

from pjecz_perseo_flask.main import app

if __name__ == "__main__":
    print("Worker is running and ready to process tasks...")
    try:
        with app.app_context():
            worker.Worker([app.task_queue], connection=app.redis).work()
    except KeyboardInterrupt:
        print("Worker has been stopped.")
