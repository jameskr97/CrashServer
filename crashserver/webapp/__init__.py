from pathlib import Path

import flask
from flask import Flask
from sqlalchemy_utils import create_database, database_exists

from crashserver.config import get_appdata_directory
from crashserver.config import get_postgres_url, settings
from crashserver.utility.hostinfo import HostInfo
from crashserver.webapp.extensions import babel, debug_toolbar, login, limiter, migrate, db, queue
from crashserver.webapp.models import User


def create_app():
    app = init_environment()

    register_extensions(app)
    register_blueprints(app)
    register_jinja(app)

    return app


def init_environment():
    """
    Create Flask object with correct template/static dirs, and ensure essential app directories exist.
    :return: Flask app object
    """
    # Setup config directories
    resources_root = Path("res").absolute()
    templates = resources_root / "templates"
    static = resources_root / "static"

    # Create essential directories
    [get_appdata_directory(p) for p in ["symbol", "symcache", "minidump", "sym_upload_v2"]]

    # Create app and initial parameters
    app = Flask("CrashServer", static_folder=str(static), template_folder=str(templates))
    app.config["SECRET_KEY"] = settings.flask.secret_key
    app.config["SQLALCHEMY_DATABASE_URI"] = get_postgres_url()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
    app.config["LANGUAGES"] = ['en', 'zh']

    return app


def register_extensions(app: Flask):
    babel.init_app(app)
    debug_toolbar.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db, directory="crashserver/migrations")
    limiter.init_app(app)
    login.init_app(app)

    @babel.localeselector
    def get_locale():
        return flask.request.accept_languages.best_match(app.config["LANGUAGES"])

    login.login_view = "auth.login"
    login.login_message = "You must be logged in to see this page"
    login.login_message_category = "info"


def register_blueprints(app: Flask):
    from .views import views
    from .api import api
    from .symupload import sym_upload_v1, sym_upload_v2
    from .auth import auth

    app.register_blueprint(views)
    app.register_blueprint(api)
    app.register_blueprint(sym_upload_v1, url_prefix="/symupload")
    app.register_blueprint(sym_upload_v2, url_prefix="/symupload")
    app.register_blueprint(auth, url_prefix="/auth")


def register_jinja(app: Flask):
    from crashserver.utility import sysinfo, misc
    import humanize

    app.add_template_global(sysinfo, "sysinfo")
    app.add_template_global(HostInfo, "HostInfo")
    app.add_template_global(misc.get_font_awesome_os_icon, "get_font_awesome_os_icon")
    app.add_template_global(misc.naturaltime, "humantime")
    app.add_template_global(humanize, "humanize")
    app.add_template_global(app.config, "settings")

    @app.template_filter("pluralize")
    def pluralize(number, singular="", plural="s"):
        return singular if number == 1 else plural


def init_database(app: Flask):
    """TODO: Reformat to be in manage.py"""
    # Ensure database exists
    if not database_exists(app.config["SQLALCHEMY_DATABASE_URI"]):
        create_database(app.config["SQLALCHEMY_DATABASE_URI"])
        print("Database created")

    from crashserver.webapp.models import Annotation
    from crashserver.webapp.models import BuildMetadata
    from crashserver.webapp.models import Minidump
    from crashserver.webapp.models import Project
    from crashserver.webapp.models import Symbol
    from crashserver.webapp.models import SymbolUploadV2
    from crashserver.webapp.models import User
    from crashserver.webapp.models import SymCache
