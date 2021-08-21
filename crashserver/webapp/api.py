from flask import Blueprint, request, render_template
import magic

from crashserver.utility.decorators import file_key_required, api_key_required
from crashserver.webapp.models import Minidump, Annotation, Symbol
import crashserver.webapp.operations as ops
import crashserver.tasks as tasks
from crashserver.webapp import db

api = Blueprint("api", __name__)


@api.route('/api/minidump/upload', methods=["POST"])
@file_key_required("upload_file_minidump")
@api_key_required()
def upload_minidump(project_id):
    """
    A Crashpad_handler sets this endpoint as their upload url with the "-no-upload-gzip"
    argument, and it will save and prepare the file for processing
    :return:
    """
    minidump = request.files.get("upload_file_minidump")

    # Validate magic number
    magic_number = magic.from_buffer(minidump.stream.read(2048), mime=True)
    if magic_number != "application/x-dmp":
        return {"error": "Bad Minidump"}, 400
    minidump.stream.seek(0)

    # Add minidump to database
    new_dump = Minidump(project_id=project_id, client_guid=request.args.get("guid", default=None))
    new_dump.store_minidump(minidump.stream.read())
    db.session.add(new_dump)
    db.session.flush()

    # Add annotations to database
    annotation = dict(request.values)
    annotation.pop("guid", None)  # Remove GUID value from annotations
    annotation.pop("api_key", None)
    for key, value in annotation.items():
        new_dump.annotations.append(Annotation(key=key, value=value))

    db.session.commit()
    tasks.decode_minidump(new_dump.id)()
    return {"status": "success"}, 200


@api.route('/api/symbol/upload', methods=["POST"])
@file_key_required("symbol_file")
@api_key_required()
def upload_symbol(project_id):
    # Get relevant module info from first line of file
    symbol_file = request.files.get("symbol_file")
    symbol_data = ops.SymbolData.from_module_line(symbol_file.stream.readline().decode('utf-8'))
    symbol_file.stream.seek(0)

    return ops.symbol_upload(db.session, project_id, symbol_file.stream.read(), symbol_data)


@api.route('/webapi/symbols/<project_id>')
def get_symbols(project_id):
    data = db.session.query(Symbol).filter_by(project_id=project_id).all()
    return {"html": render_template("symbols/symbol-list.html", data=data)}, 200
