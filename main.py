"""
Run Flask app
"""
from perseo import app

app = app.create_app()


if __name__ == "__main__":
    app.run()
