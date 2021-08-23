from flask import flash


def flash_form_errors(form):
    for field_name in form.errors:
        for error in form.errors[field_name]:
            flash("{}: {}".format(form[field_name].label.text, error), "error")


def get_font_awesome_os_icon(os: str):
    if os == "windows":
        return "fab fa-windows"
    if os == "mac":
        return "fab fa-apple"
    if os == "linux":
        return "fab fa-linux"
    return ""
