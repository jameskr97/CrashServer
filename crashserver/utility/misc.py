import dataclasses

from flask import flash
import datetime
import humanize


def flash_form_errors(form):
    for field_name in form.errors:
        for error in form.errors[field_name]:
            flash("{}: {}".format(form[field_name].label.text, error), "error")


def get_font_awesome_os_icon(os: str):
    os = os.lower()
    if os == "windows":
        return "fab fa-windows"
    if os == "mac":
        return "fab fa-apple"
    if os == "linux":
        return "fab fa-linux"
    return ""


def get_storage_icon(key: str):
    key = key.lower()
    if key == "filesystem":
        return "fas fa-hdd"
    if key == "s3":
        return "fab fa-aws"


def naturaltime(time) -> str:
    now = datetime.datetime.now(tz=time.tzinfo)
    return humanize.naturaltime(now - time)


@dataclasses.dataclass
class SymbolData:
    """
    These attributes uniquely identify any symbol file. It is used over the Symbol db model as the db model is
    organized different to keep data duplication to a minimum
    """

    os: str = ""
    arch: str = ""
    build_id: str = ""
    module_id: str = ""
    app_version: str = None

    @staticmethod
    def from_module_line(module_line: str):
        metadata = module_line.strip().split(" ")
        return SymbolData(
            os=metadata[1],
            arch=metadata[2],
            build_id=metadata[3],
            module_id=metadata[4],
        )
