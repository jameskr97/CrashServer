from . import db
from .models import Minidump
from pathlib import Path
from flask import Blueprint, render_template, request, current_app
from werkzeug.utils import secure_filename
import magic

views = Blueprint("views", __name__)


@views.route('/')
def home():
    return render_template("home.html")


@views.route('/crash-reports')
def crash():
    return render_template("crash.html")


@views.route('/symbols')
def symbols():
    return render_template("symbols.html")


@views.route('/upload')
def upload():
    return render_template("upload.html")


@views.route('/api/upload', methods=["POST"])
def upload_api():
    """
    A crashpad_handler sets this endpoint as their upload url with the "-no-upload-gzip"
    argument, and it will save and prepare the file for processing
    :return:
    """
    # Error out if encoding is gzip. TODO(james): Handle gzip
    if request.content_encoding == "gzip":
        return {"error": "Cannot accept gzip"}, 400

    # Ensure required annotations have been uploaded
    annotations = dict(request.values)
    if not all([x in annotations.keys() for x in ["version", "git_hash"]]):
        return {"error": "Parameters are missing"}, 400

    # Ensure minidump file was uploaded
    if "upload_file_minidump" not in request.files.keys():
        return {"error": "Missing minidump"}, 400
    minidump = request.files["upload_file_minidump"]
    minidump_fname = secure_filename(minidump.filename)

    # Validate magic number
    magic_number = magic.from_buffer(minidump.stream.read(2048), mime=True)
    if magic_number != "application/x-dmp":
        return {"error": "Bad Minidump"}, 400

    metadata = {
        "game_version": annotations["version"],
        "git_hash": annotations["git_hash"],
    }

    # Save the minidump
    minidump_file = Path(current_app.config["MINIDUMP_STORE"]) / minidump_fname
    minidump.save(minidump_file.absolute())

    # Add entry to database
    new_dump = Minidump()
    new_dump.filename = minidump_fname
    new_dump.client_guid = annotations["guid"] if annotations["guid"] else None
    db.session.add(new_dump)
    db.session.commit()

    return "Received", 200
