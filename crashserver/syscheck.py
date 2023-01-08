import os
import stat

from loguru import logger
from redis import Redis

import crashserver.config as config


def validate_all_settings():
    success = all(
        [
            valid_postgres_settings(),
            valid_redis_settings(),
            validate_binary_executable_bit(),
        ]
    )
    if not success:
        logger.error("Startup check failed. Terminating.")
        exit(1)
    else:
        logger.info("Startup check complete.")


def valid_postgres_settings():
    """
    Attempt to connect to the database with the credentials from application settings.
    :return: True if successful, otherwise false.
    """
    from sqlalchemy import create_engine

    # Connect to database
    db = config.settings.db
    engine = create_engine(f"postgresql://{db.user}:{db.passwd}@{db.host}:{db.port}/{db.name}")

    try:
        # Don't do any operation, just try to make a connection to the server
        with engine.begin():
            pass
    except Exception as ex:
        logger.error("Database connection failed: {}", str(ex.args[0]).strip())
        return False

    logger.info(f"Credentials verified for postgresql://{db.user}@{db.host}:{db.port}/{db.name}")
    return True


def valid_redis_settings():
    """
    Attempt to connect to redis host with the credentials from application settings.
    :return: True if successful, otherwise false.
    """
    r = Redis.from_url(config.get_redis_url())
    try:
        return r.ping()
    except Exception:
        logger.error(f"Unable to connect to redis instance at redis://:***@{config.settings.redis.host}:{config.settings.redis.port}")
        return False


def validate_binary_executable_bit():
    exe_path = "res/bin/linux"
    exe_files = ["dump_syms", "stackwalker", "minidump_stackwalk"]
    validated = True
    for f in exe_files:
        full_path = os.path.join(exe_path, f)
        can_rx = os.access(full_path, os.R_OK | os.X_OK)

        # If we cant read/execute, attempt to add read/execute
        if not can_rx:
            try:
                st = os.stat(full_path)
                os.chmod(full_path, st.st_mode | stat.S_IEXEC)
                logger.debug(f"File {full_path} given executable bit.")
            except PermissionError:
                logger.error(f"Unable to read or write {full_path}. Unable to add executable bit. " "PermissionError: Operation not permitted")
                validated = False
    return validated
