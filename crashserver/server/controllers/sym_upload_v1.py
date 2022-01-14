"""
sym_upload_v1: An implementation of the `sym-upload-v1` protocol to upload
symbol files to the CrashServer.

This protocol is used when the `symupload` program from the breakpad repository
is invoked without any `-p` parameter, and without
"""

from flask import Blueprint, request

from crashserver.utility.decorators import (
    file_key_required,
    api_key_required,
    check_project_versioned,
)
from crashserver.utility.misc import SymbolData
from crashserver.server import db, helpers

sym_upload_v1 = Blueprint("sym-upload-v1", __name__)


@sym_upload_v1.route("", methods=["POST"])
@file_key_required("symbol_file")
@api_key_required("symbol")
@check_project_versioned()
def upload(project, version):
    """
    Upload endpoint for `sym-upload-v1` protocol.
    Received payload is a multipart/form request with all data needed to receive a symbol file
    :return:
    """
    data = SymbolData(
        os=request.form["os"].strip(),
        arch=request.form["cpu"].strip(),
        build_id=request.form["debug_identifier"].strip(),
        module_id=request.form["debug_file"].strip(),
        app_version=version,
    )

    file_content = request.files.get("symbol_file").stream.read()
    return helpers.symbol_upload(db.session, project, file_content, data)
