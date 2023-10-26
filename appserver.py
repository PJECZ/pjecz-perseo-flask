"""
Arrancar el servidor de la aplicación Flask

https://stackoverflow.com/questions/51395936/how-to-get-flask-app-running-with-gunicorn
"""
from perseo.app import create_app

if __name__ == "__main__":
    # Running the server locally
    #     python3 appserver.py
    # Create the Flask object gets created via your create_app method and you are able to access the server.
    app = create_app()
    app.run()
else:
    # Run the server via Gunicorn
    #     gunicorn --bind 127.0.0.1:5000 appserver:gunicorn_app
    # You need to specify the module name and the variable name of the app for Gunicorn to access it.
    # Note that the variable should be a WSGI callable object for e.g a flask app object.
    gunicorn_app = create_app()
