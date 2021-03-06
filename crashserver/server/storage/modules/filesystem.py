import io
import typing
from pathlib import Path
from loguru import logger
from crashserver.server.storage import storage_factory


class DiskStorage:
    def __init__(self, config: dict):
        self.config = config
        self.config["path"] = Path(self.config.get("path"))

    def init(self) -> None:
        logger.info("[STORAGE/DISK] Initializing...")
        self.config.get("path").mkdir(parents=True, exist_ok=True)
        logger.info("[STORAGE/DISK] Initialization complete")

    def create(self, path: Path, file_contents: bytes) -> bool:
        """Store the data in file at path. Return bool for success"""
        filepath = Path(self.config.get("path"), path)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        logger.debug(f"[STORAGE/DISK] Creating file {filepath}")
        try:
            with open(filepath, "wb+") as outfile:
                outfile.write(file_contents)
            return True
        except:
            return False

    def read(self, path: Path) -> typing.Optional[typing.IO]:
        """Retrieve and return the file at path as a file-like object"""
        filepath = self.config.get("path") / path
        if not filepath.exists():
            logger.debug(f"[STORAGE/DISK] Cannot load file [{filepath}]. File does not exist.")
            return None

        logger.debug(f"[STORAGE/DISK] Reading file {filepath}")
        with open(filepath, "rb") as outfile:
            return io.BytesIO(outfile.read())

    def delete(self, path: Path) -> bool:
        """Delete the file at path. Return bool for success"""
        file = Path(self.config.get("path") / path)
        if file.exists():
            logger.info(f"[STORAGE/DISK] Deleting file {path}")
            file.unlink(missing_ok=True)
        else:
            logger.warning(f"[STORAGE/DISK] File not deleted. File does not exist. File: {path}")
        return True


class DiskStorageMeta:
    @staticmethod
    def ui_name() -> str:
        return "Filesystem"

    @staticmethod
    def default_enabled() -> bool:
        """Return true if module is enabled by default, otherwise false"""
        return True

    @staticmethod
    def default_primary():
        return True

    @staticmethod
    def default_config() -> dict:
        """Get default config options for this storage target"""
        return {"path": "/storage"}

    @staticmethod
    def web_config() -> dict:
        """Retrieve parameters for web config"""
        return {
            "options": [
                {"key": "path", "title": "Path", "default": DiskStorageMeta.default_config()["path"], "desc": "Absolute path without a trailing slash (e.g. /storage)"},
            ]
        }

    @staticmethod
    def validate_credentials(config) -> bool:
        """Return true if given credentials are valid, otherwise false"""
        return True


def register() -> None:
    storage_factory.register("filesystem", DiskStorage, DiskStorageMeta)
