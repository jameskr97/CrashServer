from pathlib import Path
import uuid

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
import magic

from crashserver import config
from crashserver.webapp import db


class Attachment(db.Model):
    """
    id: Generated GUID for this table
    project_id: The project which this attachment relates to
    minidump_id: The minidump which this attachment was uploaded with
    date_created: The timestamp of when the attachment was uploaded
    filename: The name of the attachment on disk
    mime_type: The uploaded file mime_type
    file_size_bytes: The size of the file
    """

    __tablename__ = "attachments"
    id = db.Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    project_id = db.Column(UUID(as_uuid=True), db.ForeignKey("project.id"), nullable=False)
    minidump_id = db.Column(UUID(as_uuid=True), db.ForeignKey("minidump.id"), nullable=False)
    date_created = db.Column(db.DateTime(timezone=True), server_default=func.now())
    filename = db.Column(db.Text(), nullable=False)
    mime_type = db.Column(db.Text(), nullable=False)
    file_size_bytes = db.Column(db.Integer(), nullable=False)

    # Relationships
    project = db.relationship("Project")
    minidump = db.relationship("Minidump", back_populates="attachments")

    def store_file(self, file_content: bytes):

        # Determine storage location
        dump_id_part = str(self.minidump_id).split("-")[0]
        filename = "attachment-%s-%s" % (dump_id_part, str(uuid.uuid4().hex)[:8])
        attach_loc = config.get_appdata_directory("attachments") / str(self.project_id) / filename
        attach_loc.parent.mkdir(parents=True, exist_ok=True)

        # Determine mime-type
        self.mime_type = magic.from_buffer(file_content, mime=True)

        # Store file
        with open(attach_loc.absolute(), "wb") as f:
            f.write(file_content)

        self.filename = str(filename)
        self.file_size_bytes = len(file_content)

    def delete_file(self):
        location = Path(config.get_appdata_directory("attachments") / str(self.project_id) / self.filename)
        location.unlink(missing_ok=True)
