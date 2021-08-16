"""
sym_upload_v1: An implementation of the `sym-upload-v1` protocol to upload
symbol files to the CrashServer.

This protocol is used when the `symupload` program from the breakpad repository
is invoked without any `-p` parameter, and without
"""

from flask import Blueprint, request, url_for

from src.utility import url_arg_required, file_key_required
from src.webapp import operations as ops
from src.webapp import db


sym_upload_v1 = Blueprint("sym-upload-v1", __name__)


@sym_upload_v1.route("", methods=["POST"])
@url_arg_required('api_key')
@file_key_required('symbol_file')
def upload():
    key = request.args.get("api_key")

    proj_id = ops.get_project_id(key)
    if not proj_id:
        return {"error": "Bad api_key"}, 400

    data = ops.SymbolData(
        os=request.form['os'],
        arch=request.form['cpu'],
        build_id=request.form['debug_identifier'],
        module_id=request.form['debug_file'])

    file_content = request.files.get('symbol_file').stream.read()

    return ops.symbol_upload(db.session, proj_id, file_content, data)

