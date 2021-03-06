import io
import os
import uuid

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_babel import _
from flask_login import login_required, current_user

from crashserver.config import settings as config
from crashserver.server import db, helpers
from crashserver.server.forms import CreateAppForm, UploadMinidumpForm, UpdateAccount, UploadSymbolForm
from crashserver.server.models import Minidump, Project, ProjectType, User, Storage
from crashserver.utility import misc

views = Blueprint("views", __name__)


@views.route("/")
def home():
    apps = Project.query.all()
    return render_template("app/home.html", apps=apps)


@views.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    users = db.session.query(User).all()
    projects = db.session.query(Project).all()
    storage = db.session.query(Storage).order_by(Storage.key).all()

    form = UpdateAccount(current_user)
    if request.method == "POST" and form.validate():
        current_user.set_password(form.new_pass.data)
        db.session.commit()
        flash(_("Password Updated"))
    else:
        misc.flash_form_errors(form)

    return render_template(
        "app/settings.html",
        account_form=form,
        users=users,
        projects=projects,
        settings=config,
        storage=storage,
    )


@views.route("/project/create", methods=["GET", "POST"])
@login_required
def project_create():
    form = CreateAppForm(request.form)

    # If the form is valid
    if request.method == "POST" and form.validate():
        # Check if the name is taken
        existing = db.session.query(Project).filter_by(project_name=form.title.data).first()
        if existing is not None:
            flash(_("Project name %(name)s is taken.", name=form.title.data))
            return redirect(url_for("views.project_create", form=form))

        # Create the project
        # TODO(james): Ensure apikey doesn't exist?
        def random_key():
            return str(uuid.UUID(bytes=os.urandom(16), version=4)).replace("-", "")

        new_project = Project(project_name=form.title.data)
        new_project.minidump_api_key = random_key()
        new_project.symbol_api_key = random_key()
        new_project.project_type = ProjectType.get_type_from_str(form.project_type.data)

        db.session.add(new_project)
        db.session.commit()

        flash(_("Project %(name)s was created.", name=form.title.data))
        return redirect(url_for("views.home"))
    else:
        misc.flash_form_errors(form)

    return render_template("app/create.html", form=form)


@views.route("/project/<id>")
def project_dashboard(id: str):
    proj = Project.query.filter_by(id=id).first()
    return render_template("app/dashboard.html", project=proj)


@views.route("/crash-reports")
def crash():
    page = request.args.get("page", 1, type=int)
    res = db.session.query(Minidump, Project.project_name).filter(Minidump.project_id == Project.id).order_by(Minidump.date_created.desc()).paginate(page=page, per_page=10)
    return render_template("crash/crash.html", dumps=res)


@views.route("/crash-reports/<crash_id>")
def crash_detail(crash_id):
    minidump = db.session.query(Minidump).get(crash_id)

    if not minidump:
        abort(404)

    return render_template("crash/crash_detail.html", dump=minidump)


@views.route("/symbols")
def symbols():
    projects = Project.query.with_entities(Project.id, Project.project_name).all()
    return render_template("symbols/symbols.html", projects=projects)


@views.route("/upload-minidump", methods=["GET", "POST"])
def upload_minidump():
    form = UploadMinidumpForm()

    if request.method == "POST" and form.validate_on_submit():
        res = helpers.minidump_upload(db.session, form.project.data, {}, form.minidump.data.stream.read(), [])
        if res.status_code != 200:
            flash(res.json["error"], category="danger")
            return redirect(url_for("views.upload_minidump"))
        else:
            return redirect(url_for("views.crash_detail", crash_id=res.json["id"]))
    else:
        misc.flash_form_errors(form)

    projects = Project.query.with_entities(Project.id, Project.project_name).all()
    for p in projects:
        form.add_project_choice(str(p.id), p.project_name)
    return render_template("app/upload.html", form=form, projects=projects)


@views.route("/upload-symbol", methods=["GET", "POST"])
@login_required
def upload_symbol():
    form = UploadSymbolForm()

    if request.method == "POST" and form.validate_on_submit():
        project = Project.query.get(form.project.data)  # Get project

        # Read first line of symbol file
        symbol_file_bytes = form.symbol.data.stream.read()
        with io.BytesIO(symbol_file_bytes) as f:
            first_line_str = f.readline().decode("utf-8")

        # Get relevant module info from first line of file
        symbol_data = misc.SymbolData.from_module_line(first_line_str)
        symbol_data.app_version = form.version.data if form.version.data else None

        res = helpers.symbol_upload(db.session, project, symbol_file_bytes, symbol_data)
        if res.status_code != 200:
            flash(res.json["error"], category="danger")
        else:
            flash(_(f"Symbol {symbol_data.module_id}:{symbol_data.os}:{symbol_data.build_id} received."))
    else:
        misc.flash_form_errors(form)

    projects = Project.query.with_entities(Project.id, Project.project_name, Project.project_type).all()
    return render_template("symbols/symbol-upload.html", projects=projects, form=form)
