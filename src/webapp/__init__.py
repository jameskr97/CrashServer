import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_utils import create_database, database_exists
from pathlib import Path
import toml

db = SQLAlchemy()

def init_web_app() -> Flask:
    app = init_app()
    init_views(app)
    setup_database(app)
    return app

def init_app() -> Flask:
    """
    Create Flask all object with all paths, error handlers, extensions, etc. registered.
    :return: Flask app object
    """
    # Setup config directories
    resources_root = Path("res").absolute()
    templates = resources_root / "templates"
    static = resources_root / "static"

    # Load config file
    config_file = os.environ.get("CONFIG_FILE", default=resources_root / "Config.toml")
    config_data = toml.load(config_file)

    # Create config directories
    Path(config_data["storage"]["minidump_location"]).absolute().mkdir(parents=True, exist_ok=True)
    Path(config_data["storage"]["symbol_location"]).absolute().mkdir(parents=True, exist_ok=True)

    # Create app and inital parameters
    app = Flask("CrashServer", static_folder=str(static), template_folder=str(templates))
    app.config["SECRET_KEY"] = config_data["flask"]["secret_key"]
    app.config["cfg"] = config_data

    # Prepare database
    init_database(app, config_data["postgres"])
    return app

def init_views(app: Flask) -> Flask:
    from .views import views
    from .api import api
    app.register_blueprint(views)
    app.register_blueprint(api)
    return app

def init_database(app: Flask, sql_params: dict):
    # Get config values
    dbu, dbp = sql_params["username"], sql_params["password"]
    dbh, dbn = sql_params["hostname"], sql_params["database"]
    db_url = f"postgresql://{dbu}:{dbp}@{dbh}:5432/{dbn}"

    # Configure app parameters
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_size": 30
    }
    db.init_app(app)

def setup_database(app: Flask):
    # Ensure database exists
    if not database_exists(app.config["SQLALCHEMY_DATABASE_URI"]):
        create_database(app.config["SQLALCHEMY_DATABASE_URI"])
        print("Database created")

    from .models import Annotation
    from .models import Minidump
    from .models import Project

    db.create_all(app=app)  # Setup Database
