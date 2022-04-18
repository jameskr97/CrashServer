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

from crashserver.server.storage.backend import StorageBackend, StorageMeta

storage_registry: dict[str, typing.Type[StorageBackend]] = {}
storage_meta: dict[str, typing.Type[StorageMeta]] = {}


def register(storage_key: str, instance: typing.Type[StorageBackend], meta: typing.Type[StorageMeta]):
    """Register a new storage target"""
    if storage_key in storage_registry:
        logger.warning(f"Storage key '{storage_key}' already exists. {instance.__name__} was not added to registry.")
    storage_registry[storage_key] = instance
    storage_meta[storage_key] = meta


def unregister(storage_key: str) -> None:
    """Unregister a storage target"""
    storage_registry.pop(storage_key, None)


def get_storage_methods() -> dict[str, StorageBackend]:
    return storage_registry


def get_metadata(key: str) -> typing.Type[StorageMeta]:
    return storage_meta.get(key, None)


def get_storage_method(key: str) -> typing.Callable[..., StorageBackend]:
    return storage_registry.get(key, None)
