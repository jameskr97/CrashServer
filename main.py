import logging
import os

# Initialize Logging
logger = logging.getLogger("CrashServer")
logger.setLevel(logging.INFO)
log_handler = logging.StreamHandler()
log_handler.setFormatter(logging.Formatter(fmt="[%(asctime)s][%(name)s][%(levelname)s]: %(message)s", datefmt="%F %T"))
logger.addHandler(log_handler)

if __name__ == '__main__':
    # Set working directory to the directory of this file (project root)
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    from crashserver.config import settings
    from crashserver.webapp import app

    app.run(host="0.0.0.0", port=settings.flask.web_port, debug=True)
