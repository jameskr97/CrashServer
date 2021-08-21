import pathlib

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from flask import current_app

from crashserver.webapp import db
from crashserver.utility import sysinfo


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
    api_key = db.Column(db.String(length=32), nullable=False)

    # Relationships
    minidump = db.relationship('Minidump')
    symbol = db.relationship('Symbol')

    @property
    def symbol_location(self):
        return pathlib.Path(current_app.config["cfg"]["storage"]["symbol_location"], str(self.id)).absolute()

    @property
    def minidump_location(self):
        return pathlib.Path(current_app.config["cfg"]["storage"]["minidump_location"], str(self.id)).absolute()

    @property
    def total_minidump_size(self):
        """:return: Size of this projects minidump location in bytes"""
        return sysinfo.get_directory_size(self.minidump_location)

    @property
    def total_symbol_size(self):
        """:return: Size of this projects symbol location in bytes"""
        return sysinfo.get_directory_size(self.symbol_location)

