import typing
import importlib
import importlib.resources

from loguru import logger


class ModuleInterface:
    """Represents a plugin interface. A plugin has a single register function."""

    @staticmethod
    def register() -> None:
        """Register the necessary items in the storage factory."""


def import_module(name: str) -> ModuleInterface:
    """Imports a module given a name."""
    return importlib.import_module(name)  # type: ignore


def load_plugins(package: typing.Any):
    """Import all plugins in a package"""
    files = importlib.resources.contents(package)
    plugins = [f[:-3] for f in files if f.endswith(".py") and f[0] != "_"]
    for plugin in plugins:
        name = f"{package.__package__}.{plugin}"
        plugin_ref = import_module(name)
        if not hasattr(plugin_ref, "register"):
            logger.warning(f"Module {name} does not have top-level function `register()`. {name} will be ignored.")
            continue
        plugin_ref.register()
