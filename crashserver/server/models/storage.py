from pathlib import Path
from typing import IO, Optional

from loguru import logger
from sqlalchemy.dialects.postgresql import JSONB

import crashserver.server.storage.modules as storage_targets
from crashserver.server import db
from crashserver.server.storage import storage_factory

STORAGE_INSTANCES: dict[str, storage_factory.StorageTarget] = {}


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
    config = db.Column(JSONB, nullable=True)

    @staticmethod
    def register_targets():
        # Register internal targets
        storage_factory.register("filesystem", storage_targets.DiskStorage)
        storage_factory.register("s3", storage_targets.S3Storage)
        storage_factory.register("s3generic", storage_targets.S3GenericStorage)

        # Ensure all methods exist within database
        new_modules = []
        current_targets = [key[0] for key in db.session.query(Storage.key)]
        modules = storage_factory.get_storage_methods()
        for key, storage in modules.items():
            if key not in current_targets:
                # If the target does not exist, get the default config, and insert that storage target into the database
                new_modules.append(Storage(key=key, is_enabled=storage.is_default_enabled(), config=storage.get_default_config()))
            else:
                # If the target does exist, compare config dicts, and add a blank config for each any new possible config keys
                existing_module = db.session.query(Storage).get(key)
                new_cfg = storage.get_default_config()
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
        active_targets: [Storage] = db.session.query(Storage).filter_by(is_enabled=True).all()
        for target in active_targets:
            STORAGE_INSTANCES[target.key] = storage_factory.get_storage_method(target.key)(target.config)
            STORAGE_INSTANCES[target.key].init()

    def get_user_friendly_name(self) -> str:
        """Get user-facing name of target"""
        return storage_factory.get_storage_method(self.key).get_user_friendly_name()

    def get_web_config(self):
        return storage_factory.get_storage_method(self.key).get_web_config()

    def validate_credentials(self, config) -> bool:
        """Return true if given credentials are valid, otherwise false"""
        return storage_factory.get_storage_method(self.key).validate_credentials(config)

    @staticmethod
    def create(path: Path, file_contents: bytes):
        for key, instance in STORAGE_INSTANCES.items():
            instance.create(path, file_contents)

    @staticmethod
    def retrieve(path: Path) -> Optional[IO]:
        for key, instance in STORAGE_INSTANCES.items():
            file = instance.retrieve(path)
            if file is not None:
                return file
        return None

    @staticmethod
    def delete(path: Path):
        for key, instance in STORAGE_INSTANCES.items():
            instance.delete(path)
