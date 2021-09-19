from pathlib import Path
import hashlib

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from flask import current_app

from crashserver import config
from crashserver.webapp import db


class Symbol(db.Model):
    """
    id: Generated GUID for this table
    project_id: The project which this minidump relates to
    date_created: The timestamp of when the minidump was uploaded
    file_location: The location of the minidump file, with respect to the root storage location
    """

    __tablename__ = "symbol"
    id = db.Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    project_id = db.Column(UUID(as_uuid=True), db.ForeignKey("project.id"), nullable=False)
    build_metadata_id = db.Column(UUID(as_uuid=True), db.ForeignKey("build_metadata.id"), nullable=False)
    date_created = db.Column(db.DateTime(timezone=True), server_default=func.now())
    app_version = db.Column(db.Text(), nullable=True)
    os = db.Column(db.Text(), nullable=False)
    arch = db.Column(db.Text(), nullable=False)
    file_location = db.Column(db.Text(), nullable=False)
    file_size_bytes = db.Column(db.Integer(), nullable=False)
    file_hash = db.Column(db.String(length=64), nullable=False)

    # Relationships
    project = db.relationship("Project", back_populates="symbol")
    build = db.relationship("BuildMetadata")

    def store_file(self, file_content: bytes):
        filesystem_module_id = self.build.module_id.split(".")[0]
        dir_location = Path(self.build.module_id, self.build.build_id, filesystem_module_id + ".sym")
        sym_loc = config.get_appdata_directory("symbol") / str(self.project_id) / dir_location
        sym_loc.parent.mkdir(parents=True, exist_ok=True)

        with open(sym_loc.absolute(), "wb") as f:
            f.write(file_content)

        self.file_size_bytes = len(file_content)
        self.file_location = str(dir_location)
        self.file_hash = str(hashlib.blake2s(file_content).hexdigest())
