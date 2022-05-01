import enum
import pathlib

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text

from crashserver.server import db
from .minidump import Minidump
from .symbol import Symbol


class ProjectType(enum.Enum):
    SIMPLE = "Simple"
    VERSIONED = "Versioned"

    @staticmethod
    def get_type_from_str(ptype):
        if ptype == "simple":
            return ProjectType.SIMPLE
        if ptype == "versioned":
            return ProjectType.VERSIONED
        return None

    def __str__(self):
        return str(self.name)


class Project(db.Model):
    """
    Crash Server is capable of storing symbols for, and decoding minidumps for multiple projects.

    id: Generated GUID for this table
    date_created: The timestamp of when the minidump was uploaded
    project_name: User-friendly interface name of the project
    api_key: An api key to be used when uploading minidumps
    """

    __tablename__ = "project"
    id = db.Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    date_created = db.Column(db.DateTime(timezone=True), server_default=func.now())
    project_name = db.Column(db.Text(), nullable=False)
    project_type = db.Column(db.Enum(ProjectType), nullable=False)
    minidump_api_key = db.Column(db.String(length=32), nullable=False)
    symbol_api_key = db.Column(db.String(length=32), nullable=False)

    # Relationships
    minidump = db.relationship("Minidump", viewonly=True)
    symbol = db.relationship("Symbol")
    unprocessed_dumps = db.relationship("Minidump", primaryjoin="and_(Minidump.project_id==Project.id, Minidump.symbolicated=='false')", viewonly=True)

    @property
    def symbol_location(self):
        return pathlib.Path("symbol", str(self.id))

    @property
    def minidump_location(self):
        return pathlib.Path("minidump", str(self.id))

    @property
    def total_minidump_size(self):
        """:return: Size of this projects minidump location in bytes"""
        # TODO: Store minidump size, and properly return it
        return 0  # sysinfo.get_directory_size(self.minidump_location)

    @property
    def total_symbol_size(self):
        """:return: Size of this projects symbol location in bytes"""
        return db.session.query(func.sum(Symbol.file_size_bytes)).scalar()

    @property
    def symbol_count(self):
        return db.session.query(func.count(Symbol.id)).filter_by(project_id=self.id).scalar()

    @property
    def minidump_count(self):
        return db.session.query(func.count(Minidump.id)).filter_by(project_id=self.id).scalar()

    @property
    def unprocessed_count(self):
        return db.session.query(func.count(Minidump.id)).filter_by(symbolicated=False, project_id=self.id).scalar()
