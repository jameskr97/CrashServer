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
    in the `compile_metadata` table. Thought at the time of writing this, it doesn't really matter. On mac, windows,
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
from src.webapp.models import SymbolUploadV2
from src.utility import url_arg_required
from src.webapp import operations as ops
from src.webapp import db

from flask import Blueprint, request, url_for, current_app

from pathlib import Path
import logging
import hashlib
import os


logger = logging.getLogger("CrashServer").getChild("sym-upload-v2")
sym_upload_v2 = Blueprint("sym-upload-v2", __name__)


@sym_upload_v2.route('/v1/symbols/<module_id>/<build_id>:checkStatus')
@url_arg_required('key')
def check_status(module_id, build_id):
    apikey = request.args.get("key")
    if apikey == "(null)":
        return {"error": "Bad api_key"}, 400

    proj_id = ops.get_project_id(apikey)
    if proj_id is None:
        return {"error": "Bad api_key"}, 400

    data = ops.SymbolData(module_id=module_id, build_id=build_id)
    symbol_exists = ops.get_db_symbol_exists(db.session, project_id=proj_id, symbol_data=data)

    # This will return if the row does not exist...
    if symbol_exists is None:
        return {"status": "STATUS_UNSPECIFIED"}, 200

    # ...and this will return based on symbol_exists on an existing row
    return {"status": "FOUND" if symbol_exists else "MISSING"}, 200


@sym_upload_v2.route('/v1/uploads:create', methods=["POST"])
@url_arg_required('key')
def create():
    apikey = request.args.get("key")
    if apikey == "(null)":
        return {"error": "Bad api_key"}, 400

    proj_id = ops.get_project_id(apikey)
    if proj_id is None:
        return {"error": "Bad api_key"}, 400

    symbol_ref = SymbolUploadV2(project_id=proj_id)
    db.session.add(symbol_ref)
    db.session.commit()

    res = {
        "uploadUrl": url_for("sym-upload-v2.upload_location", sym_id=symbol_ref.id, _external=True),
        "uploadKey": symbol_ref.id,
    }

    return res, 200


@sym_upload_v2.route('/upload', methods=["PUT"])
@url_arg_required('sym_id')
def upload_location():
    sym_id = request.args.get("sym_id")
    symbol_file_content = bytes(request.data)

    new_symbol_path = Path(current_app.config["cfg"]["storage"]["sym_upload_location"], "{}.sym".format(sym_id))
    new_symbol_path.parent.mkdir(parents=True, exist_ok=True)
    with open(new_symbol_path.absolute(), "wb") as f:
        f.write(symbol_file_content)

    sym = SymbolUploadV2.query.get(sym_id)
    sym.file_hash = hashlib.blake2s(symbol_file_content).hexdigest()
    db.session.commit()

    logger.info("New symbol file uploaded")
    return "", 200


@sym_upload_v2.route('/v1/uploads/<upload_key>:complete', methods=["POST"])
@url_arg_required('key')
def is_upload_complete(upload_key):
    apikey = request.args.get("key")
    if apikey == "(null)":
        return {"error": "Bad api_key"}, 400

    proj_id = ops.get_project_id(apikey)
    if proj_id is None:
        return {"error": "Bad api_key"}, 400

    logger.info("Attempting to upload new symbol file")
    if request.json["symbol_upload_type"] != "BREAKPAD":
        return {"error": "CrashServer only accepts breakpad debug symbols"}, 400

    # Get reference to the uploaded sym file
    symbol_ref = SymbolUploadV2.query.get(upload_key)

    # Load new file data
    with open(symbol_ref.file_location, "rb") as f:
        first_line = f.readline().decode('utf-8')
        symbol_data = ops.get_symbol_data(first_line)  # Get symbol data from file module line
        f.seek(0)
        uploaded_symbol_file = f.read()

    # If a version already exists, compare hashes
    existing_sym_file = ops.get_db_symbol(db.session, symbol_data)

    res = {"result": "OK"}
    update_sym = lambda: ops.symbol_upload(db.session, proj_id, uploaded_symbol_file, symbol_data)
    if existing_sym_file is None:  # No existing symbol file
        logger.info("Symbol file for {}:{} does not exist. Storing symbol..."
                    .format(symbol_data.module_id, symbol_data.build_id))
        update_sym()
    else:  # Existing symbol file. Compare hashes, update if different, notify if same.
        if existing_sym_file.file_hash == symbol_ref.file_hash:
            logger.info("Symbol file hashes match. Changing nothing.")
            res["result"] = "DUPLICATE_DATA"
        else:
            logger.info("Symbol file hashes do not match. Replacing existing symbol file...")
            update_sym()

    # Delete upload
    os.remove(symbol_ref.file_location)

    # Always delete intermediary table row. Only to track symupload v2 usages.
    db.session.delete(symbol_ref)
    db.session.commit()

    return res, 200
