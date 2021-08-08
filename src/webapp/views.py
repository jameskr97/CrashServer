from . import db
from .models import Minidump, Annotation
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
    res = Minidump.query.order_by(Minidump.date_created.desc()).limit(5).all()
    return render_template("crash.html", dumps=res)


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

    # Ensure minidump file was uploaded
    if "upload_file_minidump" not in request.files.keys():
        return {"error": "Missing minidump"}, 400
    minidump = request.files["upload_file_minidump"]
    minidump_fname = secure_filename(minidump.filename)

    # Validate magic number
    magic_number = magic.from_buffer(minidump.stream.read(2048), mime=True)
    if magic_number != "application/x-dmp":
        return {"error": "Bad Minidump"}, 400

    # At this point, we have received a minidump validated to be the correct type.
    # Save the file, insert annotations, and insert minidump records.

    # Save the minidump
    minidump_file = Path(current_app.config["MINIDUMP_STORE"]) / minidump_fname
    minidump.save(minidump_file.absolute())

    # Add minidump to database
    new_dump = Minidump(filename=minidump_fname, client_guid=request.args.get("guid", default=None))
    db.session.add(new_dump)
    db.session.flush()

    # Add annotations to database
    annotation = dict(request.values)
    annotation.pop("guid", None)  # Remove GUID value from annotations
    for key, value in annotation.items():
        new_annotation = Annotation(minidump_id=new_dump.id, key=key, value=value)
        db.session.add(new_annotation)

    db.session.commit()

    return "Received", 200
