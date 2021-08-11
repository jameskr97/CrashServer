import os
import uuid

from flask import Blueprint, render_template, request, redirect, url_for

from . import db
from .models import Minidump, Annotation, Application

views = Blueprint("views", __name__)


@views.route('/')
def home():
    apps = Application.query.with_entities(Application.id, Application.app_name).all()
    return render_template("home.html", apps=apps)


@views.route('/app/create', methods=["GET", "POST"])
def app_create():
    if request.method == "GET":
        return render_template("app/create.html")

    new_app = Application(app_name=request.form.get("app_name"))
    new_api_key = str(uuid.UUID(bytes=os.urandom(16), version=4)).replace("-", "")
    new_app.api_key = new_api_key

    db.session.add(new_app)
    db.session.commit()
    return redirect(url_for('views.app_dashboard', id=new_app.id))


@views.route('/app/<id>')
def app_dashboard(id: str):
    app = Application.query.filter_by(id=id).first()
    return render_template("app/dashboard.html", app=app)


@views.route('/crash-reports')
def crash():
    res = Minidump.query.order_by(Minidump.date_created.desc()).limit(5).all()
    return render_template("crash.html", dumps=res)


@views.route('/crash-reports/<crash_id>')
def crash_detail(crash_id):
    dump = Minidump.query.filter_by(id=crash_id).first()
    annotations = Annotation.query.filter_by(minidump_id=dump.id)
    return render_template("crash_detail.html", dump=dump, annotations=annotations)


@views.route('/symbols')
def symbols():
    return render_template("symbols.html")


@views.route('/upload')
def upload():
    return render_template("upload.html")
