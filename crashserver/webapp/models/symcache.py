from pathlib import Path
import subprocess
import os

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text

from crashserver.utility import misc
from crashserver import config
from crashserver.webapp import db


class SymCache(db.Model):
    """
    This table is specifically for symbols which are downloaded from a remote source to this server, to facilitate
    full symbolization of minidump file. The BuildMetadata table is not used as data in this table, and the data
    referred to in this table, is ephemeral.

    id: Generated GUID for this table
    date_created: The timestamp of when the minidump was uploaded
    module_id: The module_id of the file
    build_id: The build_id of the file
    os: The operating system this symbol can decode for
    arch: The architecture of the symbol
    file_location: The location of the symbol file
    file_size_bytes: The size of the symbol file
    """

    __tablename__ = "symcache"
    id = db.Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    date_created = db.Column(db.DateTime(timezone=True), server_default=func.now())
    module_id = db.Column(db.Text(), nullable=False)
    build_id = db.Column(db.Text(), nullable=False)

    os = db.Column(db.Text(), nullable=True)
    arch = db.Column(db.Text(), nullable=True)
    file_location = db.Column(db.Text(), nullable=True)
    file_size_bytes = db.Column(db.Integer(), nullable=True)

    @property
    def url_path(self):
        return "{0}/{1}/{0}".format(self.module_id, self.build_id)

    def store_and_convert_symbol(self, file_content: bytes):
        dump_syms = str(Path("res/bin/linux/dump_syms").absolute())
        self.file_size_bytes = len(file_content)

        # Store PDB
        pdb_location = config.get_appdata_directory("symcache") / Path(self.url_path)
        pdb_location.parent.mkdir(exist_ok=True, parents=True)
        with open(pdb_location, "wb") as f:
            f.write(file_content)

        # Convert pdb to sym and store to file
        filename = self.module_id.split(".")[0] + ".sym"
        symfile = pdb_location.parent / filename
        with open(symfile, "wb") as f:
            # Write symbol data
            subprocess.run([dump_syms, pdb_location], stdout=f)

        with open(symfile, "rb") as f:
            f.seek(0)  # go to first line
            first_line = f.readline().decode("utf-8")  # read first line and decode
            data = misc.SymbolData.from_module_line(first_line)  # process
            self.os = data.os
            self.arch = data.arch
            self.file_location = "{0}/{1}/{2}".format(self.module_id, self.build_id, filename)

        # Delete original pdb
        os.remove(pdb_location.absolute())
