from dynaconf import Dynaconf
from pathlib import Path

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
