from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from . import db
import uuid


class Application(db.Model):
    """
    Crash Server is capable of storing symbols for, and decoding minidumps for multiple applications.
    Each row in the applications table is the logical separation for each application
    """
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date_created = db.Column(db.DateTime(timezone=True), server_default=func.now())
    app_name = db.Column(db.Text(), nullable=False)
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
    processed: True if raw_stacktrace and machine_stacktrace have been generated.
    filename: The filename of the guid stored in the MINIDUMP_STORE directory
    client_guid: The guid parameter passed in from the post parameters. Optional.
    raw_stacktrace: Stacktrace decoded with `./minidump_stackwalk <dmp> <symbols>`
    machine_stacktrace: Stacktrace decoded with `./minidump_stackwalk -m <dmp> <symbols>`
    """
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    app_id = db.Column(UUID(as_uuid=True), db.ForeignKey('application.id'), nullable=False)
    date_created = db.Column(db.DateTime(timezone=True), server_default=func.now())
    filename = db.Column(db.Text(), nullable=False)
    client_guid = db.Column(UUID(as_uuid=True), nullable=True)
    raw_stacktrace = db.Column(db.Text(), nullable=True)
    machine_stacktrace = db.Column(db.Text(), nullable=True)
