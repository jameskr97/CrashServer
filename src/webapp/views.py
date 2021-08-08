from flask import Blueprint, render_template
from .models import Minidump, Annotation

views = Blueprint("views", __name__)


@views.route('/')
def home():
    return render_template("home.html")


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
