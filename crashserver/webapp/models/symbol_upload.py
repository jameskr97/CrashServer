import hashlib

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text

from crashserver.utility.misc import SymbolData
from crashserver.webapp import db
from crashserver import config


class SymbolUploadV2(db.Model):
    """
    Track upload_locations for the `sym-upload-v2` protocol.

    While `sym-upload-v1` is a more direct uploading protocol, `sym-upload-v2` defines
    additional endpoints to use to check the status of a symbol before/after it's been
    uploaded. Steps are explained in the header of `sym_upload_v2.py`
    """

    __tablename__ = "sym_upload_tracker"
    id = db.Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    project_id = db.Column(UUID(as_uuid=True), db.ForeignKey("project.id"), nullable=False)
    date_created = db.Column(db.DateTime(timezone=True), server_default=func.now())
    module_id = db.Column(db.Text(), nullable=True)
    build_id = db.Column(db.Text(), nullable=True)
    arch = db.Column(db.Text(), nullable=True)
    os = db.Column(db.Text(), nullable=True)
    file_hash = db.Column(db.String(length=64))

    # Relationships
    project = db.relationship("Project")

    @property
    def file_location(self):
        return config.get_appdata_directory("sym_upload_v2") / "{}.sym".format(self.id)

    @property
    def symbol_data(self):
        return SymbolData(module_id=self.module_id, build_id=self.build_id, arch=self.arch, os=self.os)

    def store_file(self, file_content: bytes):
        # Ensure very first line starts with word "MODULE"
        file_content = file_content[file_content.find("MODULE".encode()) :]

        first_line = file_content[: file_content.find("\n".encode())].decode("utf-8")
        symbol_data = SymbolData.from_module_line(first_line)
        self.build_id = symbol_data.build_id
        self.module_id = symbol_data.module_id
        self.arch = symbol_data.arch
        self.os = symbol_data.os

        self.file_location.parent.mkdir(parents=True, exist_ok=True)
        with open(self.file_location.absolute(), "wb") as f:
            f.write(file_content)

        self.file_hash = str(hashlib.blake2s(file_content).hexdigest())

    def load_file(self) -> bytes:
        with open(self.file_location.absolute(), "rb") as f:
            file_content = f.read()
        return file_content
