"""
CrashServer

Logging Setup from: https://pawamoy.github.io/posts/unify-logging-for-a-gunicorn-uvicorn-app/
"""
# fmt: off
import flask_migrate
from gevent import monkey

monkey.patch_all()
# fmt: on

import importlib.metadata as meta
import logging
import sys
import os

from werkzeug.middleware.proxy_fix import ProxyFix
from gunicorn.app.base import BaseApplication
from gunicorn.glogging import Logger
from loguru import logger

from crashserver.server.models import Storage
from crashserver.server import create_app
from crashserver.config import settings
from crashserver import syscheck

LOG_LEVEL = logging.getLevelName(os.environ.get("LOG_LEVEL", "INFO"))
JSON_LOGS = True if os.environ.get("JSON_LOGS", "0") == "1" else False
WORKERS = int(os.environ.get("GUNICORN_WORKERS", "5"))


class InterceptHandler(logging.Handler):
    """
    This InterceptHandler is given via loguru's documentation, and lets us intercept standard logging messages to be
    forwarded to loguru

    https://github.com/Delgan/loguru#entirely-compatible-with-standard-logging
    """

    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


class StubbedGunicornLogger(Logger):
    """
    This logger lets us override gunicorns logging configuration to be formatted how we choose
    """

    def setup(self, cfg):
        handler = logging.NullHandler()
        self.error_logger = logging.getLogger("gunicorn.error")
        self.error_logger.addHandler(handler)
        self.access_logger = logging.getLogger("gunicorn.access")
        self.access_logger.addHandler(handler)
        self.error_logger.setLevel(LOG_LEVEL)
        self.access_logger.setLevel(LOG_LEVEL)


class StandaloneApplication(BaseApplication):
    """Our Gunicorn application."""

    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        config = {key: value for key, value in self.options.items() if key in self.cfg.settings and value is not None}
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application


if __name__ == "__main__":
    # Change to directory of this file
    os.chdir(os.path.abspath(os.path.dirname(__file__)))

    # Intercept and initialize loggers
    logger.remove()  # Remove default logger
    intercept_handler = InterceptHandler()
    logging.root.setLevel(LOG_LEVEL)
    logger.configure(handlers=[{"sink": sys.stdout, "serialize": JSON_LOGS}])
    seen = set()
    for name in [*logging.root.manager.loggerDict.keys(), "gunicorn", "gunicorn.access", "gunicorn.error", "werkzeug"]:
        if name not in seen:
            seen.add(name.split(".")[0])
            logging.getLogger(name).handlers = [intercept_handler]

    # fmt: off
    LOG_FORMAT = "<green>[{time:YYYY-MM-DD HH:mm:ss}]</green><lvl>[{level}]</lvl>: <bold>{message}</bold>"
    filter_app = lambda record: any(part in record["name"] for part in ["crashserver", "__main__"])
    filter_access = lambda record: record["name"] == "gunicorn.glogging" and record["function"] == "access"
    # fmt: on

    config = {
        "handlers": [
            {"sink": sys.stdout, "format": LOG_FORMAT, "colorize": True, "level": LOG_LEVEL},
            {"sink": os.path.join(settings.storage.logs, "app.log"), "filter": filter_app, "format": LOG_FORMAT},
            {"sink": os.path.join(settings.storage.logs, "access.log"), "filter": filter_access, "format": "{message}"},
        ],
    }
    logger.configure(**config)

    syscheck.validate_all_settings()  # Ensure application has a sane environment

    app = create_app()
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # Activate proxy pass detection to get real ip

    with app.app_context():
        flask_migrate.upgrade()
        Storage.register_targets()
        Storage.init_targets()

    if os.environ.get("FLASK_DEBUG"):
        app.run(host="0.0.0.0", port=settings.flask.web_port, debug=True)
        exit(0)
    else:
        logger.info("Starting CrashServer v{}", meta.version("crashserver"))

    # Configure and run gunicorn
    options = {
        "bind": f"0.0.0.0:{settings.flask.web_port}",
        "workers": WORKERS,
        "accesslog": "-",
        "errorlog": "-",
        "logger_class": StubbedGunicornLogger,
        "worker_class": "gevent",
    }
    StandaloneApplication(create_app(), options).run()
