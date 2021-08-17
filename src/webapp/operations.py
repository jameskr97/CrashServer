"""
symbol.py: Operations which coordinate transactions between
the filesystem and the database on each api request
"""
from pathlib import Path
import dataclasses
import hashlib
import uuid

from .models import Project, Symbol, CompileMetadata, Minidump

from flask import current_app

from src import tasks


# %% Models
@dataclasses.dataclass
class SymbolData:
    """
    These attributes uniquely identify any symbol file. It is used over the Symbol db model as the db model is
    organized different to keep data duplication to a minimum
    """
    os: str = ""
    arch: str = ""
    build_id: str = ""
    module_id: str = ""


# %% Database Queries
def get_project_id(api_key):
    return Project.query.with_entities(Project.id).filter_by(api_key=api_key).scalar()


def get_symbol_data(first_line: str) -> SymbolData:
    """
    Parse the `MODULE` line of a symbol file. Always the first line of the symbol file.
    Format: MODULE <os> <arch> <build_id> <module_id>
    """
    metadata = first_line.strip().split(' ')
    return SymbolData(os=metadata[1], arch=metadata[2],
                      build_id=metadata[3], module_id=metadata[4])


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


def get_db_symbol_exists(session, project_id: str, symbol_data: SymbolData):
    return session.query(CompileMetadata.symbol_exists)\
                 .filter(CompileMetadata.project_id == project_id)\
                 .filter(CompileMetadata.module_id == symbol_data.module_id)\
                 .filter(CompileMetadata.build_id == symbol_data.build_id).scalar()


def get_db_unprocessed_dumps(session, compile_id: str):
    return session.query(Minidump.id)\
            .filter(Minidump.build_metadata_id == compile_id)\
            .filter(Minidump.machine_stacktrace == None).all()


# %% Database/Storage Modification
def store_symbol(proj_id, symbol_data: SymbolData, file_contents: bytes) -> str:
    """
    Takes project_id, symbol module data, and the symbol file content, and writes it to file.

    :param proj_id: Project ID to store file in
    :param symbol_data: Struct of info from module line of symbol data
    :param file_contents: Symbol file in bytes
    :return file location within project directory
    """

    # Determine file location on disk
    # module_id is split by 0, then we get the first component, in-case there is a period.
    # There will only be a period on windows when it ends in `.pdb` and we do not want to retain that.
    filesystem_module_id = symbol_data.module_id.split('.')[0]
    dir_location = Path(symbol_data.module_id, symbol_data.build_id, filesystem_module_id + ".sym")
    sym_loc = Path(current_app.config["cfg"]["storage"]["symbol_location"], str(proj_id), dir_location)
    sym_loc.parent.mkdir(parents=True, exist_ok=True)

    with open(sym_loc.absolute(), 'wb') as f:
        f.write(file_contents)

    return str(dir_location)


def symbol_upload(session, project_id: str, symbol_file: bytes, symbol_data: SymbolData):
    """
    Store the symbol in the correct location, and track it in the database.

    While usually the data in `symbol_data` will be taken from `symbol_file` depending
    on the caller of this function (whether it be the sym-upload protocol, or the CrashServer
    web upload interface, the data might be from a different source.

    TODO(james): Is it worth separating this function out like this? The SymbolData struct
        will almost always be from the first line of the symbol file.

    :param session: The database session object
    :param project_id: The project_id to relate the symbol to
    :param symbol_file: The bytes to store in the file
    :param symbol_data: Metadata about the symfile param
    :return: The response to the client making this request
    """
    # Save to file
    file_location = store_symbol(project_id, symbol_data, symbol_file)
    file_hash = str(hashlib.blake2s(symbol_file).hexdigest())

    # Check if a minidump was already uploaded with the current module_id and build_id
    meta = get_db_compile_metadata(session, symbol_data)  # Check if data exists
    process_unprocessed_dumps = meta is not None
    if meta is None:
        # If we can't find the metadata for the symbol (which will usually be the case unless a minidump was uploaded
        # before the symbol file was uploaded), then create a new CompileMetadata, flush, and relate to symbol
        meta = CompileMetadata(project_id=project_id, module_id=symbol_data.module_id,
                               build_id=symbol_data.build_id, symbol_exists=True)
        session.add(meta)
        session.flush()
    meta.symbol_exists = True  # Ensure compile metadata shows we do have the symbols

    new_sym = Symbol(project_id=project_id,
                     build_metadata_id=meta.id,
                     os=symbol_data.os,
                     arch=symbol_data.arch,
                     file_location=file_location,
                     file_hash=file_hash,
                     file_size_bytes=len(symbol_file))

    session.add(new_sym)  # Create new symbol entry
    session.commit()      # Commit to Database

    if process_unprocessed_dumps:
        dumps = get_db_unprocessed_dumps(session, meta.id)
        for dump in dumps:  # Send all minidump id's to task processor to for decoding
            tasks.decode_minidump(dump[0])

    res = {
        "id": str(new_sym.id),
        "os": symbol_data.os,
        "arch": symbol_data.arch,
        "build_id": symbol_data.build_id,
        "module_id": symbol_data.module_id,
        "date_created": new_sym.date_created.isoformat(),
    }

    return res, 200


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
