import os

from .models import Minidump, Annotation, Project, Symbol, CompileMetadata
import src.webapp.operations as ops
from . import db

from flask import Blueprint, request, current_app, render_template
import utility
import magic
import tasks

api = Blueprint("api", __name__)


@api.route('/api/minidump/upload', methods=["POST"])
@utility.url_arg_required("api_key")
@utility.file_key_required("upload_file_minidump")
def upload_minidump():
    """
    A Crashpad_handler sets this endpoint as their upload url with the "-no-upload-gzip"
    argument, and it will save and prepare the file for processing
    :return:
    """
    project_id = ops.get_project_id(request.args.get("api_key"))
    if project_id is None:
        return {"error": "Bad api key"}, 400

    # Ensure minidump file was uploaded
    minidump = request.files.get("upload_file_minidump")

    # Validate magic number
    magic_number = magic.from_buffer(minidump.stream.read(2048), mime=True)
    if magic_number != "application/x-dmp":
        return {"error": "Bad Minidump"}, 400

    # File is acceptable. Save the minidump.
    minidump.stream.seek(0)
    filename = ops.store_minidump(project_id, minidump.stream.read())

    # Add minidump to database
    new_dump = Minidump(
        filename=filename,
        project_id=project_id,
        client_guid=request.args.get("guid", default=None))
    db.session.add(new_dump)
    db.session.flush()

    # Add annotations to database
    annotation = dict(request.values)
    annotation.pop("guid", None)  # Remove GUID value from annotations
    annotation.pop("api_key", None)
    for key, value in annotation.items():
        new_annotation = Annotation(minidump_id=new_dump.id, key=key, value=value)
        db.session.add(new_annotation)

    db.session.commit()

    tasks.decode_minidump(new_dump.id)()

    return {"status": "success"}, 200


@api.route('/api/symbol/upload/', methods=["POST"])
@utility.url_arg_required("api_key")
@utility.file_key_required("symbol-file")
def upload_symbol():
    project_id = ops.get_project_id(request.args.get("api_key"))
    if project_id is None:
        return {"error": "Bad api key"}, 400

    # Get relevant module info from first line of file
    symfile = request.files.get("symbol-file", default=None)
    symdata = ops.get_symbol_data(symfile.stream.readline().decode('utf-8'))

    # Check if module_id already exists
    if ops.get_db_symbol(db.session, symdata):
        return {"error": "Symbol file already uploaded"}, 400

    size_bytes = ops.store_symbol(project_id, symdata, symfile.stream.read())

    # Check if a minidump was already uploaded with the current module_id and build_id
    meta = ops.get_db_compile_metadata(db.session, symdata)  # Check if data exists
    process_undecoded_dumps = meta is not None
    if meta is None:
        # If we can't find the metadata for the symbol (which will usually be the case unless a minidump was uploaded
        # before the symbol file was uploaded), then create a new CompileMetadata, flush, and relate to symbol
        meta = CompileMetadata(project_id=project_id, module_id=symdata.module_id, build_id=symdata.build_id,
                               symbol_exists=True)
        db.session.add(meta)
        db.session.flush()

    # Ensure compile metadata shows we do have the symbols
    meta.symbol_exists = True

    # Create new symbol entry
    new_sym = Symbol(project_id=project_id, build_metadata_id=meta.id, os=symdata.os,
                     arch=symdata.arch, file_size_bytes=size_bytes)
    db.session.add(new_sym)

    # Commit to Database
    db.session.commit()

    if process_undecoded_dumps:
        dumps = db.session.query(Minidump.id)\
            .filter(Minidump.build_metadata_id == meta.id)\
            .filter(Minidump.machine_stacktrace == None).all()

        # Send all minidump id's to task processor to for decoding
        for dump in dumps:
            tasks.decode_minidump(dump[0])

    res = {
        "id": str(new_sym.id),
        "os": symdata.os,
        "arch": symdata.arch,
        "build_id": symdata.build_id,
        "module_id": symdata.module_id,
        "date_created": new_sym.date_created.isoformat(),
    }

    return res, 200


@api.route('/webapi/symbols/<project_id>')
def get_symbols(project_id):
    data = db.session.query(Symbol, CompileMetadata)\
        .filter(Symbol.project_id == project_id)\
        .filter(Symbol.build_metadata_id == CompileMetadata.id)\
        .all()
    return {"html": render_template("symbols/symbol-list.html", data=data)}, 200