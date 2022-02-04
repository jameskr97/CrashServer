"""
symbol.py: Operations which coordinate transactions between
the filesystem and the database on each api request
"""
from loguru import logger
import flask
import magic

from crashserver.server.models import Symbol, BuildMetadata, Minidump, Annotation, Project, Attachment, ProjectType
from crashserver.utility.misc import SymbolData


def symbol_upload(session, project: Project, symbol_file: bytes, symbol_data: SymbolData):
    """
    Store the symbol in the correct location, and track it in the database.

    While usually the data in `symbol_data` will be taken from `symbol_file` depending
    on the caller of this function (whether it be the sym-upload protocol, or the CrashServer
    web upload interface, the data might be from a different source.

    TODO(james): Is it worth separating this function out like this? The SymbolData struct
        will almost always be from the first line of the symbol file.

    :param session: The database session object
    :param project: The project to relate the symbol to
    :param symbol_file: The bytes to store in the file
    :param symbol_data: Metadata about the symfile param
    :return: The response to the client making this request
    """
    # Check if a minidump was already uploaded with the current module_id and build_id
    build = (
        session.query(BuildMetadata)
            .filter_by(
            project_id=project.id,
            build_id=symbol_data.build_id,
            module_id=symbol_data.module_id,
        )
            .first()
    )
    if build is None:
        # If we can't find the metadata for the symbol (which will usually be the case unless a minidump was uploaded
        # before the symbol file was uploaded), then create a new BuildMetadata, flush, and relate to symbol
        build = BuildMetadata(
            project_id=project.id,
            module_id=symbol_data.module_id,
            build_id=symbol_data.build_id,
        )
        session.add(build)

    if build.symbol:
        logger.error("Symbol {} already uploaded. Subsequent upload rejected.", symbol_data.build_id)
        return {"error": "Symbol file already uploaded"}, 203

    build.symbol = Symbol(
        project_id=project.id,
        os=symbol_data.os,
        arch=symbol_data.arch,
        app_version=symbol_data.app_version,
    )
    build.symbol.store_file(symbol_file)
    logger.info(
        "Symbols received for {project_name} [{project_id}][{project_type}{sym_version}][{os}:{arch}]".format(
            project_name=project.project_name,
            project_id=str(project.id).split("-")[0],
            project_type=str(project.project_type).split(".")[-1],
            sym_version=(":" + symbol_data.app_version if project.project_type == ProjectType.VERSIONED else ""),
            os=symbol_data.os,
            arch=symbol_data.arch,
        )
    )

    # Send all minidump id's to task processor to for decoding
    to_process = build.unprocessed_dumps
    if to_process:
        logger.info("Attempting to reprocess {} unprocessed minidump", len(to_process))
        for dump in to_process:
            dump.decode_task()
    session.commit()

    res = {
        "id": build.symbol.id,
        "os": build.symbol.os,
        "arch": build.symbol.arch,
        "build_id": build.build_id,
        "module_id": build.module_id,
        "date_created": build.symbol.date_created.isoformat(),
    }
    return res, 200


def minidump_upload(session, project_id: str, annotations: dict, minidump_file: bytes, attachments):
    # Verify file is actually a minidump based on magic number
    # Validate magic number
    magic_number = magic.from_buffer(minidump_file, mime=True)
    if magic_number != "application/x-dmp":
        logger.error("Minidump rejected from {}. File detected as {}", flask.request.remote_addr, magic_number)
        return flask.make_response({"error": "Bad Minidump"}, 400)

    # Add minidump to database
    new_dump = Minidump(project_id=project_id)
    new_dump.upload_ip = flask.request.remote_addr
    new_dump.client_guid = annotations.pop("guid", None)
    new_dump.store_minidump(minidump_file)
    session.add(new_dump)
    session.flush()

    # Store attachments
    for attach in attachments:
        new_attach = Attachment(project_id=project_id, minidump_id=new_dump.id, original_filename=attach.filename)
        new_attach.store_file(attach.stream.read())
        session.add(new_attach)

    # Store annotations
    if annotations:
        annotations.pop("api_key", None)  # Remove API key from being added as annotation
        for key, value in annotations.items():
            new_dump.annotations.append(Annotation(key=key, value=value))

    new_dump.decode_task()
    session.commit()
    logger.info(
        f"Minidump received [{new_dump.id}] for project [{project_id}] - [{flask.request.remote_addr}] - [{len(attachments)} attachments]"
    )

    return flask.make_response({"status": "success", "id": str(new_dump.id)}, 200)
