from distutils.version import StrictVersion
import charset_normalizer as char_norm
import itertools
import operator

from flask import Blueprint, request, render_template

from crashserver.webapp import limiter

from crashserver.utility.decorators import (
    file_key_required,
    api_key_required,
    check_project_versioned,
)
from crashserver.webapp.models import Symbol, Project, ProjectType
from crashserver.utility.misc import SymbolData
import crashserver.webapp.operations as ops
from crashserver.webapp import db

api = Blueprint("api", __name__)


@api.route("/api/minidump/upload", methods=["POST"])
@limiter.limit()
@file_key_required("upload_file_minidump")
@api_key_required()
def upload_minidump(project):
    """
    A Crashpad_handler sets this endpoint as their upload url with the "-no-upload-gzip"
    argument, and it will save and prepare the file for processing
    :return:
    """
    minidump = request.files.get("upload_file_minidump")
    return ops.minidump_upload(db.session, project.id, dict(request.values), minidump.stream.read())


@api.route("/api/symbol/upload", methods=["POST"])
@file_key_required("symbol_file")
@api_key_required("symbol")
@check_project_versioned()
def upload_symbol(project, version):
    symbol_file = request.files.get("symbol_file")

    # Use charset_normalizer to get a readable version of the text.
    first_line_bytes = symbol_file.stream.read()
    char_res = char_norm.from_bytes(first_line_bytes)
    decoded = char_res.best().output()
    first_line_str = decoded[: decoded.find("\n".encode())].decode("utf-8")

    # Get relevant module info from first line of file
    symbol_data = SymbolData.from_module_line(first_line_str)
    symbol_data.app_version = version
    symbol_file.stream.seek(0)

    return ops.symbol_upload(db.session, project.id, decoded, symbol_data)


@api.route("/webapi/symbols/<project_id>")
def get_symbols(project_id):
    project = db.session.query(Project).get(project_id)
    proj_symbols = db.session.query(Symbol).filter_by(project_id=project_id).all()

    # Get counts for os symbols
    def sym_count(os: str):
        return db.session.query(Symbol).filter_by(project_id=project_id, os=os).count()

    stats = {
        "sym_count": {
            "linux": sym_count("linux"),
            "mac": sym_count("mac"),
            "windows": sym_count("windows"),
        }
    }
    if project.project_type == ProjectType.VERSIONED:

        # Creates callable that returns 'app_version' from object when you get_attr(object)
        # sym_dict is  in the format of {app_version: [Symbol objects of that version]}
        get_attr = operator.attrgetter("app_version")
        sorted_list = sorted(proj_symbols, key=lambda x: StrictVersion(str(get_attr(x))), reverse=True)
        sym_dict = {
            version: sorted(list(group), key=operator.attrgetter("os"))
            for version, group in itertools.groupby(sorted_list, get_attr)
        }
        stats = {
            "sym_count": {
                "linux": sym_count("linux"),
                "mac": sym_count("mac"),
                "windows": sym_count("windows"),
            }
        }
        return {
            "html": render_template(
                "symbols/symbol-list-versioned.html",
                project=project,
                sym_dict=sym_dict,
                stats=stats,
            )
        }, 200

    elif project.project_type == ProjectType.SIMPLE:
        return {
            "html": render_template(
                "symbols/symbol-list-simple.html",
                project=project,
                symbols=proj_symbols,
                stats=stats,
            )
        }, 200
