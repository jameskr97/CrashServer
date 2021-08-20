from pathlib import Path
import uuid

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from flask import current_app

from src.webapp import db


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
    id = db.Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    project_id = db.Column(UUID(as_uuid=True), db.ForeignKey('project.id'), nullable=False)
    build_metadata_id = db.Column(UUID(as_uuid=True), db.ForeignKey('build_metadata.id'), nullable=True, default=None)
    date_created = db.Column(db.DateTime(timezone=True), server_default=func.now())
    filename = db.Column(db.Text(), nullable=False)
    client_guid = db.Column(UUID(as_uuid=True), nullable=True)
    raw_stacktrace = db.Column(db.Text(), nullable=True)
    machine_stacktrace = db.Column(db.Text(), nullable=True)

    # Relationships
    project = db.relationship("Project")
    build = db.relationship("BuildMetadata", back_populates='unprocessed_dumps')
    annotations = db.relationship("Annotation")

    @property
    def file_location(self):
        return str(Path("{0}/{1}".format(self.project_id, self.filename)))

    def store_minidump(self, file_contents: bytes):
        filename = "minidump-%s.dmp" % str(uuid.uuid4().hex)

        dump_file = Path(current_app.config["cfg"]["storage"]["minidump_location"]) / str(self.project_id) / filename
        dump_file.parent.mkdir(parents=True, exist_ok=True)
        with open(dump_file.absolute(), 'wb') as f:
            f.write(file_contents)

        self.filename = filename

