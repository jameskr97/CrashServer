from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField
from wtforms.validators import DataRequired, Email, Length

class LoginForm(FlaskForm):
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8, max=256)])
    remember_me = BooleanField('Remember Me')

class CreateAppForm(FlaskForm):
    title = StringField('Project Name', validators=[DataRequired()])
    project_type = SelectField('Project Type', validators=[DataRequired()], choices=[('simple', "Simple"), ('versioned', "Versioned")])

