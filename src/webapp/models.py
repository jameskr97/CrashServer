from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from flask import current_app
from pathlib import Path
from . import db
import uuid


class Project(db.Model):
    """
    Crash Server is capable of storing symbols for, and decoding minidumps for multiple projects.

    id: Generated GUID for this table
    date_created: The timestamp of when the minidump was uploaded
    project_name: User-friendly interface name of the project
    api_key: An api key to be used when uploading minidumps
    """
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date_created = db.Column(db.DateTime(timezone=True), server_default=func.now())
    project_name = db.Column(db.Text(), nullable=False)
    api_key = db.Column(db.String(length=32), nullable=False)


class Annotation(db.Model):
    """
    A crashpad_handler may be configured to upload an arbitrary number of annotations alongside
    the minidump itself. These annotations must be stored in a separate table, and related to the
    minidump which they were uploaded by.
    id: Generated GUID for this table
    minidump_id: Foreign key to minidump.id
    key: The annotation key
    value: The annotation value
    """
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    minidump_id = db.Column(UUID(as_uuid=True), db.ForeignKey('minidump.id'), nullable=False)
    key = db.Column(db.Text(), nullable=False)
    value = db.Column(db.Text(), nullable=False)


class Minidump(db.Model):
    """
    Each minidump uploaded will get a file reference. The file won't always exist on system,
    but any data to regenerate the UI view of the minidump on /crash-report endpoints

    id: Generated GUID for this table
    project_id: The project which this minidump relates to
    date_created: The timestamp of when the minidump was uploaded
    filename: The filename of the guid stored in the MINIDUMP_STORE directory
    client_guid: The guid parameter passed in from the post parameters. Optional.
    raw_stacktrace: Stacktrace decoded with `./minidump_stackwalk <dmp> <symbols>`
    machine_stacktrace: Stacktrace decoded with `./minidump_stackwalk -m <dmp> <symbols>`
    """
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = db.Column(UUID(as_uuid=True), db.ForeignKey('project.id'), nullable=False)
    build_metadata_id = db.Column(UUID(as_uuid=True), db.ForeignKey('compile_metadata.id'), nullable=True, default=None)
    date_created = db.Column(db.DateTime(timezone=True), server_default=func.now())
    filename = db.Column(db.Text(), nullable=False)
    client_guid = db.Column(UUID(as_uuid=True), nullable=True)
    raw_stacktrace = db.Column(db.Text(), nullable=True)
    machine_stacktrace = db.Column(db.Text(), nullable=True)

    @property
    def file_location(self):
        return str(Path("{0}/{1}".format(self.project_id, self.filename)))


class Symbol(db.Model):
    """
    id: Generated GUID for this table
    project_id: The project which this minidump relates to
    date_created: The timestamp of when the minidump was uploaded
    file_location: The location of the minidump file, with respect to the root storage location
    """
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = db.Column(UUID(as_uuid=True), db.ForeignKey('project.id'), nullable=False)
    build_metadata_id = db.Column(UUID(as_uuid=True), db.ForeignKey('compile_metadata.id'), nullable=False)
    date_created = db.Column(db.DateTime(timezone=True), server_default=func.now())
    os = db.Column(db.Text(), nullable=False)
    arch = db.Column(db.Text(), nullable=False)
    file_location = db.Column(db.Text(), nullable=False)
    file_size_bytes = db.Column(db.Integer(), nullable=False)
    file_hash = db.Column(db.String(length=64), nullable=False)

    @property
    def file_size_mb(self):
        return "{:.2f}Mb".format(self.file_size_bytes * 10e-7)


class CompileMetadata(db.Model):
    """
    Table to story the common elements between symbols and minidump files. The `symbol_exists` row is added
    for convenience in the the decode_minidump task.

    This data is stored separately in the database in-case we receive a minidump file, but have not received
    symbol files to decode that minidump. Even if we can't decode the minidump, we still want a record that we are
    aware of the existence of a given module and build id combination.
    """
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = db.Column(UUID(as_uuid=True), db.ForeignKey('project.id'), nullable=False)
    module_id = db.Column(db.Text(), nullable=False)
    build_id = db.Column(db.Text(), nullable=False)
    symbol_exists = db.Column(db.Boolean(), nullable=False)


class SymbolUploadV2(db.Model):
    __tablename__ = "sym_upload_tracker"
    """
    Track upload_locations for the `sym-upload-v2` protocol.

    While `sym-upload-v1` is a more direct uploading protocol, `sym-upload-v2` defines
    additional endpoints to use to check the status of a symbol before/after it's been
    uploaded. Steps are explained in the header of `sym_upload_v2.py`
    """
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = db.Column(UUID(as_uuid=True), db.ForeignKey('project.id'), nullable=False)
    date_created = db.Column(db.DateTime(timezone=True), server_default=func.now())
    file_hash = db.Column(db.String(length=64))

    @property
    def file_location(self):
        return Path(current_app.config["cfg"]["storage"]["sym_upload_location"], "{}.sym".format(self.id)).absolute()
