from pathlib import Path
import os

from sqlalchemy_utils import create_database, database_exists
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask import Flask
import toml

db = SQLAlchemy()
login = LoginManager()

def init_web_app() -> Flask:
    app = init_app()
    init_views(app)
    init_database(app)
    init_login(app)

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
    sql_params = config_data["postgres"]
    dbu, dbp = sql_params["username"], sql_params["password"]
    dbh, dbn = sql_params["hostname"], sql_params["database"]
    db_url = f"postgresql://{dbu}:{dbp}@{dbh}:5432/{dbn}"

    # Configure app parameters
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_size": 30}
    db.init_app(app)
    return app

def init_views(app: Flask):
    from .views import views
    from .api import api
    from .symupload import sym_upload_v1, sym_upload_v2
    from .auth import auth
    app.register_blueprint(views)
    app.register_blueprint(api)
    app.register_blueprint(sym_upload_v1, url_prefix="/symupload")
    app.register_blueprint(sym_upload_v2, url_prefix="/symupload")
    app.register_blueprint(auth, url_prefix="/auth")

def init_database(app: Flask):
    # Ensure database exists
    if not database_exists(app.config["SQLALCHEMY_DATABASE_URI"]):
        create_database(app.config["SQLALCHEMY_DATABASE_URI"])
        print("Database created")

    from .models import Annotation
    from .models import Minidump
    from .models import Project

    db.create_all(app=app)  # Setup Database

def init_login(app: Flask):
    login.init_app(app)
    login.login_view = "auth.login"
    login.login_message = "You must be logged in to see this page"
    login.login_message_category = "info"