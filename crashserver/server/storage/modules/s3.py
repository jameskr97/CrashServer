import io
import typing
from pathlib import Path

import boto3
from loguru import logger


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
            "bucket_name": "",
            "region_name": "",
        }

    @staticmethod
    def get_web_config() -> dict:
        """Retrieve parameters for web config"""
        return {
            "options": [
                {"key": "endpoint_url", "title": "Endpoint URI", "desc": "The full S3-compliant endpoint URI"},
                {"key": "bucket_name", "title": "Bucket Name", "desc": "The unique bucket name to create"},
                {"key": "aws_access_key_id", "title": "Access Key ID", "desc": "The Access Key ID"},
                {"key": "aws_secret_access_key", "title": "Secret Access Key", "desc": "The Access Key Secret for the Access Key ID"},
                {"key": "region_name", "title": "Bucket Region", "desc": "The region for the bucket"},
            ],
            "actions": [
                {"func": "upload_data", "desc": "Upload all local data to AWS S3"},
            ],
        }

    @staticmethod
    def validate_credentials(config) -> bool:
        """Return true if given credentials are valid, otherwise false"""
        logger.info(config)

        client = boto3.client(
            "s3",
            aws_access_key_id=config.get("aws_access_key_id", ""),
            aws_secret_access_key=config.get("aws_secret_access_key", ""),
            endpoint_url=config.get("endpoint_url", ""),
            region_name=config.get("region_name", ""),
        )
        try:
            res = client.head_bucket(Bucket=config.get("bucket_name", ""))
            return res
        except:
            return False

    def create(self, path: Path, file_contents: bytes) -> bool:
        """Store the data in file at path. Return bool for success"""
        return self.store.create(path, file_contents)

    def retrieve(self, path: Path) -> typing.IO:
        """Retrieve and return the file at path as a file-like object"""
        return self.store.retrieve(path)

    def delete(self, path: Path) -> bool:
        """Delete the file at path. Return bool for success"""
        return self.store.delete(path)
