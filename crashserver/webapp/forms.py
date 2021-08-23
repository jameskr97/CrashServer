from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, SelectField
from wtforms.validators import DataRequired, Email, Length

class LoginForm(FlaskForm):
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8, max=256)])
    remember_me = BooleanField('Remember Me')

class CreateAppForm(FlaskForm):
    title = StringField('Project Name', validators=[DataRequired()])
    project_type = SelectField('Project Type', validators=[DataRequired()], choices=[('simple', "Simple"), ('versioned', "Versioned")])


class UploadMinidumpForm(FlaskForm):
    minidump = FileField("Select Minidump file", validators=[FileRequired(), FileAllowed(['dmp'], "Minidump Files Only")])
    project = SelectField(u"Projects", coerce=str, validate_choice=False)

    def add_project_choice(self, value, title):
        data = (value, title)
        if not self.project.choices:
            self.project.choices = [data]
        else:
            self.project.choices.append(data)
