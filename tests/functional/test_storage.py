from pathlib import Path

from minio import Minio
from minio.error import S3Error

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
        self.filename = Path("filename.txt")
        self.file_content = b"ThisIsTheSavedFileContent!"

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
        Storage.create(self.filename, self.file_content)

        # Ensure file exists
        assert Path(self.storage_config.get("path"), self.filename).exists()

    def test_fileio_read(self):
        # Read file
        with Storage.retrieve(self.filename) as file:
            data = file.read()
        assert data == self.file_content

    def test_fileio_delete(self):
        Storage.delete(self.filename)

        # Ensure file deleted
        assert not Path(self.storage_config.get("path"), self.filename).exists()


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
        # Create file
        Storage.create(self.filename, self.file_content)

        # Ensure file exists
        assert self.client.stat_object(self.bucket_name, str(self.filename))

    def test_fileio_retrieve(self):
        # Read file
        with Storage.retrieve(self.filename) as file:
            data = file.read()
        assert data == self.file_content

    def test_fileio_removed(self):
        Storage.delete(self.filename)

        try:
            self.client.stat_object(self.bucket_name, str(self.filename))
            assert False, "The file was successfully found, when it should not have been."
        except S3Error:
            assert True, "We reached an S3Error, meaning we could not find the file. (Test desired outcome)"


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
        Storage.create(self.filename, self.file_content)

        # Ensure file exists
        assert self.client.stat_object(self.bucket_name, str(self.filename))
        assert Path(self.fs_config.get("path"), self.filename).exists()

    def test_fileio_retrieve(self):
        # Read file
        for backend in self.testing_backends:
            with Storage.retrieve(self.filename, backend) as file:
                data = file.read()
                assert data == self.file_content

    def test_fileio_removed(self):
        Storage.delete(self.filename)

        assert not Path(self.fs_config.get("path"), self.filename).exists()

        try:
            self.client.stat_object(self.bucket_name, str(self.filename))
            assert False, "The file was successfully found, when it should not have been."
        except S3Error:
            assert True, "We reached an S3Error, meaning we could not find the file. (Test desired outcome)"
