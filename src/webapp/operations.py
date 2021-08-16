"""
symbol.py: Operations which coordinate transactions between
the filesystem and the database on each api request
"""
from .models import Project, Symbol, CompileMetadata

from flask import current_app

from pathlib import Path
import dataclasses
import uuid
import os


@dataclasses.dataclass
class SymbolData:
    os: str
    arch: str
    build_id: str
    module_id: str


def get_project_id(api_key):
    return Project.query.with_entities(Project.id).filter_by(api_key=api_key).scalar()


def get_symbol_data(first_line: str) -> SymbolData:
    """
    Parse the `MODULE` line of a symbol file. Always the first line of the symbol file.
    Format: MODULE <os> <arch> <build_id> <module_id>
    """
    metadata = first_line.strip().split(' ')
    return SymbolData(
        os=metadata[1],
        arch=metadata[2],
        build_id=metadata[3],
        module_id=metadata[4])


def get_db_symbol(session, params: SymbolData):
    res = session.query(Symbol)\
        .filter(Symbol.build_metadata_id == CompileMetadata.id)\
        .filter(CompileMetadata.build_id == params.build_id)\
        .filter(CompileMetadata.module_id == params.module_id).first()
    return res


def get_db_compile_metadata(session, symdata: SymbolData):
    return session.query(CompileMetadata)\
            .filter(CompileMetadata.module_id == symdata.module_id)\
            .filter(CompileMetadata.build_id == symdata.build_id).first()


def store_symbol(proj_id, symdata: SymbolData, file_contents: bytes) -> int:
    """
    Takes project_id, symbol module data, and the symbol file content, and writes it to file.
    :return: File size
    """

    # Determine file location on disk
    # module_id is split by 0, then we get the first component, in-case there is a period.
    # There will only be a period on windows when it ends in `.pdb` and we do not want to retain that.
    filesystem_module_id = symdata.module_id.split('.')[0]
    dir_location = Path(symdata.module_id, symdata.build_id, filesystem_module_id + ".sym")
    sym_loc = Path(current_app.config["cfg"]["storage"]["symbol_location"], str(proj_id), dir_location)
    sym_loc.parent.mkdir(parents=True, exist_ok=True)

    with open(sym_loc.absolute(), 'wb') as f:
        f.write(file_contents)

    # Get file size on disk
    return len(file_contents)


def store_minidump(proj_id, file_contents: bytes) -> str:
    """
    Takes a project, and file data, and stores it to the proper location.
    :return: name of the stored file
    """
    filename = "minidump-%s.dmp" % str(uuid.uuid4().hex)

    minidump_file = Path(current_app.config["cfg"]["storage"]["minidump_location"])
    minidump_file = minidump_file / str(proj_id) / filename
    minidump_file.parent.mkdir(parents=True, exist_ok=True)
    with open(minidump_file.absolute(), 'wb') as f:
        f.write(file_contents)

    return filename

