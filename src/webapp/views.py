from flask import Blueprint, render_template
from .models import Minidump

views = Blueprint("views", __name__)


@views.route('/')
def home():
    return render_template("home.html")


@views.route('/crash-reports')
def crash():
    res = Minidump.query.order_by(Minidump.date_created.desc()).limit(5).all()
    return render_template("crash.html", dumps=res)


@views.route('/symbols')
def symbols():
    return render_template("symbols.html")


@views.route('/upload')
def upload():
    return render_template("upload.html")
