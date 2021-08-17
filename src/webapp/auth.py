import os
import uuid

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Email, Length

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user, login_user, login_required, logout_user
from . import db, login
from .models import User

auth = Blueprint("auth", __name__)

# %% Flask-Login Required
@login.user_loader
def load_user(user_id):
    return User.query.get(user_id)

# %% Flask-WTF Form
class LoginForm(FlaskForm):
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8, max=256)])
    remember_me = BooleanField('Remember Me')

# %% Routes
@auth.route("/login", methods=["GET", "POST"])
def login():
    """Present the user with a page where they can login."""
    # Go to homepage if user is already logged in
    if current_user.is_authenticated:
        return redirect(url_for("auth.secure"))

    # If we posted and the for is valid
    form = LoginForm(request.form)
    if request.method == "POST" and form.validate():

        # Find the user verify password
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            # If any info is bad, alert user
            flash('Invalid email or password', category="error")
            return redirect(url_for('auth.login'))

        # Otherwise login
        else:
            flash("Logged in", category="info")
            login_user(user, remember=form.remember_me.data)
            return redirect(url_for('views.home'))

    # Present form errors if form is invalid
    elif form.errors:
        for field_name in form.errors:
            for error in form.errors[field_name]:
                flash("{}: {}".format(form[field_name].label.text, error), "error")

    return render_template('auth/login.html', form=form)


@auth.route("/logout")
def logout():
    if current_user.is_authenticated:
        flash("Logged out")
        logout_user()
    return redirect(url_for("views.home"))
