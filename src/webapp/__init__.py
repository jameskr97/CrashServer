from flask import Flask
from .views import views
from pathlib import Path

def create_app() -> Flask:
    """
    Create Flask all object with all paths, error handlers, extensions, etc. registered.
    :return: Flask app object
    """
    resources_root = Path("res")
    templates = resources_root / "templates"
    static = resources_root / "static"

    app = Flask("CrashServer", static_folder=static, template_folder=templates)
    app.register_blueprint(views)
    return app
