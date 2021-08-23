from distutils.version import StrictVersion
import itertools
import operator

from flask import Blueprint, request, render_template
import magic

from crashserver.utility.decorators import file_key_required, api_key_required, check_project_versioned
from crashserver.webapp.models import Minidump, Annotation, Symbol, Project, ProjectType
import crashserver.webapp.operations as ops
import crashserver.tasks as tasks
from crashserver.webapp import db

api = Blueprint("api", __name__)


@api.route('/api/minidump/upload', methods=["POST"])
@file_key_required("upload_file_minidump")
@api_key_required()
def upload_minidump(project):
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
    new_dump = Minidump(project_id=project.id, client_guid=request.args.get("guid", default=None))
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
@check_project_versioned()
def upload_symbol(project, version):
    # Get relevant module info from first line of file
    symbol_file = request.files.get("symbol_file")
    symbol_data = ops.SymbolData.from_module_line(symbol_file.stream.readline().decode('utf-8'))
    symbol_data.app_version = version
    symbol_file.stream.seek(0)

    return ops.symbol_upload(db.session, project.id, symbol_file.stream.read(), symbol_data)


@api.route('/webapi/symbols/<project_id>')
def get_symbols(project_id):
    project = db.session.query(Project).get(project_id)
    proj_symbols = db.session.query(Symbol).filter_by(project_id=project_id).all()

    # Get counts for os symbols
    def sym_count(os: str): return db.session.query(Symbol).filter_by(project_id=project_id, os=os).count()
    stats = {"sym_count": {
            "linux": sym_count("linux"),
            "mac": sym_count("mac"),
            "windows": sym_count("windows"),
        }}
    if project.project_type == ProjectType.VERSIONED:

        # Creates callable that returns 'app_version' from object when you get_attr(object)
        # sym_dict is  in the format of {app_version: [Symbol objects of that version]}
        get_attr = operator.attrgetter('app_version')
        sorted_list = sorted(proj_symbols, key=lambda x: StrictVersion(str(get_attr(x))), reverse=True)
        sym_dict = {version: sorted(list(group), key=operator.attrgetter('os')) for version, group in itertools.groupby(sorted_list, get_attr)}
        stats = {
            "sym_count": {
                "linux": sym_count("linux"),
                "mac": sym_count("mac"),
                "windows": sym_count("windows"),
            }
        }
        return {"html": render_template("symbols/symbol-list-versioned.html", project=project, sym_dict=sym_dict, stats=stats)}, 200

    elif project.project_type == ProjectType.SIMPLE:
        return {"html": render_template("symbols/symbol-list-simple.html", project=project, symbols=proj_symbols, stats=stats)}, 200


