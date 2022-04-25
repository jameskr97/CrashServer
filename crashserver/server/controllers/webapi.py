import itertools
import json
import operator
import os

import natsort
from flask import Blueprint, request, render_template, flash, redirect, abort, url_for
from flask_babel import _
from flask_login import login_required
from loguru import logger
from sqlalchemy import func, text

from crashserver.server import db
from crashserver.server.models import Symbol, Project, ProjectType, Minidump, Attachment, Storage

webapi = Blueprint("webapi", __name__)


@webapi.route("/webapi/symbols/<project_id>")
def get_symbols(project_id):
    project = db.session.query(Project).get(project_id)
    proj_symbols = db.session.query(Symbol).filter_by(project_id=project_id).all()

    if len(proj_symbols) == 0:
        return {"html": render_template("symbols/symbol-list-no-syms.html")}, 200

    # Get counts for os symbols
    def sym_count(os: str):
        return db.session.query(Symbol).filter(Symbol.project_id == project_id).filter(func.lower(Symbol.os) == os.lower()).count()

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
        sym_dict = {version: sorted(list(group), key=operator.attrgetter("os")) for version, group in itertools.groupby(sorted_list, get_attr)}
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


@webapi.route("/webapi/stats/crash-per-day/<project_id>")
def crash_per_day(project_id):
    # Get crash per day data
    num_days = request.args.get("days", default=7, type=int)
    if num_days not in [7, 30]:
        num_days = 7

    if project_id == "all":
        project_id = None

    with db.engine.connect() as conn:
        conn.execute(f"SET LOCAL timezone = '{os.environ.get('TZ')}';")
        sql = text(
            f"""
        SELECT
            to_char(m.date_created::DATE, 'Dy') as day_name,
            to_char(m.date_created::DATE, 'MM-DD') as upload_date,
            COUNT(m.date_created) as num_dump
        FROM minidump m
        WHERE (m.project_id = :project_id OR :project_id is NULL)
        GROUP BY m.date_created::DATE
        ORDER BY to_char(m.date_created::DATE, 'YYYY-MM-DD') DESC
        LIMIT :num_days;
        """
        )
        res = conn.execute(sql, project_id=project_id, num_days=num_days)

    labels = []
    counts = []

    # Fill with actual data
    for data in res:
        labels.insert(0, [f"{data[1]}", f"({data[0]})"])
        counts.insert(0, data[2])

    # Fill with empty data if leftover spaces
    while len(labels) < num_days:
        labels.insert(0, [""])
        counts.insert(0, 0)

    return json.dumps({"labels": labels, "counts": counts}, default=str)


@webapi.route("/webapi/attachment/get-content/<attach_id>")
def get_attachment_content(attach_id):
    attach = Attachment.query.get(attach_id)
    content = attach.file_content
    return {"file_content": content}, 200 if content is not None else 404


@webapi.route("/webapi/storage/update/<key>", methods=["POST"])
@login_required
def update_storage_target(key):
    storage = db.session.query(Storage).get(key)

    # Attempting to save settings to a target that doesn't exist??
    if not storage:
        abort(500)

    # Determine if the storage backend is being enabled or disabled
    form = {key: val for key, val in dict(request.form).items() if val}

    # If this is set to primary, disable all other primary
    primary_backend = True if form.pop("primary_backend", False) else False
    if primary_backend:
        old_prim = db.session.query(Storage).filter_by(is_primary=True).first()
        old_prim.is_primary = False
        storage.is_primary = True


    should_enable = True if form.pop("target_enabled", False) else False  # Attempt to pop target_enabled. If it's not there, then disable.
    changed = not (should_enable == storage.is_enabled)

    old_config = storage.config.copy()
    old_config.update(form)

    # If it was changed, and should_enable is false, disable, commit, and notify.
    if changed and not should_enable:
        storage.is_enabled = False
        db.session.commit()
        flash(_("%(key)s has been disabled. No settings were changed.", key=key))
        logger.info(f"{key} has been disabled. No settings were changed.")
        return redirect(url_for("views.settings"))

    # If we are here, then the state is already enabled, or newly enabled. Either way, update the settings.
    valid = storage.meta.validate_credentials(old_config)  # First validate credentials

    if not valid:
        flash(_(f"Unable to validate credentials to {key}. Please try again."))
        return redirect(url_for("views.settings"))

    # If we are here, the given credentials were valid
    storage.config = old_config
    storage.is_enabled = True
    db.session.commit()

    Storage.init_targets()

    flash(_("%(key)s settings have been updated.", key=key))
    return redirect(url_for("views.settings"))
