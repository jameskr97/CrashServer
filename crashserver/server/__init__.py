from pathlib import Path

import flask
from flask import Flask, render_template
from flask_babel import _
from sqlalchemy_utils import create_database, database_exists

from crashserver.cli import register_cli
from crashserver.config import get_postgres_url, settings
from crashserver.server.core.extensions import babel, debug_toolbar, login, limiter, migrate, db, queue
from crashserver.server.models import User, Storage
from crashserver.utility.hostinfo import HostInfo


def create_app():
    app = init_environment()

    register_errors(app)
    register_extensions(app)
    register_blueprints(app)
    register_jinja(app)
    register_cli(app)

    with app.app_context():
        Storage.register_targets()
        Storage.init_targets()

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

    # Create app and initial parameters
    app = Flask("CrashServer", static_folder=str(static), template_folder=str(templates))
    app.config["SECRET_KEY"] = settings.flask.secret_key
    app.config["SQLALCHEMY_DATABASE_URI"] = get_postgres_url()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
    app.config["LANGUAGES"] = ["en", "zh"]
    app.config["BABEL_TRANSLATION_DIRECTORIES"] = str(resources_root / "translations")

    return app


def register_errors(app: Flask):
    def render_error(error):
        """Render error template."""
        error_code = getattr(error, "code", 500)
        return render_template(f"errors/{error_code}.html"), error_code

    for errcode in [404, 500]:
        app.errorhandler(errcode)(render_error)


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
    login.login_message = _("You must be logged in to see this page")
    login.login_message_category = "info"


def register_blueprints(app: Flask):
    from .controllers import (
        auth,
        crash_upload_api,
        sym_upload_v1,
        sym_upload_v2,
        webapi,
        views,
    )

    app.register_blueprint(views)
    app.register_blueprint(webapi)
    app.register_blueprint(crash_upload_api)
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
    app.add_template_global(misc.get_storage_icon, "get_storage_icon")
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

    from crashserver.server.models import Annotation
    from crashserver.server.models import BuildMetadata
    from crashserver.server.models import Minidump
    from crashserver.server.models import Project
    from crashserver.server.models import Symbol
    from crashserver.server.models import SymbolUploadV2
    from crashserver.server.models import User
    from crashserver.server.models import SymCache
