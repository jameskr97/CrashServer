from werkzeug.security import generate_password_hash, check_password_hash

from src.webapp import operations as ops

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from flask_login import UserMixin
from flask import current_app
from pathlib import Path
from . import db
import hashlib
import uuid


class User(db.Model, UserMixin):
    """
    Crash Server keeps track of user accounts ot determine who has has permission to administrate Crash Server.
    There will be zero permissions available.
        - An anonymous user can upload minidumps, view symbols, and view the crash dashboard for each application.
        - An authenticated user can access api-keys, delete symbols, and manage any application settings.
    """
    __tablename__ = "users"
    id = db.Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), default=uuid.uuid4)
    date_created = db.Column(db.DateTime(timezone=True), server_default=func.now())
    email = db.Column(db.String(254), nullable=False)
    password = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password = generate_password_hash(password, method='pbkdf2:sha512:310000')

    def check_password(self, password):
        return check_password_hash(self.password, password)


class Project(db.Model):
    """
    Crash Server is capable of storing symbols for, and decoding minidumps for multiple projects.

    id: Generated GUID for this table
    date_created: The timestamp of when the minidump was uploaded
    project_name: User-friendly interface name of the project
    api_key: An api key to be used when uploading minidumps
    """
    __tablename__ = "project"
    id = db.Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), default=uuid.uuid4)
    date_created = db.Column(db.DateTime(timezone=True), server_default=func.now())
    project_name = db.Column(db.Text(), nullable=False)
    api_key = db.Column(db.String(length=32), nullable=False)


class CompileMetadata(db.Model):
    """
    Table to story the common elements between symbols and minidump files. The `symbol_exists` row is added
    for convenience in the the decode_minidump task.

    This data is stored separately in the database in-case we receive a minidump file, but have not received
    symbol files to decode that minidump. Even if we can't decode the minidump, we still want a record that we are
    aware of the existence of a given module and build id combination.
    """
    __tablename__ = "compile_metadata"
    id = db.Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), default=uuid.uuid4)
    project_id = db.Column(UUID(as_uuid=True), db.ForeignKey('project.id'), nullable=False)
    module_id = db.Column(db.Text(), nullable=False)
    build_id = db.Column(db.Text(), nullable=False)

    # Relationships
    symbol = db.relationship('Symbol', uselist=False, back_populates='build')
    unprocessed_dumps = db.relationship("Minidump", primaryjoin="and_(Minidump.build_metadata_id==CompileMetadata.id,"
                                                                "Minidump.machine_stacktrace==None)")


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
    __tablename__ = "minidump"
    id = db.Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), default=uuid.uuid4)
    project_id = db.Column(UUID(as_uuid=True), db.ForeignKey('project.id'), nullable=False)
    build_metadata_id = db.Column(UUID(as_uuid=True), db.ForeignKey('compile_metadata.id'), nullable=True, default=None)
    date_created = db.Column(db.DateTime(timezone=True), server_default=func.now())
    filename = db.Column(db.Text(), nullable=False)
    client_guid = db.Column(UUID(as_uuid=True), nullable=True)
    raw_stacktrace = db.Column(db.Text(), nullable=True)
    machine_stacktrace = db.Column(db.Text(), nullable=True)

    # Relationships
    project = db.relationship("Project")
    build = db.relationship("CompileMetadata", back_populates='unprocessed_dumps')
    annotations = db.relationship("Annotation")

    @property
    def file_location(self):
        return str(Path("{0}/{1}".format(self.project_id, self.filename)))


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
    __tablename__ = "annotation"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    minidump_id = db.Column(UUID(as_uuid=True), db.ForeignKey('minidump.id'), nullable=False)
    key = db.Column(db.Text(), nullable=False)
    value = db.Column(db.Text(), nullable=False)

    # Relationships
    minidump = db.relationship('Minidump', back_populates='annotations')


class Symbol(db.Model):
    """
    id: Generated GUID for this table
    project_id: The project which this minidump relates to
    date_created: The timestamp of when the minidump was uploaded
    file_location: The location of the minidump file, with respect to the root storage location
    """
    __tablename__ = "symbol"
    id = db.Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), default=uuid.uuid4)
    project_id = db.Column(UUID(as_uuid=True), db.ForeignKey('project.id'), nullable=False)
    build_metadata_id = db.Column(UUID(as_uuid=True), db.ForeignKey('compile_metadata.id'), nullable=False)
    date_created = db.Column(db.DateTime(timezone=True), server_default=func.now())
    os = db.Column(db.Text(), nullable=False)
    arch = db.Column(db.Text(), nullable=False)
    file_location = db.Column(db.Text(), nullable=False)
    file_size_bytes = db.Column(db.Integer(), nullable=False)
    file_hash = db.Column(db.String(length=64), nullable=False)

    # Relationships
    project: Project = db.relationship('Project')
    build: CompileMetadata = db.relationship('CompileMetadata')

    @property
    def file_size_mb(self):
        return "{:.2f}Mb".format(self.file_size_bytes * 10e-7)

    def store_file(self, file_content: bytes):
        filesystem_module_id = self.build.module_id.split('.')[0]
        dir_location = Path(self.build.module_id, self.build.build_id, filesystem_module_id + ".sym")
        sym_loc = Path(current_app.config["cfg"]["storage"]["symbol_location"], str(self.project_id), dir_location)
        sym_loc.parent.mkdir(parents=True, exist_ok=True)

        with open(sym_loc.absolute(), 'wb') as f:
            f.write(file_content)

        self.file_size_bytes = len(file_content)
        self.file_location = str(dir_location)
        self.file_hash = str(hashlib.blake2s(file_content).hexdigest())


class SymbolUploadV2(db.Model):
    """
    Track upload_locations for the `sym-upload-v2` protocol.

    While `sym-upload-v1` is a more direct uploading protocol, `sym-upload-v2` defines
    additional endpoints to use to check the status of a symbol before/after it's been
    uploaded. Steps are explained in the header of `sym_upload_v2.py`
    """
    __tablename__ = "sym_upload_tracker"
    id = db.Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), default=uuid.uuid4)
    project_id = db.Column(UUID(as_uuid=True), db.ForeignKey('project.id'), nullable=False)
    date_created = db.Column(db.DateTime(timezone=True), server_default=func.now())
    module_id = db.Column(db.Text(), nullable=True)
    build_id = db.Column(db.Text(), nullable=True)
    arch = db.Column(db.Text(), nullable=True)
    os = db.Column(db.Text(), nullable=True)
    file_hash = db.Column(db.String(length=64))

    # Relationships
    project: Project = db.relationship("Project")

    @property
    def file_location(self):
        return Path(current_app.config["cfg"]["storage"]["sym_upload_location"], "{}.sym".format(self.id))

    @property
    def symbol_data(self):
        return ops.SymbolData(module_id=self.module_id, build_id=self.build_id, arch=self.arch, os=self.os)

    def store_file(self, file_content: bytes):
        first_line = file_content[:file_content.find('\n'.encode())].decode('utf-8')
        symbol_data = ops.SymbolData.from_module_line(first_line)
        self.build_id = symbol_data.build_id
        self.module_id = symbol_data.module_id
        self.arch = symbol_data.arch
        self.os = symbol_data.os

        self.file_location.parent.mkdir(parents=True, exist_ok=True)
        with open(self.file_location.absolute(), 'wb') as f:
            f.write(file_content)

        self.file_hash = str(hashlib.blake2s(file_content).hexdigest())

    def load_file(self) -> bytes:
        with open(self.file_location.absolute(), 'rb') as f:
            file_content = f.read()
        return file_content


