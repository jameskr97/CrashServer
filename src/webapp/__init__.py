from flask import Flask
from .views import views
from pathlib import Path
import toml

def create_app() -> Flask:
    """
    Create Flask all object with all paths, error handlers, extensions, etc. registered.
    :return: Flask app object
    """
    resources_root = Path("res").absolute()
    templates = resources_root / "templates"
    static = resources_root / "static"

    app = Flask("CrashServer", static_folder=static.name, template_folder=templates.name)
    app.config.from_file(resources_root / "Config.toml", load=toml.load)
    app.register_blueprint(views)

    # Create config directories
    Path(app.config["MINIDUMP_STORE"]).absolute().mkdir(exist_ok=True)
    return app
