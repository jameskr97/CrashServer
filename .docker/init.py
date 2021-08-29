import logging

from crashserver import syscheck

logger = logging.getLogger("CrashServer")
logger.setLevel(logging.INFO)
log_handler = logging.StreamHandler()
log_handler.setFormatter(logging.Formatter(fmt="[%(asctime)s][%(name)s][%(levelname)s]: %(message)s", datefmt="%F %T"))
logger.addHandler(log_handler)

if __name__ == "__main__":
    syscheck.validate_all_settings()
