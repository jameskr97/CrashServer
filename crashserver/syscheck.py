import stat
import os

from loguru import logger

import crashserver.config as config


def validate_all_settings():
    sys_db = valid_postgres_settings()
    is_bin_init = validate_binary_executable_bit()
    if not all([sys_db, is_bin_init]):
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
                logger.error(
                    f"Unable to read or write {full_path}. Unable to add executable bit. "
                    "PermissionError: Operation not permitted"
                )
                validated = False
    return validated
