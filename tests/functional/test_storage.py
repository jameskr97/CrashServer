from pathlib import Path

import pytest
from minio import Minio


from crashserver.server import db
from crashserver.server.models import Storage


def init_s3generic_config(bucket_name):
    # Store default credentials in database
    s3 = db.session.query(Storage).filter_by(key="s3generic").first()
    s3.config = {
        "aws_access_key_id": "cs-access-key",
        "aws_secret_access_key": "cs-secret-key",
        "endpoint_url": "http://minio:9000",
        "bucket_name": bucket_name,
        "region_name": "",
    }
    db.session.commit()


def init_s3generic_client(bucket_name):
    client = Minio("minio:9000", "cs-access-key", "cs-secret-key", secure=False)

    # Create bucket if it doesn't exist
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)

    # Delete all objects
    for obj in client.list_objects(bucket_name):
        client.remove_object(bucket_name, obj.object_name)

    return client


class StorageData:
    def setup_class(self):
        class SampleFile:
            def __init__(self, filename, file_content):
                self.path = Path(filename)
                self.content = file_content
        self.file_all = SampleFile("all_platforms.txt", b"ThisIsTheSavedFileContent!\n")
        self.file_s3 = SampleFile("s3only.txt", b"ThisFileIsOnS3Only!\n")
        self.file_fs = SampleFile("fsonly.txt", b"ThisFileIsOnFilesystemOnly!\n")

    @staticmethod
    def disable_backends_except(backends: list):
        # Disable all backends except filesystem
        res = db.session.query(Storage).all()
        for r in res:
            r.is_enabled = True if r.key in backends else False

    @staticmethod
    def get_config_data(backend):
        res = db.session.query(Storage).filter_by(key=backend).first()
        return res.config


class TestFilesystem(StorageData):
    def setup_class(self):
        super().setup_class(self)
        StorageData.disable_backends_except(["filesystem"])
        self.storage_config = StorageData.get_config_data("filesystem")

        # Init storage modules
        Storage.register_targets()
        Storage.init_targets()

    def test_fileio_save(self):
        # Create file
        Storage.create(self.file_all.path, self.file_all.content)

        # Ensure file exists
        assert Path(self.storage_config.get("path"), self.file_all.path).exists()

    def test_fileio_read(self):
        # Read file
        with Storage.retrieve(self.file_all.path) as file:
            data = file.read()
        assert data == self.file_all.content

    def test_fileio_delete(self):
        Storage.delete(self.file_all.path)

        # Ensure file deleted
        assert not Path(self.storage_config.get("path"), self.file_all.path).exists()


class TestS3(StorageData):
    def setup_class(self):
        super().setup_class(self)
        self.bucket_name = "crashserver"

        StorageData.disable_backends_except(["s3generic"])
        init_s3generic_config(self.bucket_name)

        # Init storage modules
        Storage.register_targets()
        Storage.init_targets()

        # Create bucket if not existent
        self.client = init_s3generic_client(self.bucket_name)

    def test_fileio_create(self):
        Storage.create(self.file_s3.path, self.file_s3.content)  # Create file
        assert self.client.stat_object(self.bucket_name, str(self.file_s3.path))  # Ensure file exists

    def test_fileio_retrieve(self):
        data = Storage.retrieve(self.file_s3.path).read()
        assert data == self.file_s3.content

    def test_fileio_removed(self):
        Storage.delete(self.file_s3.path)

        pytest.raises(FileNotFoundError, Storage.retrieve, self.file_s3.path)


class TestMultiBackend(StorageData):
    def setup_class(self):
        super().setup_class(self)
        self.testing_backends = ["s3generic", "filesystem"]
        self.bucket_name = "crashserver"
        self.fs_config = StorageData.get_config_data("filesystem")

        StorageData.disable_backends_except(self.testing_backends)
        init_s3generic_config(self.bucket_name)

        # Init storage modules
        Storage.register_targets()
        Storage.init_targets()

        # Create bucket if not existent
        self.client = init_s3generic_client(self.bucket_name)

    def test_multi_create(self):
        # Create file
        Storage.create(self.file_all.path, self.file_all.content)
        Storage.create(self.file_fs.path, self.file_fs.content, "filesystem")
        Storage.create(self.file_s3.path, self.file_s3.content, "s3generic")

        # Ensure files exists
        assert self.client.stat_object(self.bucket_name, str(self.file_all.path))
        assert self.client.stat_object(self.bucket_name, str(self.file_s3.path))
        assert Path(self.fs_config.get("path"), self.file_all.path).exists()
        assert Path(self.fs_config.get("path"), self.file_fs.path).exists()

    def test_multi_retrieve(self):
        # Attempt reading all stored files
        f_all = Storage.retrieve(self.file_all.path).read()
        f_ffs = Storage.retrieve(self.file_fs.path).read()
        f_fs3 = Storage.retrieve(self.file_s3.path).read()

        # Ensure Content Matches
        assert f_all == self.file_all.content
        assert f_ffs == self.file_fs.content
        assert f_fs3 == self.file_s3.content

    def test_multi_retrieve_expect_fail(self):
        # Ensure files are only available where they were stored
        pytest.raises(FileNotFoundError, Storage.retrieve_from_backend, self.file_s3.path, "filesystem")
        pytest.raises(FileNotFoundError, Storage.retrieve_from_backend, self.file_fs.path, "s3generic")

    def test_multi_removed(self):
        Storage.delete(self.file_all.path)
        Storage.delete(self.file_s3.path)
        Storage.delete(self.file_fs.path)

        pytest.raises(FileNotFoundError, Storage.retrieve, self.file_all.path)
        pytest.raises(FileNotFoundError, Storage.retrieve, self.file_s3.path)
        pytest.raises(FileNotFoundError, Storage.retrieve, self.file_fs.path)
