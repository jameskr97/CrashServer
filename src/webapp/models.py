from sqlalchemy.dialects.postgresql import UUID
from . import db
import uuid

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
    processed = db.Column(db.Boolean(), default=False)
    filename = db.Column(db.Text(), nullable=False)
    client_guid = db.Column(UUID(as_uuid=True), nullable=True)
    raw_stacktrace = db.Column(db.Text(), nullable=True)
    machine_stacktrace = db.Column(db.Text(), nullable=True)
