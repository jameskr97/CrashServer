import os
import uuid

from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required

from . import db
from .models import Minidump, Project, CompileMetadata

views = Blueprint("views", __name__)


@views.route('/')
def home():
    apps = Project.query.with_entities(Project.id, Project.project_name).all()
    return render_template("home.html", apps=apps)


@views.route('/settings')
@login_required
def settings():
    return render_template("app/settings.html")


@views.route('/project/create', methods=["GET", "POST"])
def project_create():
    if request.method == "GET":
        return render_template("app/create.html")

    new_project = Project(project_name=request.form.get("project_name"))
    new_api_key = str(uuid.UUID(bytes=os.urandom(16), version=4)).replace("-", "")
    new_project.api_key = new_api_key

    db.session.add(new_project)
    db.session.commit()
    return redirect(url_for('views.project_dashboard', id=new_project.id))


@views.route('/project/<id>')
def project_dashboard(id: str):
    proj = Project.query.filter_by(id=id).first()
    return render_template("app/dashboard.html", project=proj)


@views.route('/crash-reports')
def crash():
    res = db.session.query(Minidump, Project.project_name)\
        .filter(Minidump.project_id == Project.id)\
        .order_by(Minidump.date_created.desc())\
        .limit(5).all()
    return render_template("crash/crash.html", data=res)


@views.route('/crash-reports/<crash_id>')
def crash_detail(crash_id):
    res = db.session.query(Minidump, Project, CompileMetadata)\
        .filter(Minidump.id == crash_id)\
        .filter(Minidump.project_id == Project.id)\
        .filter(Minidump.build_metadata_id == CompileMetadata.id)\
        .first()
    return render_template("crash/crash_detail.html", dump=res[0], project=res[1], meta=res[2])


@views.route('/symbols')
def symbols():
    projects = Project.query.with_entities(Project.id, Project.project_name).all()
    return render_template("symbols/symbols.html", projects=projects)


@views.route('/upload')
def upload():
    return render_template("upload.html")
