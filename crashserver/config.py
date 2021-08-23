from dynaconf import Dynaconf

settings = Dynaconf(
    settings_files=["config/settings.toml"],
    environments=True,
    load_dotenv=True,
    envvar_prefix="CRASH",
)
