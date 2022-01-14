import gzip
import io

from flask import Blueprint, request
from werkzeug.formparser import parse_form_data

import crashserver.webapp.operations as ops
from crashserver.utility.decorators import (
    file_key_required,
    api_key_required,
    check_project_versioned,
)
from crashserver.utility.misc import SymbolData
from crashserver.webapp import db

crash_upload_api = Blueprint("api", __name__)


@crash_upload_api.route("/api/minidump/upload", methods=["POST"])
@api_key_required()
def upload_minidump(project):
    """
    A Crashpad_handler sets this endpoint as their upload url with the "-no-upload-gzip"
    argument, and it will save and prepare the file for processing
    :return:
    """

    # A crashpad upload `Content Encoding` will only be gzip, or not present.
    if request.content_encoding == "gzip":
        uncompressed = gzip.decompress(request.get_data())
        environ = {
            "wsgi.input": io.BytesIO(uncompressed),
            "CONTENT_LENGTH": str(len(uncompressed)),
            "CONTENT_TYPE": request.content_type,
            "REQUEST_METHOD": "POST",
        }
        stream, form, files = parse_form_data(environ)
        dump_values = dict(form)
        attachments = files.to_dict()

    else:
        # Additional files after minidump has been popped from dict are misc attachments.
        attachments = request.files.to_dict()
        dump_values = dict(request.values)

    minidump_key = "upload_file_minidump"
    if minidump_key not in attachments.keys():
        return {"error": "missing file parameter {}".format(minidump_key)}, 400
    minidump = attachments.pop(minidump_key)

    return ops.minidump_upload(
        db.session,
        project.id,
        dump_values,
        minidump.stream.read(),
        attachments.values(),
    )


@crash_upload_api.route("/api/symbol/upload", methods=["POST"])
@file_key_required("symbol_file")
@api_key_required("symbol")
@check_project_versioned()
def upload_symbol(project, version):
    symbol_file = request.files.get("symbol_file")

    symbol_file_bytes = symbol_file.stream.read()
    with io.BytesIO(symbol_file_bytes) as f:
        first_line_str = f.readline().decode("utf-8")

    # Get relevant module info from first line of file
    symbol_data = SymbolData.from_module_line(first_line_str)
    symbol_data.app_version = version
    symbol_file.stream.seek(0)

    return ops.symbol_upload(db.session, project, symbol_file_bytes, symbol_data)
