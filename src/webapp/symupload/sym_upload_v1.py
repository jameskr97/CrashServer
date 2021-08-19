"""
sym_upload_v1: An implementation of the `sym-upload-v1` protocol to upload
symbol files to the CrashServer.

This protocol is used when the `symupload` program from the breakpad repository
is invoked without any `-p` parameter, and without
"""

from flask import Blueprint, request

from src.utility import url_arg_required, file_key_required
from src.webapp import operations as ops
from src.webapp import db


sym_upload_v1 = Blueprint("sym-upload-v1", __name__)


@sym_upload_v1.route("", methods=["POST"])
@url_arg_required('api_key')
@file_key_required('symbol_file')
def upload():
    """
    Upload endpoint for `sym-upload-v1` protocol.
    Received payload is a multipart/form request with all data needed to receive a symbol file
    :return:
    """
    proj_id = ops.get_project_id(db.session, request.args.get("api_key"))
    if not proj_id:
        return {"error": "Bad api_key"}, 400

    data = ops.SymbolData(
        os=request.form['os'].strip(),
        arch=request.form['cpu'].strip(),
        build_id=request.form['debug_identifier'].strip(),
        module_id=request.form['debug_file'].strip())

    file_content = request.files.get('symbol_file').stream.read()
    return ops.symbol_upload(db.session, proj_id, file_content, data)
