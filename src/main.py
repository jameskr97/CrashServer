import logging
import webapp

# Initialize Logging
logger = logging.getLogger("CrashServer")
logger.setLevel(logging.INFO)
log_handler = logging.StreamHandler()
log_handler.setFormatter(logging.Formatter(fmt="[%(asctime)s][%(name)s][%(levelname)s]: %(message)s", datefmt="%F %T"))
logger.addHandler(log_handler)

# Run CrashServer
if __name__ == '__main__':
    from src.webapp import app
    app.run(host="0.0.0.0", port=8081, debug=True)
