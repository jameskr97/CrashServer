import os

from . import db
from .models import Minidump, Annotation, Project, Symbol, CompileMetadata
from pathlib import Path
from flask import Blueprint, request, current_app, render_template
from werkzeug.utils import secure_filename
import utility
import magic
import tasks

api = Blueprint("api", __name__)

@api.route('/api/minidump/upload', methods=["POST"])
@utility.url_arg_required("api-key")
@utility.file_key_required("upload_file_minidump")
def upload_minidump():
    """
    A Crashpad_handler sets this endpoint as their upload url with the "-no-upload-gzip"
    argument, and it will save and prepare the file for processing
    :return:
    """
    apikey = request.args.get("api-key")
    project = Project.query\
        .with_entities(Project.id, Project.project_name)\
        .filter_by(api_key=apikey)\
        .first()
    if project is None:
        return {"error": "Bad api key"}, 400

    # Ensure minidump file was uploaded
    minidump = request.files.get("upload_file_minidump")

    # Validate magic number
    magic_number = magic.from_buffer(minidump.stream.read(2048), mime=True)
    if magic_number != "application/x-dmp":
        return {"error": "Bad Minidump"}, 400

    # At this point, we have received a minidump validated to be the correct type.
    # Save the file, insert annotations, and insert minidump records.

    # Save the minidump
    minidump_fname = secure_filename(minidump.filename)
    minidump_file = Path(current_app.config["cfg"]["storage"]["minidump_location"]) / str(project.id) / minidump_fname
    minidump_file.parent.mkdir(parents=True, exist_ok=True)
    minidump.stream.seek(0)
    minidump.save(minidump_file.absolute())

    # Add minidump to database
    new_dump = Minidump(
        filename=minidump_fname,
        project_id=project.id,
        client_guid=request.args.get("guid", default=None))
    db.session.add(new_dump)
    db.session.flush()

    # Add annotations to database
    annotation = dict(request.values)
    annotation.pop("guid", None)  # Remove GUID value from annotations
    annotation.pop("api-key", None)
    for key, value in annotation.items():
        new_annotation = Annotation(minidump_id=new_dump.id, key=key, value=value)
        db.session.add(new_annotation)

    db.session.commit()

    tasks.decode_minidump(new_dump.id)()

    return {"status": "success"}, 200


@api.route('/api/symbol/upload/', methods=["POST"])
@utility.url_arg_required("api-key")
@utility.file_key_required("symbol-file")
def upload_symbol():
    apikey = request.args.get("api-key")
    project = Project.query\
        .with_entities(Project.id, Project.project_name)\
        .filter_by(api_key=apikey)\
        .first()
    if project is None:
        return {"error": "Bad api key"}, 400

    # Get relevant module info from first line of file
    symfile = request.files.get("symbol-file", default=None)
    metadata = symfile.stream.readline().rstrip().decode('utf-8').split(' ')
    sym_os, sym_arch = metadata[1], metadata[2]
    build_id, module_id = metadata[3], metadata[4]

    # Check if module_id already exists
    res = db.session.query(Symbol)\
        .filter(Symbol.build_metadata_id == CompileMetadata.id)\
        .filter(CompileMetadata.build_id == build_id)\
        .filter(CompileMetadata.module_id == module_id).first()
    if res:
        return {"error": "Symbol file already uploaded"}, 400

    # Determine file location on disk
    # module_id is split by 0, then we get the first component, in-case there is a period.
    # There will only be a period on windows when it ends in `.pdb` and we do not want to retain that.
    filesystem_module_id = module_id.split('.')[0]
    dir_location = Path(module_id, build_id, filesystem_module_id + ".sym")
    sym_loc = Path(current_app.config["cfg"]["storage"]["symbol_location"], str(project.id)) / dir_location
    sym_loc.parent.mkdir(parents=True, exist_ok=True)

    # Get file size
    symfile.stream.seek(0, os.SEEK_END)
    size_bytes = symfile.stream.tell()
    symfile.stream.seek(0)

    # Save to filesystem
    symfile.save(sym_loc)

    # Check if a minidump was already uploaded with the current module_id and build_id
    meta = db.session.query(CompileMetadata)\
        .filter(CompileMetadata.module_id == module_id)\
        .filter(CompileMetadata.build_id == build_id).first()

    # If we can't find the metadata for the symbol (which will usually be the case unless a minidump was uploaded before
    # the symbol file was uploaded), then create a new CompileMetadata, flush, and relate to symbol
    if meta is None:
        meta = CompileMetadata(project_id=project.id, module_id=module_id, build_id=build_id, symbol_exists=True)
        db.session.add(meta)
        db.session.flush()

    # Create new symbol entry
    new_sym = Symbol(project_id=project.id, build_metadata_id=meta.id, file_os=sym_os,
                     file_arch=sym_arch, file_size_bytes=size_bytes)
    db.session.add(new_sym)

    # Commit to Database
    db.session.commit()

    res = {
        "id": str(new_sym.id),
        "sym_os": sym_os,
        "sym_arch": sym_arch,
        "build_id": build_id,
        "module_id": module_id,
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