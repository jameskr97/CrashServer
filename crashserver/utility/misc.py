from flask import flash


def flash_form_errors(form):
    for field_name in form.errors:
        for error in form.errors[field_name]:
            flash("{}: {}".format(form[field_name].label.text, error), "error")
