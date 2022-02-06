from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import text

from crashserver.server import db


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
    id = db.Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    minidump_id = db.Column(UUID(as_uuid=True), db.ForeignKey("minidump.id"), nullable=False)
    key = db.Column(db.Text(), nullable=False)
    value = db.Column(db.Text(), nullable=False)

    # Relationships
    minidump = db.relationship("Minidump", back_populates="annotations")
