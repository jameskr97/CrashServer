import os
import uuid

from flask import Blueprint, render_template, request, redirect, url_for

from . import db
from .models import Annotation, Minidump, Project

views = Blueprint("views", __name__)


@views.route('/')
def home():
    apps = Project.query.with_entities(Project.id, Project.project_name).all()
    return render_template("home.html", apps=apps)


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
    res = db.session.query(Minidump, Project.project_name).order_by(Minidump.date_created.desc()).limit(5).all()
    return render_template("crash.html", data=res)


@views.route('/crash-reports/<crash_id>')
def crash_detail(crash_id):
    res = db.session.query(Minidump, Project).filter(Minidump.id == crash_id).first()
    return render_template("crash_detail.html", dump=res[0], project=res[1])


@views.route('/symbols')
def symbols():
    return render_template("symbols.html")


@views.route('/upload')
def upload():
    return render_template("upload.html")
