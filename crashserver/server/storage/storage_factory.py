"""
Storage Factory
===============
This factory stores a registry of all classes which follow the StorageTarget protocol. Currently, the elements
must be registered manually within the `storage.py:init_targets` function. This factory is used heavily within
that function in order to separate the loading and initialization of a storage module, and the usage of any
storage module.
"""
import typing

from loguru import logger

from .storage_target import StorageTarget

storage_registry: dict[str, typing.Type[StorageTarget]] = {}


def register(storage_key: str, instance: typing.Type[StorageTarget]):
    """Register a new storage target"""
    if storage_key in storage_registry:
        logger.warning(f"Storage key '{storage_key}' already exists. {instance.__name__} was not added to registry.")
    storage_registry[storage_key] = instance


def unregister(storage_key: str) -> None:
    """Unregister a storage target"""
    storage_registry.pop(storage_key, None)


def get_storage_methods() -> dict[str, StorageTarget]:
    return storage_registry


def get_storage_method(key: str) -> typing.Callable[..., StorageTarget]:
    return storage_registry.get(key, None)
