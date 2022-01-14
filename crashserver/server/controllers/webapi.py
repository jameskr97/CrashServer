import itertools
import json
import operator
import os

import natsort
from flask import Blueprint, request, render_template, flash, redirect
from flask_babel import _
from flask_login import login_required
from loguru import logger
from sqlalchemy import func

from crashserver.server import db
from crashserver.server.models import Symbol, Project, ProjectType, Minidump, Attachment

webapi = Blueprint("webapi", __name__)


@webapi.route("/webapi/symbols/<project_id>")
def get_symbols(project_id):
    project = db.session.query(Project).get(project_id)
    proj_symbols = db.session.query(Symbol).filter_by(project_id=project_id).all()

    if len(proj_symbols) == 0:
        return {"html": render_template("symbols/symbol-list-no-syms.html")}, 200

    # Get counts for os symbols
    def sym_count(os: str):
        return (
            db.session.query(Symbol)
            .filter(Symbol.project_id == project_id)
            .filter(func.lower(Symbol.os) == os.lower())
            .count()
        )

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
        sorted_list = natsort.natsorted(proj_symbols, key=lambda x: get_attr(x), reverse=True)
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


@webapi.route("/webapi/symbols/count/<project_id>")
def get_symbols_count(project_id):
    proj_symbols = db.session.query(Symbol).filter_by(project_id=project_id).all()
    return {"count": len(proj_symbols)}, 200


@webapi.route("/webapi/project/rename/", methods=["POST"])
@login_required
def rename_project():
    project_id = request.form.get("project_id")
    new_name = request.form.get("project_name")
    res: Project = db.session.query(Project).filter_by(id=project_id).first()

    if res is None:
        flash(_("Unable to find Project ID?"), category="warning")
        logger.warning("Unable to rename project. Bad project ID: {}".format(project_id))
    else:
        message = _("Project %(old)s renamed to %(new)s", old=res.project_name, new=new_name)
        res.project_name = new_name
        db.session.commit()

        logger.info(message)
        flash(message)

    return redirect(request.referrer)


@webapi.route("/webapi/minidump/delete/<dump_id>", methods=["DELETE"])
@login_required
def delete_minidump(dump_id):
    dump = db.session.query(Minidump).get(dump_id)
    if not dump:
        return {"error", "dump_id is invalid"}, 404

    dump.delete_minidump()
    db.session.delete(dump)
    db.session.commit()
    return "", 200


@webapi.route("/webapi/stats/crash-per-day")
def crash_per_day():
    # Get crash per day data
    num_days = request.args.get("days", default=7, type=int)
    if num_days not in [7, 30]:
        num_days = 7

    with db.engine.connect() as conn:
        conn.execute(f"SET LOCAL timezone = '{os.environ.get('TZ')}';")
        sql = f"""
        SELECT
            to_char(m.date_created::DATE, 'Dy') as day_name,
            to_char(m.date_created::DATE, 'MM-DD') as upload_date,
            COUNT(m.date_created) as num_dump
        FROM minidump m
        GROUP BY m.date_created::DATE
        ORDER BY to_char(m.date_created::DATE, 'YYYY-MM-DD') DESC
        LIMIT {num_days};
        """
        res = conn.execute(sql)

    labels = []
    counts = []
    for data in res:
        labels.insert(0, [f"{data[1]}", f"({data[0]})"])
        counts.insert(0, data[2])

    return json.dumps({"labels": labels, "counts": counts}, default=str)


@webapi.route("/webapi/attachment/get-content/<attach_id>")
def get_attachment_content(attach_id):
    attach = Attachment.query.get(attach_id)
    content = attach.file_content
    return {"file_content": content}, 200 if content is not None else 404
