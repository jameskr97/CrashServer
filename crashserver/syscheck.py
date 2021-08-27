import logging

import crashserver.config as config

logger = logging.getLogger("CrashServer").getChild("SystemCheck")


def validate_all_settings():
    sys_db = valid_postgres_settings()
    if not sys_db:
        logger.fatal("Startup check failed. Terminating.")
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
        logger.fatal("Database connection failed: %s", str(ex.args[0]).strip())
        return False

    logger.info(f"Credentials verified for postgresql://{db.user}@{db.host}:{db.port}/{db.name}")
    return True
