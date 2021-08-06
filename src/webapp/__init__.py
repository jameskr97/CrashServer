from flask import Flask
from .views import views

def create_app() -> Flask:
    """
    Create Flask all object with all paths, error handlers, extensions, etc. registered.
    :return: Flask app object
    """
    app = Flask("CrashServer")
    app.register_blueprint(views)
    return app
