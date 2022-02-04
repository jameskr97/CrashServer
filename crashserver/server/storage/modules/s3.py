import io
from pathlib import Path
import typing

from loguru import logger
import boto3


class S3CompatibleStorage:
    def __init__(self, storage_name: str, config: dict = None):
        self.storage_name = storage_name
        self.config = config
        self.bucket_name = self.config.pop("bucket_name", "crashserver")
        self.s3 = None

    def init_storage(self):
        logger.info(f"[STORAGE/{self.storage_name}] Initializing...")
        self.s3 = boto3.client("s3", **self.config)
        self.s3.head_bucket(Bucket=self.bucket_name)
        logger.info(f"[STORAGE/{self.storage_name}] Initialization complete")

    def create(self, path: Path, file_contents: bytes) -> bool:
        logger.info(f"[STORAGE/{self.storage_name}] Creating file {path}")
        self.s3.upload_fileobj(io.BytesIO(file_contents), self.bucket_name, str(path))

    def retrieve(self, path: Path) -> typing.IO:
        logger.debug(f"[STORAGE/{self.storage_name}] Reading file {path}")
        data = io.BytesIO()
        self.s3.download_fileobj(self.bucket_name, str(path), data)
        data.seek(0)
        return data

    def delete(self, path: Path) -> bool:
        self.s3.delete_object(Bucket=self.bucket_name, Key=str(path))


class S3Storage:
    def __init__(self, config: dict):
        self.store = S3CompatibleStorage("S3", config)
        self.config = config

    def init(self) -> None:
        """Initialize the storage module"""
        self.store.init_storage()

    @staticmethod
    def is_default_enabled() -> bool:
        """Return true if module is enabled by default, otherwise false"""
        return False

    @staticmethod
    def get_default_config() -> dict:
        """Get default config options for this storage target"""
        return {
            "aws_access_key_id": "",
            "aws_secret_access_key": "",
            "endpoint_url": "",
            "bucket_name": "crashserver",
        }

    def create(self, path: Path, file_contents: bytes) -> bool:
        """Store the data in file at path. Return bool for success"""
        return self.store.create(path, file_contents)

    def retrieve(self, path: Path) -> typing.IO:
        """Retrieve and return the file at path as a file-like object"""
        return self.store.retrieve(path)

    def delete(self, path: Path) -> bool:
        """Delete the file at path. Return bool for success"""
        return self.store.delete(path)
