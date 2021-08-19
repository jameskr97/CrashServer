from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text

from src.webapp.models import Symbol, Minidump
from src.webapp import db


class BuildMetadata(db.Model):
    """
    Table to story the common elements between symbols and minidump files. The `symbol_exists` row is added
    for convenience in the the decode_minidump task.

    This data is stored separately in the database in-case we receive a minidump file, but have not received
    symbol files to decode that minidump. Even if we can't decode the minidump, we still want a record that we are
    aware of the existence of a given module and build id combination.
    """
    __tablename__ = "build_metadata"
    id = db.Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    project_id = db.Column(UUID(as_uuid=True), db.ForeignKey('project.id'), nullable=False)
    module_id = db.Column(db.Text(), nullable=False)
    build_id = db.Column(db.Text(), nullable=False)

    # Relationships
    symbol = db.relationship('Symbol', uselist=False, back_populates='build')
    unprocessed_dumps = db.relationship("Minidump", primaryjoin="and_(Minidump.build_metadata_id==BuildMetadata.id,"
                                                                "Minidump.machine_stacktrace==None)")

