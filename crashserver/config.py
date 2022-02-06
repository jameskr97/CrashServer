from pathlib import Path

from dynaconf import Dynaconf

settings = Dynaconf(
    settings_files=["config/settings.toml"],
    environments=True,
    load_dotenv=True,
    envvar_prefix="CRASH",
)


def get_appdata_directory(path: str) -> Path:
    p = Path(settings.storage.appdata, path)
    if not p.exists():
        p.mkdir(exist_ok=True, parents=True)
    return p


def get_postgres_url():
    return f"postgresql://{settings.db.user}:{settings.db.passwd}@{settings.db.host}:{settings.db.port}/{settings.db.name}"


def get_redis_url():
    return f"redis://{settings.redis.host}:{settings.redis.port}"


def get_s3store_config():
    return {
        "aws_access_key_id": settings.s3store.access_key,
        "aws_secret_access_key": settings.s3store.secret_key,
        "endpoint_url": settings.s3store.endpoint_url,
    }
