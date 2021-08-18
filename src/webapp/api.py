from flask import Blueprint, request, current_app, render_template

from .models import Minidump, Annotation, Project, Symbol, CompileMetadata
import src.webapp.operations as ops
from . import db

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


@api.route('/api/symbol/upload', methods=["POST"])
@utility.url_arg_required("api_key")
@utility.file_key_required("symbol_file")
def upload_symbol():
    project_id = ops.get_project_id(request.args.get("api_key"))
    if project_id is None:
        return {"error": "Bad api key"}, 400

    # Get relevant module info from first line of file
    symbol_file = request.files.get("symbol_file")
    symbol_data = ops.get_symbol_data(symbol_file.stream.readline().decode('utf-8'))
    symbol_file.stream.seek(0)

    # Check if module_id already exists
    if ops.get_db_symbol(db.session, symbol_data):
        return {"error": "Symbol file already uploaded"}, 400

    return ops.symbol_upload(db.session, project_id, symbol_file.stream.read(), symbol_data)


@api.route('/webapi/symbols/<project_id>')
def get_symbols(project_id):
    data = db.session.query(Symbol, CompileMetadata)\
        .filter(Symbol.project_id == project_id)\
        .filter(Symbol.build_metadata_id == CompileMetadata.id)\
        .all()
    return {"html": render_template("symbols/symbol-list.html", data=data)}, 200