import typing
from pathlib import Path


class StorageBackend(typing.Protocol):
    """Protocol for a class capable of managing files"""

    def init(self):
        """Initialize any necessary components for the storage module"""

    def create(self, path: Path, file_content: bytes) -> bool:
        """Store file_content at the given path. Return true for success, otherwise false"""

    def read(self, path: Path) -> typing.Optional[typing.IO]:
        """Read data from given path. Return bytes of result. May raise storage.errors.FileNotFound"""

    def delete(self, path: Path) -> bool:
        """Delete file at given path. Return bool for success"""


class StorageMeta(typing.Protocol):
    """Protocol for storing metadata about a backend"""

    @staticmethod
    def ui_name() -> str:
        """Get user-facing name of target"""

    @staticmethod
    def default_enabled() -> bool:
        """Return true if module is enabled by default, otherwise false"""

    @staticmethod
    def default_primary():
        """Return true if module is primary storage backend by default, otherwise false"""

    @staticmethod
    def default_config() -> dict:
        """Get default config options for this storage target"""

    @staticmethod
    def web_config() -> dict:
        """Retrieve parameters for web config"""

    @staticmethod
    def validate_credentials(config) -> bool:
        """Return true if given credentials are valid, otherwise false"""
