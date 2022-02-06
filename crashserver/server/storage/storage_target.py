import typing
from pathlib import Path


class StorageTarget(typing.Protocol):
    """Protocol for a class capable of managing files"""

    def init(self) -> None:
        """Initialize the storage module"""
        pass

    @staticmethod
    def is_default_enabled() -> bool:
        """Return true if module is enabled by default, otherwise false"""
        pass

    @staticmethod
    def get_default_config() -> dict:
        """Get default config options for this storage target"""
        pass

    @staticmethod
    def get_web_config() -> dict:
        """Retrieve parameters for web config"""
        pass

    @staticmethod
    def validate_credentials(config) -> bool:
        """Return true if given credentials are valid, otherwise false"""
        pass

    def create(self, path: Path, file_contents: bytes) -> bool:
        """Store the data in file at path. Return bool for success"""
        pass

    def retrieve(self, path: Path) -> typing.IO:
        """Retrieve and return the file at path as a file-like object"""
        pass

    def delete(self, path: Path) -> bool:
        """Delete the file at path. Return bool for success"""
        pass
