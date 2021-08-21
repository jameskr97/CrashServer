"""
Implementation of the `sym-upload-v2` protocol.
The protocol defines three endpoints which are called in a specific order.
Notes:
    - Breakpads documentation was very limited, and this is my understanding of the v2 protocol
    - /v1/ is not documented in the crashpad repository, and is unrelated to
`sym-upload-v2` protocol. It's only defining that it's version 1 of the `sym-upload-v2`
protocol.
    - Every defined endpoint requires the `key` argument

v2 protocol calls the following functions:
1. /v1/symbols/<debug_file>/<debug_id>:checkStatus?key=<key>
    First, symupload wants to check if the symbol exists on the server.
    This endpoint is called with an empty body, and expects a json response.
    The response will look like:
        { "status": "<result>" }
    Where <result> must be one of three values: ["STATUS_UNSPECIFIED", "MISSING", "FOUND"]
        - "FOUND"               - The symbol exists on the server
        - "MISSING"             - The symbol does not exist on the server
        - "STATUS_UNSPECIFIED"  - The server doesn't not explicitly state the existence or nonexistence of the symbol

    My interpretation of "STATUS_UNSPECIFIED" comes down to if there is not a row matching `debug_file` and `debug_id`
    in the `build_metadata` table. Thought at the time of writing this, it doesn't really matter. On mac, windows,
    and linux, in the source for symupload, it basically checks (res["status"] == "FOUND") ? "FOUND" : "MISSING".
    Nothing happens for "STATUS_UNSPECIFIED". Breakpad, why?

2. /v1/uploads:create?key=<key>
    After the first endpoint, if symupload decides that it wants to upload the symbol, it will call this endpoint.
    This endpoint is called with an empty body, and expects a json response.
    The response will look like:
        { "uploadUrl": "<url>", "uploadKey": "<key>" }
    Note the camel-case. `sym-upload-v2` docs shows underscores, while camel-case is used in the source. Breakpad, why?

    - <url>: This must be an endpoint where symupload may PUT the symbol file. When symupload PUT's to this url, the key
    will not be included. You are expected to send a url which it can use to upload the symbol file to an intermediary
    location. This is not meant to be a url which is used to directly add the symbol to the project. That is what
    happens in step three. Here, we only tell symupload where to upload the file, and we then evaluate and determine
    what to do with the symbol on the third url.

3. /uploads/<upload_key>:complete?key=<key>
    After the symbol is uploaded, this endpoint is called asking is to "process" the symbol file.
    This endpoint is called with an 3-parameter body, and expects a json response.
    The body will look like:
        { "symbol_id": { "debug_file": "<module_id>", "debug_id": "<build_id>" }, "symbol_upload_type": "BREAKPAD" }
    For the above values:
        - debug_file: The module_id of the previously submitted symbol file
        - debug_id:   The build_id of the previously submitted symbol file
        - symbol_upload_type: The type of symbol (since symupload can upload more than one).
                              CrashServer only accepts the BREAKPAD symbol type

    The response will look like:
        { "result": "<result>" }
    Where <result> must be one of three values: ["RESULT_UNSPECIFIED", "OK", "DUPLICATE_DATA"]
        - "OK"                  - The symbol storage was updated with the previously uploaded symbol
        - "DUPLICATE_DATA"      - The symbol is identical to the previously upload symbol. No change to symbol storage.
                                  Breakpad docs
        - "RESULT_UNSPECIFIED"  - I have no idea what this value is, or when to use this value. It's not referenced in
                                  the symupload, and is equivalent to "OK" when sent.
"""
import logging
import os

from flask import Blueprint, request, url_for

from crashserver.webapp.models import SymbolUploadV2, BuildMetadata
from crashserver.utility.decorators import url_arg_required, api_key_required
from crashserver.webapp import operations as ops
from crashserver.webapp import db

logger = logging.getLogger("CrashServer").getChild("sym-upload-v2")
sym_upload_v2 = Blueprint("sym-upload-v2", __name__)


@sym_upload_v2.route('/v1/symbols/<module_id>/<build_id>:checkStatus')
@api_key_required("key", pass_project=False)
def check_status(module_id, build_id):
    build = db.session.query(BuildMetadata).filter_by(
        build_id=module_id.strip(),
        module_id=build_id.strip()).first()

    # # This will return if the row does not exist...
    if build is None:
        return {"status": "STATUS_UNSPECIFIED"}, 200

    # ...and this will return based on symbol_exists on an existing row
    return {"status": "FOUND" if build.symbol else "MISSING"}, 200


@sym_upload_v2.route('/v1/uploads:create', methods=["POST"])
@api_key_required("key")
def create(project):
    symbol_ref = SymbolUploadV2(project_id=project.id)
    db.session.add(symbol_ref)
    db.session.commit()

    res = {
        "uploadUrl": url_for("sym-upload-v2.upload_location", sym_id=symbol_ref.id, _external=True),
        "uploadKey": symbol_ref.id
    }

    return res, 200


@sym_upload_v2.route('/upload', methods=["PUT"])
@url_arg_required('sym_id')
def upload_location():
    new_symbol = db.session.query(SymbolUploadV2).get(request.args.get("sym_id"))
    new_symbol.store_file(request.data)
    db.session.commit()
    return "", 200


@sym_upload_v2.route('/v1/uploads/<upload_key>:complete', methods=["POST"])
@api_key_required("key")
def is_upload_complete(project, upload_key):
    logger.info("Attempting to upload new symbol file")
    if request.json["symbol_upload_type"] != "BREAKPAD":
        return {"error": "CrashServer only accepts breakpad debug symbols"}, 400

    # Get reference to the uploaded sym file
    symbol_ref = db.session.query(SymbolUploadV2).get(upload_key)

    # If a version already exists, compare hashes
    build = db.session.query(BuildMetadata).filter_by(
        build_id=symbol_ref.build_id,
        module_id=symbol_ref.module_id).first()

    # If symbol exists, and hashes match, then do nothing.
    if build and build.symbol and build.symbol.file_hash == symbol_ref.file_hash:
        return {"result": "DUPLICATE_DATA"}, 200

    # Save the file!
    file_data = symbol_ref.load_file()
    ops.symbol_upload(db.session, project.id, file_data, symbol_ref.symbol_data)

    # Delete upload
    os.remove(symbol_ref.file_location)

    # Always delete intermediary table row. Only to track symupload v2 usages.
    db.session.delete(symbol_ref)
    db.session.commit()

    return {"result": "OK"}, 200
