import os
import uuid

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required

from crashserver.webapp.models import Minidump, Project, ProjectType, User
from crashserver.webapp.forms import CreateAppForm, UploadMinidumpForm
from crashserver.utility import misc
from crashserver.webapp import db
from crashserver.webapp import operations as ops

views = Blueprint("views", __name__)


# @views.route("/")
# def home():
#     apps = Project.query.with_entities(Project.id, Project.project_name).all()
#     return render_template("home.html", apps=apps)


@views.route("/settings")
@login_required
def settings():
    users = db.session.query(User).all()
    projects = db.session.query(Project).all()
    [p.create_directories() for p in projects]
    return render_template("app/settings.html", users=users, projects=projects)


@views.route("/project/create", methods=["GET", "POST"])
@login_required
def project_create():
    form = CreateAppForm(request.form)

    # If the form is valid
    if request.method == "POST" and form.validate():
        # Check if the name is taken
        existing = db.session.query(Project).filter_by(project_name=form.title.data).first()
        if existing is not None:
            flash('Project name "%s" is taken.' % form.title.data)
            return redirect(url_for("views.project_create", form=form))

        # Create the project
        # TODO(james): Ensure apikey doesn't exist?
        new_project = Project(project_name=form.title.data)
        new_api_key = str(uuid.UUID(bytes=os.urandom(16), version=4)).replace("-", "")
        new_project.api_key = new_api_key
        new_project.project_type = ProjectType.get_type_from_str(form.project_type.data)

        db.session.add(new_project)
        db.session.commit()

        new_project.create_directories()

        flash('Project "%s" was created.' % form.title.data)
        return redirect(url_for("views.home"))
    else:
        misc.flash_form_errors(form)

    return render_template("app/create.html", form=form)


@views.route("/project/<id>")
def project_dashboard(id: str):
    proj = Project.query.filter_by(id=id).first()
    return render_template("app/dashboard.html", project=proj)


@views.route("/")
@views.route("/crash-reports")
def crash():
    page = request.args.get("page", 1, type=int)
    res = (
        db.session.query(Minidump, Project.project_name)
        .filter(Minidump.project_id == Project.id)
        .order_by(Minidump.date_created.desc())
        .paginate(page=page, per_page=10)
    )
    return render_template("crash/crash.html", dumps=res)


@views.route("/crash-reports/<crash_id>")
def crash_detail(crash_id):
    minidump = db.session.query(Minidump).get(crash_id)
    return render_template("crash/crash_detail.html", minidump=minidump)


@views.route("/symbols")
def symbols():
    projects = Project.query.with_entities(Project.id, Project.project_name).all()
    return render_template("symbols/symbols.html", projects=projects)


@views.route("/upload", methods=["GET", "POST"])
def upload():
    form = UploadMinidumpForm()

    if request.method == "POST" and form.validate_on_submit():
        res = ops.minidump_upload(db.session, form.project.data, None, form.minidump.data.stream.read())
        if res.status_code != 200:
            flash(res.json["error"], category="danger")
            return redirect(url_for("views.upload"))
        else:
            return redirect(url_for("views.crash_detail", crash_id=res.json["id"]))
    else:
        misc.flash_form_errors(form)

    projects = Project.query.with_entities(Project.id, Project.project_name).all()
    for p in projects:
        form.add_project_choice(str(p.id), p.project_name)
    return render_template("upload.html", form=form, projects=projects)
