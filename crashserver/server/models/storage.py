from pathlib import Path
from typing import IO, Optional
from functools import cache

from loguru import logger
from sqlalchemy.dialects.postgresql import JSONB

import crashserver.server.storage.modules
from crashserver.server import db
from crashserver.server.storage import loader as storage_loader
from crashserver.server.storage import storage_factory
from crashserver.server.storage.backend import StorageBackend

STORAGE_INSTANCES: dict[str, StorageBackend] = {}
PRIMARY_STORAGE = ""


class Storage(db.Model):
    """
    Storage: Configuration data for the storage module.

    key: The filename where the module is stored under `crashserver.server.storage.modules.*`
    is_enabled: If the module is current active
    config: A json of config information for that module
    """

    __tablename__ = "storage"
    key = db.Column(db.Text(), primary_key=True)
    is_enabled = db.Column(db.Boolean(), nullable=False, default=False)
    is_primary = db.Column(db.Boolean(), nullable=False, default=False)
    config = db.Column(JSONB, nullable=True)

    @staticmethod
    def register_targets():
        # Register internal targets
        storage_loader.load_plugins(crashserver.server.storage.modules)

        # Ensure all methods exist within database
        new_modules = []
        current_targets = [key[0] for key in db.session.query(Storage.key)]

        modules = storage_factory.get_storage_methods()
        for key, storage in modules.items():
            meta = storage_factory.get_metadata(key)

            if key not in current_targets:
                # If the target does not exist, get the default config, and insert that storage target into the database
                new_modules.append(
                    Storage(
                        key=key,
                        is_enabled=meta.default_enabled(),
                        is_primary=meta.default_primary(),
                        config=meta.default_config(),
                    )
                )
            else:
                # If the target does exist, compare config dicts, and add a blank config for each any new possible config keys
                existing_module = db.session.query(Storage).get(key)
                new_cfg = meta.default_config()
                new_cfg.update(existing_module.config)
                existing_module.config = new_cfg

        # Store new modules to database and log action
        if new_modules:
            [db.session.add(module) for module in new_modules]
            db.session.commit()
            logger.info(f"[STORAGE] {len(new_modules)} new storage targets created")
        else:
            logger.info(f"[STORAGE] No new storage targets created")

        # Delete rows fow deleted modules
        for target in current_targets:
            if target not in modules:
                ref = db.session.query(Storage).get(target)
                db.session.delete(ref)
                db.session.commit()
                logger.info(f"Removed target {target} because the storage module has been deleted")

    @staticmethod
    def init_targets():
        global PRIMARY_STORAGE
        PRIMARY_STORAGE = db.session.query(Storage.key).filter_by(is_primary=True).first()[0]
        active_targets: [Storage] = db.session.query(Storage).filter_by(is_enabled=True).all()
        for target in sorted(active_targets, key=lambda x: x.key):
            STORAGE_INSTANCES[target.key] = storage_factory.get_storage_method(target.key)(target.config)
            STORAGE_INSTANCES[target.key].init()

    @property
    def meta(self):
        return storage_factory.get_metadata(self.key)

    @staticmethod
    def create(path: Path, file_contents: bytes, backend: str = None):
        if backend:
            STORAGE_INSTANCES[backend].create(path, file_contents)
            return

        # # Attempt primary backend first
        success = STORAGE_INSTANCES[PRIMARY_STORAGE].create(path, file_contents)
        if success:
            return

        success_backends = []
        for key, instance in STORAGE_INSTANCES.items():
            if instance.create(path, file_contents):
                success_backends.append(key)

        # If we reach here, saving was unsuccessful.
        logger.error(f"Failed [{PRIMARY_STORAGE}] storage of file [{path}]. Successfully stored in {success_backends}.")

    @staticmethod
    def retrieve(path: Path):
        for key, instance in STORAGE_INSTANCES.items():
            file = instance.read(path)
            if file is not None:
                return file
        raise FileNotFoundError

    @staticmethod
    def retrieve_from_backend(path: Path, key: str) -> Optional[IO]:
        file = STORAGE_INSTANCES[key].read(path)
        if file is not None:
            return file
        raise FileNotFoundError

    @staticmethod
    def delete(path: Path):
        for key, instance in STORAGE_INSTANCES.items():
            instance.delete(path)
