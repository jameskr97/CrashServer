from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_utils import create_database, database_exists
from pathlib import Path
import toml

db = SQLAlchemy()

def create_app() -> Flask:
    """
    Create Flask all object with all paths, error handlers, extensions, etc. registered.
    :return: Flask app object
    """
    resources_root = Path("res").absolute()
    templates = resources_root / "templates"
    static = resources_root / "static"

    app = Flask("CrashServer", static_folder=str(static), template_folder=str(templates))
    app.config.from_file(resources_root / "Config.toml", load=toml.load)

    # Import and register views
    from .views import views
    from .api import api
    app.register_blueprint(views)
    app.register_blueprint(api)

    # Create config directories
    Path(app.config["MINIDUMP_STORE"]).absolute().mkdir(parents=True, exist_ok=True)
    init_database(app)

    return app

def init_database(app):
    # Get config values
    dbu, dbp = app.config["USER"], app.config["PASS"]
    dbh, dbn = app.config["HOST"], app.config["DB_NAME"]
    db_url = f"postgresql://{dbu}:{dbp}@{dbh}:5432/{dbn}"

    # Configure app parameters
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    # Import database tables for flask to generate
    from .models import Application
    from .models import Annotation
    from .models import Minidump

    # Ensure database exists
    if not database_exists(db_url):
        create_database(db_url)
        db.create_all(app=app)  # Setup Database
        print("Database created")
