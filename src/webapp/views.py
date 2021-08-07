from flask import Blueprint, render_template

views = Blueprint("views", __name__)


@views.route('/')
def home():
    return render_template("home.html")


@views.route('/crash-reports')
def crash():
    return render_template("crash.html")


@views.route('/symbols')
def symbols():
    return render_template("symbols.html")


@views.route('/upload')
def upload():
    return render_template("upload.html")
